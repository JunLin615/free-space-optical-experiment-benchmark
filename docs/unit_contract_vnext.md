# vNext answer-unit audit

The real rc1 baseline exposed a contract error in SEED-2-2: a ratio labeled
`dimensionless` was rejected where the rc1 numerical oracle accepts `1`.
`tools/vnext/units.py` defines a separate, finite v0.2 normalization table.
It is applied to submitted Quantity objects before vNext scoring. The original
answer remains in the result record. rc1 evaluation and recorded scores are
unchanged.

| Quantity | Explicit vNext representation | Boundary |
| --- | --- | --- |
| Dimensionless | `1`, `dimensionless`, `unitless` | Length, angle, time, frequency still fail. |
| Fraction/percentage | `1`; `%` or `percent` divided by 100 | `70 percent` means 0.7, not 70. |
| Angle | `rad`, `deg`, `radian(s)`, `degree(s)` | Conversion uses the existing radian base. |
| Metric length | Existing `m`, `mm`, `um`, `µm`, `nm`; explicit common names, `cm`, `μm` | No implicit wavelength-to-length conversion. |
| Time | Existing `s`, `ps`, `fs`; explicit `ms`, `us`/`µs`/`μs`, `ns` and names | Frequency units do not satisfy time. |
| Frequency | Existing `Hz`, `kHz`, `MHz`, `GHz`; names and `THz` | Time units do not satisfy frequency. |
| Wavelength-normalized values | A dimensionless number of wavelengths uses `1` or `dimensionless` | A bare `wavelength` unit cannot be converted without a specified reference wavelength and is rejected. |

Aliases are case-sensitive and no arbitrary text parsing, unit algebra, or
dimensional inference is attempted. Unknown units fail via the normal numerical
validator. The normalizer does not fix missing fields, nonfinite values, or
malformed quantities. In particular, `3 mm` cannot satisfy a dimensionless
criterion, and `Hz` cannot satisfy a time criterion.

## Retrospective compatibility calculation

The four frozen SEED-2-2 answers in the verified `gpt-6-luna` baseline were
passed through the vNext evaluator without altering any stored run file. This
is a derived interpretation, **not** a corrected rc1 baseline or a new model
run.

| Protocol | Recorded rc1 score | Derived vNext score | Reason |
| --- | ---: | ---: | --- |
| Closed-book | 0.60 | 0.60 | The Galilean focal-length pair has the wrong magnitude ratio; unit normalization cannot fix it. |
| Case-assisted | 0.65 | 1.00 | The submitted ratio used `dimensionless`, now accepted as equivalent to `1`. |
| Tool-assisted | 0.65 | 1.00 | Same unit-label correction. |
| Case and tool-assisted | 0.65 | 1.00 | Same unit-label correction. |

These are answer-contract effects on one published case, not evidence of a
protocol benefit or a model performance change. The original rc1 values,
failure classes, result bytes, and analyses remain authoritative for rc1.
