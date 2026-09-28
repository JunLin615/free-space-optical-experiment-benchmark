"""Independent geometric constructions for the two challenged cases."""

from __future__ import annotations

import math
import unittest

from tools.physics_checks import SPEED_OF_LIGHT_M_PER_S, expected_si
from tools.scoring_runtime import load_scored_case


class IndependentPhysicsTests(unittest.TestCase):
    def test_mirror_vector_reflection_and_screen_intersection(self) -> None:
        case = load_scored_case("SEED-1-1")
        theta = math.radians(0.5)
        # Incident d=(0,0,1), rotated mirror normal n=(sin θ,0,cos θ).
        nx, nz = math.sin(theta), math.cos(theta)
        dot = nz
        rx, rz = -2 * dot * nx, 1 - 2 * dot * nz
        reflected_angle = math.atan2(abs(rx), abs(rz))
        # Screen normal to nominal reflected ray, at z=-2 m.
        spot_x = (-2.0 / rz) * rx
        expected_angle, _ = expected_si(case, "mirror_angle")
        expected_shift, _ = expected_si(case, "mirror_spot_shift")
        self.assertAlmostEqual(reflected_angle, expected_angle, places=12)
        self.assertAlmostEqual(abs(spot_x), expected_shift, places=12)

    def test_two_explicit_segments_and_inverse_travel(self) -> None:
        case = load_scored_case("SEED-1-5")
        original_stage_distance = 0.2
        motion = 0.001
        old_path = original_stage_distance + original_stage_distance
        new_path = (original_stage_distance + motion) + (original_stage_distance + motion)
        path_difference = new_path - old_path
        delay = path_difference / SPEED_OF_LIGHT_M_PER_S
        target = 100e-12
        # Solve equality of explicit outbound and return segment growth.
        required_motion = (target * SPEED_OF_LIGHT_M_PER_S) / 2
        self.assertAlmostEqual(path_difference, expected_si(case, "folded_delay_path")[0], places=12)
        self.assertAlmostEqual(delay, expected_si(case, "folded_delay_time")[0], places=20)
        self.assertAlmostEqual(required_motion, expected_si(case, "folded_delay_stage_for_target")[0], places=12)


if __name__ == "__main__":
    unittest.main()
