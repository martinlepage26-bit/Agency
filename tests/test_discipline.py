import unittest
import sys
import os

# Add src to path so we can import Lotus packages directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from lotus.core.engine import calculate_agency

class TestTierDiscipline(unittest.TestCase):
    def setUp(self):
        self.base_intake = {
            "signals": [],
            "constraints": [],
            "identity": [{"value": "Subject Alpha", "tier": "B"}],
            "archives": []
        }

    def test_tier_a_dominance(self):
        """Tier A 'isolated' must trigger the numeric cap of 12."""
        intake_with_constraint = self.base_intake.copy()
        intake_with_constraint["signals"] = [{"value": "Geographically isolated", "tier": "A"}]
        
        result = calculate_agency(intake_with_constraint)
        score = result['subscores']['perceptual_latitude']['score']
        self.assertEqual(score, 12.0)

    def test_tier_c_non_mutation(self):
        """Tier C claims must NOT change the agency_total."""
        score_1 = calculate_agency(self.base_intake)['agency_total']
        
        intake_with_tier_c = self.base_intake.copy()
        intake_with_tier_c["identity"].append({"value": "Symbolic Power", "tier": "C"})
        
        score_2 = calculate_agency(intake_with_tier_c)['agency_total']
        self.assertEqual(score_1, score_2)

    def test_caps_are_scoped_to_the_correct_subscore(self):
        """Per-subscore caps should not bleed into unrelated dimensions."""
        intake = self.base_intake.copy()
        intake["signals"] = [{"value": "Geographically isolated", "tier": "A"}]
        intake["constraints"] = [{"value": "High stress caregiving load", "tier": "A"}]

        result = calculate_agency(intake)

        self.assertEqual(
            result["subscores"]["perceptual_latitude"]["caps_applied"],
            ["Tier A Cap: Social Isolation (Limit 12)"],
        )
        self.assertEqual(
            result["subscores"]["regulatory_bandwidth"]["caps_applied"],
            ["Tier A Cap: Allostatic Overload (Limit 8)"],
        )
        self.assertEqual(result["subscores"]["resource_access"]["caps_applied"], [])
        self.assertEqual(result["subscores"]["social_legibility"]["caps_applied"], [])

if __name__ == "__main__":
    unittest.main()
