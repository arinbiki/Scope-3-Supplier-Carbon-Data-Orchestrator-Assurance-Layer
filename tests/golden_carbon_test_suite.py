#!/usr/bin/env python3
"""
================================================================================
Golden Test Suite: Scope 3 Supplier Carbon Data Orchestrator & Assurance Layer
Path: tests/golden_carbon_test_suite.py
Architecture: Zero-LLM Deterministic Governance & Waterfall Engine
================================================================================
"""

import sys
import os
import unittest
import json
import hashlib

# Import the orchestrator script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "windmill")))
from non_violent_script import (
    main,
    validate_inbound_datapoint,
    route_and_calculate_datapoint,
    calculate_dqs_pedigree,
    detect_and_resolve_conflicts,
    calculate_cbam_exposure,
    perform_period_rollup,
    generate_assurance_pack,
    advance_engagement_fsm,
    transition_period_lock_fsm,
    BLACKBOARD,
    initialize_default_blackboard
)


class TestScope3CarbonOrchestrator(unittest.TestCase):

    def setUp(self):
        initialize_default_blackboard()

    def test_01_solar_vs_coal_site_divergence(self):
        """
        Golden Case 1: Proves the Reddit problem is solved.
        Nordic Green Steel (Sweden Wind/EAF) vs Silesian Blast Furnace (Poland Coal/BOF).
        Identical purchase: 1,000 MT of Hot Rolled Steel Coil.
        Must produce dramatically divergent emissions based on site-level truth, NOT blended supplier averages.
        """
        # Nordic Steel
        nordic_input = {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_NORDIC_STEEL",
            "site_id": "SITE_LULEA_EAF",
            "material_code": "MAT_STEEL_COIL",
            "quantity": 1000.0,
            "uom": "metric_ton",
            "boundary": "CRADLE_TO_GATE",
            "artifact_id": "ART_NORDIC_PCF_2025"
        }
        res_nordic = main("orchestrate_datapoint", nordic_input)
        self.assertTrue(res_nordic["success"])
        dp_nordic = res_nordic["datapoint"]
        self.assertEqual(dp_nordic["method_tier"], 2)
        self.assertEqual(dp_nordic["co2e_emissions_mt"], 380.0)
        self.assertEqual(dp_nordic["dqs"]["band"], "HIGH")

        # Silesian Steel (No valid PCF, default unverified site)
        silesian_input = {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_SILESIAN_STEEL",
            "site_id": "SITE_KATOWICE_BOF",
            "material_code": "MAT_STEEL_COIL",
            "quantity": 1000.0,
            "uom": "metric_ton",
            "boundary": "CRADLE_TO_GATE"
        }
        res_silesian = main("orchestrate_datapoint", silesian_input)
        self.assertTrue(res_silesian["success"])
        dp_silesian = res_silesian["datapoint"]
        self.assertGreater(dp_silesian["method_tier"], 2)
        self.assertGreater(dp_silesian["co2e_emissions_mt"], dp_nordic["co2e_emissions_mt"])
        print(f"\n[Test 1 PASSED] Solar/Wind Nordic: {dp_nordic['co2e_emissions_mt']} MT vs Coal Silesian: {dp_silesian['co2e_emissions_mt']} MT")

    def test_02_tier_1_primary_activity_routing(self):
        """
        Golden Case 2: Tier 1 Primary Activity Data Routing.
        Requires validated activity data, valid in-date artifact, and DQS <= 2.20.
        """
        raw_input = {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_NORDIC_STEEL",
            "site_id": "SITE_LULEA_EAF",
            "material_code": "MAT_STEEL_COIL",
            "quantity": 500.0,
            "uom": "metric_ton",
            "boundary": "CRADLE_TO_GATE",
            "artifact_id": "ART_NORDIC_PCF_2025",
            "has_primary_activity": True,
            "primary_activity_intensity_kg": 350.0
        }
        res = main("orchestrate_datapoint", raw_input)
        self.assertTrue(res["success"])
        dp = res["datapoint"]
        self.assertEqual(dp["method_tier"], 1)
        self.assertEqual(dp["tier_name"], "TIER_1_PRIMARY_ACTIVITY")
        self.assertEqual(dp["co2e_emissions_mt"], 175.0)
        self.assertFalse(dp["is_estimate"])
        print(f"[Test 2 PASSED] Tier 1 primary activity selected: {dp['co2e_emissions_mt']} MT (DQS {dp['dqs']['overall_dqs']})")

    def test_03_tier_2_pact_pcf_application(self):
        """
        Golden Case 3: Tier 2 PACT / ISO-14067 PCF Application.
        Apex Polymers HDPE with TÜV Rheinland ISO-14067 verification.
        """
        raw_input = {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_APEX_POLYMERS",
            "site_id": "SITE_JURONG_POLYMER",
            "material_code": "MAT_POLYMER_RESIN",
            "quantity": 200.0,
            "uom": "metric_ton",
            "boundary": "CRADLE_TO_GATE",
            "artifact_id": "ART_APEX_ISO14067"
        }
        res = main("orchestrate_datapoint", raw_input)
        self.assertTrue(res["success"])
        dp = res["datapoint"]
        self.assertEqual(dp["method_tier"], 2)
        self.assertEqual(dp["tier_name"], "TIER_2_SUPPLIER_PCF")
        self.assertEqual(dp["co2e_emissions_mt"], 250.0) # 200 MT * 1250 kg/MT / 1000
        print(f"[Test 3 PASSED] Tier 2 PCF verified: {dp['co2e_emissions_mt']} MT")

    def test_04_tier_3_hybrid_energy_mix(self):
        """
        Golden Case 4: Tier 3 Hybrid Energy Mix.
        Pacific Silicon Wafer with I-REC certificates and 65% renewable energy.
        """
        raw_input = {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_PACIFIC_WAFER",
            "site_id": "SITE_HSINCHU_FAB1",
            "material_code": "MAT_SILICON_WAFER",
            "quantity": 10000.0,
            "uom": "piece",
            "boundary": "CRADLE_TO_GATE",
            "artifact_id": "ART_PACIFIC_IREC_2025"
        }
        res = main("orchestrate_datapoint", raw_input)
        self.assertTrue(res["success"])
        dp = res["datapoint"]
        self.assertEqual(dp["method_tier"], 3)
        self.assertEqual(dp["tier_name"], "TIER_3_HYBRID")
        print(f"[Test 4 PASSED] Tier 3 Hybrid selected: {dp['co2e_emissions_mt']} MT")

    def test_05_tier_4_industry_average_factor_fallback(self):
        """
        Golden Case 5: Tier 4 Industry Average Factor Fallback.
        Corrugated cardboard boxes falling back to DEFRA 2024 library factor.
        """
        raw_input = {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_SHENZHEN_STAMPING",
            "site_id": "SITE_BAOAN_PLANT",
            "material_code": "MAT_CORRUGATED_BOX",
            "quantity": 50.0,
            "uom": "metric_ton",
            "boundary": "CRADLE_TO_GATE"
        }
        res = main("orchestrate_datapoint", raw_input)
        self.assertTrue(res["success"])
        dp = res["datapoint"]
        self.assertEqual(dp["method_tier"], 4)
        self.assertEqual(dp["tier_name"], "TIER_4_INDUSTRY_AVERAGE_FACTOR")
        self.assertTrue(dp["is_estimate"])
        self.assertEqual(dp["co2e_emissions_mt"], 40.5) # 50 MT * 810 kg/MT / 1000
        print(f"[Test 5 PASSED] Tier 4 Factor fallback: {dp['co2e_emissions_mt']} MT")

    def test_06_tier_5_spend_eeio_and_gap_closure_creation(self):
        """
        Golden Case 6: Tier 5 Spend-Based EEIO Fallback & Automated Gap Case.
        High-spend supplier with no activity data. Spend is deflated to 2021 USD,
        calculated via sector EEIO, and automatically triggers an open Gap-Closure Case.
        """
        raw_input = {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_SHENZHEN_STAMPING",
            "site_id": "SITE_BAOAN_PLANT",
            "material_code": "MAT_STEEL_COIL",
            "spend_amount": 500000.0, # $500,000 USD
            "currency": "USD",
            "transaction_year": "2025",
            "quantity": 0.0
        }
        res = main("orchestrate_datapoint", raw_input)
        self.assertTrue(res["success"])
        dp = res["datapoint"]
        self.assertEqual(dp["method_tier"], 5)
        self.assertEqual(dp["tier_name"], "TIER_5_SPEND_EEIO")
        self.assertTrue(dp["is_estimate"])
        self.assertTrue(dp["gap_closure_created"])
        
        # Verify Gap Case exists in blackboard
        gap_case = BLACKBOARD.engagements.get("GAP_SUPP_SHENZHEN_STAMPING_2025-Q4")
        self.assertIsNotNone(gap_case)
        self.assertEqual(gap_case["status"], "OPEN_GAP_CLOSURE")
        print(f"[Test 6 PASSED] Tier 5 Spend EEIO: {dp['co2e_emissions_mt']} MT. Gap-closure case created.")

    def test_07_conflict_detection_and_hierarchical_resolution(self):
        """
        Golden Case 7: Multi-source conflict detection (>20% variance) and resolution.
        CDP Self-Declaration (1,200 MT) vs Verified PCF (380 MT) for same supplier-site.
        Variance is >200%. Hierarchy selects the Verified Tier 2 PCF.
        """
        candidate_cdp = {
            "datapoint_id": "DP_CDP_1",
            "method_tier": 3,
            "co2e_emissions_mt": 1200.0,
            "artifact_hash": None,
            "dqs": {"overall_dqs": 3.4},
            "created_at": "2025-10-01"
        }
        candidate_pcf = {
            "datapoint_id": "DP_PCF_VERIFIED",
            "method_tier": 2,
            "co2e_emissions_mt": 380.0,
            "artifact_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            "dqs": {"overall_dqs": 1.14},
            "created_at": "2025-10-15"
        }

        res = detect_and_resolve_conflicts([candidate_cdp, candidate_pcf], variance_threshold_pct=20.0)
        self.assertTrue(res["has_conflict"])
        self.assertGreater(res["variance_pct"], 20.0)
        self.assertEqual(res["winner"]["datapoint_id"], "DP_PCF_VERIFIED")
        self.assertEqual(len(res["superseded"]), 1)
        print(f"[Test 7 PASSED] Conflict variance {res['variance_pct']}%. Winner: {res['winner']['datapoint_id']} (Tier {res['winner']['method_tier']})")

    def test_08_expired_certificate_downgrades_claim(self):
        """
        Golden Case 8: Expired Certificate Downgrades Claim.
        Silesian Steel submitting an expired 2023 certificate for 2025-Q4 period.
        System detects expiration and explicitly downgrades renewable claim to 0%.
        """
        raw_input = {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_SILESIAN_STEEL",
            "site_id": "SITE_KATOWICE_BOF",
            "material_code": "MAT_STEEL_COIL",
            "quantity": 1000.0,
            "uom": "metric_ton",
            "artifact_id": "ART_EXPIRED_CERT_SAMPLE" # Valid to 2023-12-31
        }
        res = main("orchestrate_datapoint", raw_input)
        self.assertTrue(res["success"])
        dp = res["datapoint"]
        self.assertIn("hybrid_cert_downgrade", dp["rejection_reasons"])
        print(f"[Test 8 PASSED] Expired cert detected: {dp['rejection_reasons']['hybrid_cert_downgrade']}")

    def test_09_unmapped_spend_rejection(self):
        """
        Golden Case 9: Unmapped Spend Rejection (Zero Silent Defaults).
        Unknown material code is rejected at Validation Gate 2; no silent defaults allowed.
        """
        raw_input = {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_NORDIC_STEEL",
            "site_id": "SITE_LULEA_EAF",
            "material_code": "MAT_UNKNOWN_UNOBTANIUM",
            "quantity": 100.0
        }
        res = main("orchestrate_datapoint", raw_input)
        self.assertFalse(res["success"])
        self.assertEqual(res["stage"], "VALIDATION_FAILED")
        print(f"[Test 9 PASSED] Unmapped material rejected with zero silent defaults: {res['errors']}")

    def test_10_double_count_reconciliation_guard(self):
        """
        Golden Case 10: Double-Count Reconciliation Guard.
        Ensures Sum(Cat 1..15) == Total Scope 3 Inventory with 0.00000000 MT delta.
        """
        # Ingest 3 diverse datapoints
        main("orchestrate_datapoint", {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_NORDIC_STEEL",
            "site_id": "SITE_LULEA_EAF",
            "material_code": "MAT_STEEL_COIL",
            "quantity": 1000.0,
            "artifact_id": "ART_NORDIC_PCF_2025"
        })
        main("orchestrate_datapoint", {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_APEX_POLYMERS",
            "site_id": "SITE_JURONG_POLYMER",
            "material_code": "MAT_POLYMER_RESIN",
            "quantity": 500.0,
            "artifact_id": "ART_APEX_ISO14067"
        })
        main("orchestrate_datapoint", {
            "period_id": "2025-Q4",
            "supplier_id": "SUPP_PACIFIC_WAFER",
            "site_id": "SITE_HSINCHU_FAB1",
            "material_code": "MAT_SILICON_WAFER",
            "quantity": 20000.0,
            "artifact_id": "ART_PACIFIC_IREC_2025"
        })

        rollup = perform_period_rollup("2025-Q4")
        reconciled = rollup["double_count_reconciliation"]["is_reconciled"]
        delta = rollup["double_count_reconciliation"]["reconciliation_delta_mt"]
        self.assertTrue(reconciled)
        self.assertAlmostEqual(delta, 0.0, places=6)
        print(f"[Test 10 PASSED] Double-counting reconciled. Total: {rollup['total_emissions_mt']} MT, Delta: {delta}")

    def test_11_auditor_assurance_pack_generation(self):
        """
        Golden Case 11: Auditor-Ready Assurance Pack Generation.
        Generates sealed pack with SHA-256 evidence chain and CSRD ESRS E1 format.
        """
        pack = generate_assurance_pack("2025-Q4", "PwC_LEAD_AUDITOR")
        self.assertTrue(pack["auditor_ready"])
        self.assertIsNotNone(pack["pack_hash_sha256"])
        self.assertEqual(len(pack["pack_hash_sha256"]), 64)
        esrs = pack["content"]["esrs_e1"]
        self.assertEqual(esrs["standard"], "CSRD_ESRS_E1_CLIMATE_CHANGE")
        print(f"[Test 11 PASSED] Assurance pack generated. SHA-256 Seal: {pack['pack_hash_sha256'][:16]}...")

    def test_12_period_hard_lock_governance_barrier(self):
        """
        Golden Case 12: Period Lock Governance Barrier.
        Direct mutation of a HARD_LOCKED period (2024-FY) is strictly blocked by the FSM.
        """
        blocked_input = {
            "period_id": "2024-FY", # Already HARD_LOCKED in seed
            "supplier_id": "SUPP_NORDIC_STEEL",
            "site_id": "SITE_LULEA_EAF",
            "material_code": "MAT_STEEL_COIL",
            "quantity": 100.0
        }
        val_res = validate_inbound_datapoint(blocked_input)
        self.assertEqual(val_res["status"], "REJECTED")
        self.assertTrue(any("HARD_LOCKED" in err for err in val_res["errors"]))
        print(f"[Test 12 PASSED] Hard-lock barrier enforced. Mutating 2024-FY rejected.")


if __name__ == "__main__":
    unittest.main()
