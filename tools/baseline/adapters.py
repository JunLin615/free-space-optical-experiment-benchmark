"""Provider-neutral agent turn adapters and a constrained Codex CLI bridge."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class AdapterFailure(RuntimeError):
    failure_class = "model_api_failure"

    def __init__(self, message: str, *, events: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.events = events or []


class AdapterTimeout(AdapterFailure):
    failure_class = "timeout"


class AdapterProtocolFailure(AdapterFailure):
    failure_class = "malformed_adapter_response"


class BuiltinToolViolation(AdapterFailure):
    failure_class = "tool_policy_violation"


@dataclass
class AgentTurn:
    kind: str
    raw_response: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    usage: dict[str, int | None] = field(default_factory=dict)
    provider_usage: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    wall_time_seconds: float = 0.0


class Adapter(Protocol):
    def invoke(self, request: dict[str, Any], timeout_seconds: float) -> AgentTurn: ...


def _decode_turn(value: Any, *, wall_time_seconds: float, events: list[dict[str, Any]] | None = None) -> AgentTurn:
    if not isinstance(value, dict) or value.get("type") not in {"final", "tool_call"}:
        raise AdapterProtocolFailure("adapter must return a final or tool_call JSON envelope")
    usage = value.get("usage") or {}
    if not isinstance(usage, dict):
        raise AdapterProtocolFailure("usage must be an object")
    if value["type"] == "final":
        response = value.get("raw_response")
        if not isinstance(response, str):
            raise AdapterProtocolFailure("final envelope needs raw_response string")
        return AgentTurn("final", raw_response=response, usage=usage,
                         provider_usage=value.get("provider_usage"), events=events or [],
                         wall_time_seconds=wall_time_seconds)
    name, args = value.get("tool_name"), value.get("arguments")
    if not isinstance(name, str) or not isinstance(args, dict):
        raise AdapterProtocolFailure("tool_call envelope needs tool_name and arguments")
    return AgentTurn("tool_call", tool_name=name, arguments=args, usage=usage,
                     provider_usage=value.get("provider_usage"), events=events or [],
                     wall_time_seconds=wall_time_seconds)


class MockAdapter:
    """Scripted dry-run adapter; its records can never be labeled real baseline."""

    def __init__(self, script: dict[str, list[dict[str, Any]]]):
        self.script = {key: list(turns) for key, turns in script.items()}

    def invoke(self, request: dict[str, Any], timeout_seconds: float) -> AgentTurn:
        key = request["selection_key"] + "|" + request["protocol_id"]
        turns = self.script.get(key, [])
        if not turns:
            raise AdapterProtocolFailure(f"mock script exhausted for {key}")
        return _decode_turn(turns.pop(0), wall_time_seconds=0.0)


class CommandAdapter:
    """Run a command that accepts one JSON request on stdin and emits one JSON envelope."""

    def __init__(self, command: list[str]):
        if not command or not all(isinstance(part, str) and part for part in command):
            raise ValueError("command adapter needs nonempty argument vector")
        self.command = command

    def invoke(self, request: dict[str, Any], timeout_seconds: float) -> AgentTurn:
        start = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="optics-baseline-command-") as directory:
            try:
                result = subprocess.run(self.command, input=json.dumps(request, ensure_ascii=False),
                                        text=True, encoding="utf-8", capture_output=True, cwd=directory,
                                        timeout=timeout_seconds, check=False)
            except subprocess.TimeoutExpired as exc:
                raise AdapterTimeout("command adapter timed out") from exc
            except OSError as exc:
                raise AdapterFailure(f"command adapter launch failed: {type(exc).__name__}") from exc
        if result.returncode != 0:
            raise AdapterFailure(f"command adapter exited {result.returncode}; stderr omitted from log")
        try:
            envelope = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise AdapterProtocolFailure("command adapter did not emit one JSON envelope") from exc
        return _decode_turn(envelope, wall_time_seconds=time.monotonic() - start)


def _codex_prompt(request: dict[str, Any]) -> str:
    """Put only public scientific payload and permitted context in the model prompt."""
    lines = [request["system_prompt"]]
    if request["allowed_tools"]:
        lines += ["A tool-assisted turn may request one runner tool through a JSON envelope, for example:",
                  '{"type":"tool_call","tool_name":"calculator","arguments":{"expression":"2*pi"}}.',
                  "Only runner tools listed below are permitted. Do not use built-in tools.",
                  "Permitted runner tools: " + json.dumps(request["allowed_tools"])]
    else:
        lines += ["No tools are available. Return the final JSON answer directly. Do not use built-in tools."]
    lines += ["Scientific task and answer structure:",
             json.dumps(request["scientific_payload"], ensure_ascii=False, sort_keys=True),
             "Retrieved examples (if any):",
             json.dumps(request.get("retrieved_items", []), ensure_ascii=False, sort_keys=True),
             "Prior tool exchanges (if any):",
             json.dumps(request.get("tool_exchanges", []), ensure_ascii=False, sort_keys=True),
             "Return the final answer as one JSON object only."]
    if request.get("correction"):
        lines.append("Format correction: " + request["correction"])
    return "\n\n".join(lines)


def _safe_codex_event(event: dict[str, Any]) -> dict[str, Any]:
    """Preserve event order/type/usage while omitting arbitrary tool output."""
    safe: dict[str, Any] = {"type": event.get("type")}
    if isinstance(event.get("usage"), dict):
        safe["usage"] = {key: value for key, value in event["usage"].items()
                         if isinstance(value, int) and value >= 0}
    item = event.get("item")
    if isinstance(item, dict):
        safe["item"] = {key: item[key] for key in ("id", "type", "status")
                        if key in item and isinstance(item[key], (str, int))}
        if item.get("type") not in {"agent_message", "reasoning", "error"}:
            safe["item"]["event_sha256"] = hashlib.sha256(
                json.dumps(item, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return safe


class CodexCliAdapter:
    """Codex CLI with built-in tools disabled and an isolated temporary cwd.

    JSONL events and final message are retained in memory for runner logs. A
    built-in tool event invalidates the run rather than being counted as an
    approved calculator/unit conversion call.
    """

    def __init__(self, model_id: str, command_prefix: list[str] | None = None):
        self.model_id = model_id
        self.command_prefix = command_prefix or ["codex"]

    def invoke(self, request: dict[str, Any], timeout_seconds: float) -> AgentTurn:
        start = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="optics-baseline-codex-") as directory:
            output_path = Path(directory) / "last_message.txt"
            executable = shutil.which(self.command_prefix[0]) or self.command_prefix[0]
            command = [executable, *self.command_prefix[1:], "exec", "--json", "--skip-git-repo-check",
                       "-C", directory, "--sandbox", "read-only", "--disable", "shell_tool",
                       "-c", 'web_search="disabled"',
                       "-m", self.model_id, "-o", str(output_path), "-"]
            # Keep login and runtime variables, but never pass common API keys to
            # a subprocess prompted by a candidate model.
            environment = {key: value for key, value in os.environ.items()
                           if not any(secret in key.upper() for secret in
                                      ("API_KEY", "TOKEN", "PASSWORD", "SECRET", "CREDENTIAL"))}
            try:
                result = subprocess.run(command, input=_codex_prompt(request), text=True, encoding="utf-8",
                                        capture_output=True, cwd=directory, env=environment,
                                        timeout=timeout_seconds, check=False)
            except subprocess.TimeoutExpired as exc:
                partial = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                partial_events = []
                for line in partial.splitlines():
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(event, dict):
                        partial_events.append(_safe_codex_event(event))
                raise AdapterTimeout("Codex CLI timed out", events=partial_events) from exc
            except OSError as exc:
                raise AdapterFailure(f"Codex CLI launch failed: {type(exc).__name__}") from exc
            events = []
            for line in result.stdout.splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    events.append(event)
            safe_events = [_safe_codex_event(event) for event in events]
            if result.returncode != 0:
                raise AdapterFailure(f"Codex CLI exited {result.returncode}; stderr omitted from log",
                                     events=safe_events)
            item_errors = [event["item"] for event in events if event.get("type", "").startswith("item.")
                           and isinstance(event.get("item"), dict) and event["item"].get("type") == "error"]
            if item_errors:
                message_digest = hashlib.sha256(str(item_errors[0].get("message", "unknown")).encode("utf-8")).hexdigest()
                raise AdapterFailure(f"Codex CLI item error; message_sha256={message_digest}",
                                     events=safe_events)
            forbidden = [event for event in events if event.get("type", "").startswith("item.")
                         and isinstance(event.get("item"), dict)
                         and event["item"].get("type") not in {"agent_message", "reasoning", "error"}]
            if forbidden:
                kinds = sorted({str(event["item"].get("type")) for event in forbidden})
                raise BuiltinToolViolation(f"Codex emitted {len(forbidden)} built-in tool event(s): {kinds}",
                                           events=safe_events)
            raw = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        usage = {}
        for event in events:
            if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
                reported = event["usage"]
                for source, target in (("input_tokens", "input"), ("output_tokens", "output"),
                                       ("cached_input_tokens", "cached_input"),
                                       ("reasoning_output_tokens", "reasoning")):
                    if isinstance(reported.get(source), int):
                        usage[target] = reported[source]
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError:
            envelope = {"type": "final", "raw_response": raw}
        if isinstance(envelope, dict) and envelope.get("type") not in {"final", "tool_call"}:
            envelope = {"type": "final", "raw_response": raw}
        envelope["usage"] = usage
        envelope["provider_usage"] = {"source": "codex_jsonl", "usage": usage}
        return _decode_turn(envelope, wall_time_seconds=time.monotonic() - start, events=safe_events)
