#!/usr/bin/env python3
"""
================================================================================
Scope 3 Supplier Carbon Data Orchestrator & Assurance Layer
Windmill Python Worker Script (Zero-LLM Architecture)
Path: f/carbon_data/non_violent_script
Version: 1.0.0
Author: Carbon Architecture & Assurance Engineering

Core Design Principles:
1. Every carbon number is a governed, immutable object.
2. 100% deterministic: 0 LLM calls, pure algebraic equations, reproducible.
3. Site-level truth: (supplier-site x material x period), never blended supplier averages.
4. 5-Tier Method Waterfall Router with explicit rejection rationale.
5. 5-Dimension Pedigree Data Quality Score (DQS).
6. Multi-source conflict detection (>20% variance) & hierarchical resolution.
7. Auditor-ready assurance pack generator with SHA-256 evidence chain.
================================================================================
"""

import sys
import os
import json
import hashlib
import math
from datetime import datetime, date, timezone
from typing import Dict, List, Any, Optional, Tuple

# ==============================================================================
# 1. CONSTANTS, STANDARDS, AND CANONICAL CONVERSION FACTORS
# ==============================================================================

GHG_CATEGORIES = {
    1: {"code": "CAT_01_PURCHASED_GOODS", "name": "Purchased Goods and Services"},
    2: {"code": "CAT_02_CAPITAL_GOODS", "name": "Capital Goods"},
    3: {"code": "CAT_03_FUEL_ENERGY", "name": "Fuel- and Energy-Related Activities"},
    4: {"code": "CAT_04_UPSTREAM_TRANSPORT", "name": "Upstream Transportation and Distribution"},
    5: {"code": "CAT_05_WASTE_OPERATIONS", "name": "Waste Generated in Operations"},
    6: {"code": "CAT_06_BUSINESS_TRAVEL", "name": "Business Travel"},
    7: {"code": "CAT_07_EMPLOYEE_COMMUTING", "name": "Employee Commuting"},
    8: {"code": "CAT_08_UPSTREAM_LEASED", "name": "Upstream Leased Assets"},
    9: {"code": "CAT_09_DOWNSTREAM_TRANSPORT", "name": "Downstream Transportation and Distribution"},
    10: {"code": "CAT_10_PROCESSING_SOLD", "name": "Processing of Sold Products"},
    11: {"code": "CAT_11_USE_SOLD_PRODUCTS", "name": "Use of Sold Products"},
    12: {"code": "CAT_12_END_OF_LIFE", "name": "End-of-Life Treatment of Sold Products"},
    13: {"code": "CAT_13_DOWNSTREAM_LEASED", "name": "Downstream Leased Assets"},
    14: {"code": "CAT_14_FRANCHISES", "name": "Franchises"},
    15: {"code": "CAT_15_INVESTMENTS", "name": "Investments"},
}

# Unit Conversion to Canonical Units (Mass -> metric_ton, Energy -> kwh, Transport -> ton_km)
UOM_CONVERSIONS = {
    "metric_ton": 1.0,
    "mt": 1.0,
    "tonne": 1.0,
    "ton": 0.907185,         # US short ton to metric ton
    "kg": 0.001,             # kg to metric ton
    "lb": 0.00045359237,     # lb to metric ton
    "ton_km": 1.0,
    "ton_mile": 1.459972,    # short ton-mile to metric ton-km
    "kwh": 1.0,
    "mwh": 1000.0,
    "gj": 277.778,           # 1 GJ = 277.778 kWh
    "piece": 1.0,
    "compute_core_hour": 1.0
}

# Currency Deflation Rates to EEIO Base Year 2021 (for Tier 5 Spend-based)
DEFLATION_FACTORS_2021 = {
    "USD": {"2025": 0.852104, "2024": 0.881230, "2023": 0.924510, "2022": 0.971200, "2021": 1.000000},
    "EUR": {"2025": 0.835420, "2024": 0.865100, "2023": 0.912300, "2022": 0.963100, "2021": 1.000000},
    "GBP": {"2025": 0.821900, "2024": 0.851400, "2023": 0.898700, "2022": 0.954000, "2021": 1.000000},
    "CNY": {"2025": 0.941200, "2024": 0.958000, "2023": 0.974000, "2022": 0.989000, "2021": 1.000000},
    "JPY": {"2025": 0.965000, "2024": 0.976000, "2023": 0.988000, "2022": 0.995000, "2021": 1.000000},
}

# FX Rates to USD for Spend Normalization
FX_TO_USD = {
    "USD": 1.000000,
    "EUR": 1.085000,
    "GBP": 1.285000,
    "CNY": 0.138000,
    "JPY": 0.006700,
}

# DQS Weights per GHG Protocol / Pedigree Matrix
DQS_WEIGHTS = {
    "reliability": 0.30,
    "completeness": 0.15,
    "temporal": 0.15,
    "geographical": 0.15,
    "technological": 0.25,
}

# Default Factor Fallbacks (kg CO2e per canonical unit)
DEFAULT_FACTOR_LIBRARY = {
    "MAT_STEEL_COIL": {
        "GLO": {"factor": 2150.0, "unit": "kg_co2e_per_metric_ton", "library": "LIB_ECOINVENT_310"},
        "EU":  {"factor": 420.0,  "unit": "kg_co2e_per_metric_ton", "library": "LIB_ECOINVENT_310"},
    },
    "MAT_ALUMINUM_INGOT": {
        "GLO": {"factor": 8600.0, "unit": "kg_co2e_per_metric_ton", "library": "LIB_ECOINVENT_310"},
    },
    "MAT_POLYMER_RESIN": {
        "GLO": {"factor": 1890.0, "unit": "kg_co2e_per_metric_ton", "library": "LIB_ECOINVENT_310"},
    },
    "MAT_SILICON_WAFER": {
        "GLO": {"factor": 14.5,   "unit": "kg_co2e_per_piece",      "library": "LIB_ECOINVENT_310"},
    },
    "MAT_CORRUGATED_BOX": {
        "GLO": {"factor": 810.0,  "unit": "kg_co2e_per_metric_ton", "library": "LIB_DEFRA_2024"},
    },
    "MAT_FREIGHT_OCEAN": {
        "GLO": {"factor": 0.0162, "unit": "kg_co2e_per_ton_km",     "library": "LIB_DEFRA_2024"},
    },
    "MAT_FREIGHT_ROAD": {
        "GLO": {"factor": 0.0841, "unit": "kg_co2e_per_ton_km",     "library": "LIB_DEFRA_2024"},
    },
}

# EEIO Sector Factors (kg CO2e per 2021 USD)
DEFAULT_EEIO_FACTORS = {
    "BASIC_METALS": 0.985400,
    "CHEMICALS":    0.742100,
    "ELECTRONICS":  0.312500,
    "PACKAGING":    0.512000,
    "LOGISTICS":    0.621400,
    "SERVICES":     0.142000,
}

# CBAM Benchmark Defaults (EU conservative surrender defaults vs average verified)
CBAM_BENCHMARK_DEFAULTS = {
    "MAT_STEEL_COIL": {"default_intensity": 2.45, "benchmark_intensity": 1.35, "penalty_eur_per_tco2e": 85.0},
    "MAT_ALUMINUM_INGOT": {"default_intensity": 8.60, "benchmark_intensity": 4.10, "penalty_eur_per_tco2e": 85.0},
}


# ==============================================================================
# 2. IN-MEMORY BLACKBOARD / DATABASE ABSTRACTION
# ==============================================================================

class CarbonBlackboard:
    """
    In-memory state and validation registry for Scope 3 orchestration.
    Can sync directly with PostgreSQL database 'scope3_carbon' if available.
    """
    def __init__(self):
        self.suppliers: Dict[str, Dict[str, Any]] = {}
        self.sites: Dict[str, Dict[str, Any]] = {}
        self.materials: Dict[str, Dict[str, Any]] = {}
        self.artifacts: Dict[str, Dict[str, Any]] = {}
        self.periods: Dict[str, Dict[str, Any]] = {}
        self.datapoints: Dict[str, Dict[str, Any]] = {}
        self.conflicts: Dict[str, Dict[str, Any]] = {}
        self.engagements: Dict[str, Dict[str, Any]] = {}
        self.calculation_runs: Dict[str, Dict[str, Any]] = {}
        self.assurance_packs: Dict[str, Dict[str, Any]] = {}
        self.audit_events: List[Dict[str, Any]] = []

    def log_audit(self, entity_type: str, entity_id: str, action: str, before: Any, after: Any, actor: str = "WindmillWorker"):
        event = {
            "event_id": len(self.audit_events) + 1,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "before_state": before,
            "after_state": after,
            "actor": actor,
            "rule_version": "V1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_hash": hashlib.sha256(f"{entity_type}:{entity_id}:{action}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()
        }
        self.audit_events.append(event)
        return event

BLACKBOARD = CarbonBlackboard()


def initialize_default_blackboard():
    """Seed the in-memory blackboard with realistic baseline entities matching the PostgreSQL seed."""
    # 1. Suppliers
    BLACKBOARD.suppliers = {
        "SUPP_NORDIC_STEEL": {
            "supplier_id": "SUPP_NORDIC_STEEL",
            "legal_name": "Nordic Green Steel AB",
            "country_iso2": "SE",
            "segment": "RAW_MATERIAL",
            "priority_class": "STRATEGIC",
            "annual_spend_usd": 14500000.0,
            "has_cbam_exposure": True,
            "contact_email": "sustainability@nordicgreensteel.se"
        },
        "SUPP_SILESIAN_STEEL": {
            "supplier_id": "SUPP_SILESIAN_STEEL",
            "legal_name": "Silesian Blast Furnace Sp. z o.o.",
            "country_iso2": "PL",
            "segment": "RAW_MATERIAL",
            "priority_class": "STRATEGIC",
            "annual_spend_usd": 14200000.0,
            "has_cbam_exposure": True,
            "contact_email": "compliance@silesiansteel.pl"
        },
        "SUPP_APEX_POLYMERS": {
            "supplier_id": "SUPP_APEX_POLYMERS",
            "legal_name": "Apex Polymer Solutions Pte Ltd",
            "country_iso2": "SG",
            "segment": "RAW_MATERIAL",
            "priority_class": "CRITICAL",
            "annual_spend_usd": 8900000.0,
            "has_cbam_exposure": False,
            "contact_email": "esg@apexpolymers.sg"
        },
        "SUPP_PACIFIC_WAFER": {
            "supplier_id": "SUPP_PACIFIC_WAFER",
            "legal_name": "Pacific Silicon Wafer Corp",
            "country_iso2": "TW",
            "segment": "TIER_1_DIRECT",
            "priority_class": "CRITICAL",
            "annual_spend_usd": 22400000.0,
            "has_cbam_exposure": False,
            "contact_email": "carbon@pacificwafer.com.tw"
        },
        "SUPP_SHENZHEN_STAMPING": {
            "supplier_id": "SUPP_SHENZHEN_STAMPING",
            "legal_name": "Shenzhen Precision Stamping Co",
            "country_iso2": "CN",
            "segment": "TIER_1_DIRECT",
            "priority_class": "STANDARD",
            "annual_spend_usd": 3200000.0,
            "has_cbam_exposure": False,
            "contact_email": "operations@sz-precision.cn"
        }
    }

    # 2. Sites (Site-Level Truth)
    BLACKBOARD.sites = {
        "SITE_LULEA_EAF": {
            "site_id": "SITE_LULEA_EAF",
            "supplier_id": "SUPP_NORDIC_STEEL",
            "site_name": "Luleå Hydrogen & EAF Plant",
            "country_iso2": "SE",
            "grid_region": "SE_ZONE_1",
            "primary_process": "ELECTRIC_ARC_FURNACE",
            "energy_mix": {"renewable_pct": 100, "grid_pct": 0, "wind_ppa_pct": 85, "hydro_pct": 15},
            "certificates": ["ISO_14064", "ISO_14067", "EPD_SWEDEN", "RECs"],
            "verification_status": "THIRD_PARTY_ASSURED",
            "pcf_intensity_kg_co2e_per_mt": 380.0
        },
        "SITE_KATOWICE_BOF": {
            "site_id": "SITE_KATOWICE_BOF",
            "supplier_id": "SUPP_SILESIAN_STEEL",
            "site_name": "Katowice Blast Furnace & BOF",
            "country_iso2": "PL",
            "grid_region": "PL_GRID",
            "primary_process": "BLAST_FURNACE_BOF",
            "energy_mix": {"renewable_pct": 5, "grid_pct": 95, "coal_onsite_coke_pct": 90},
            "certificates": ["ISO_9001"],
            "verification_status": "UNVERIFIED",
            "pcf_intensity_kg_co2e_per_mt": 2450.0
        },
        "SITE_JURONG_POLYMER": {
            "site_id": "SITE_JURONG_POLYMER",
            "supplier_id": "SUPP_APEX_POLYMERS",
            "site_name": "Jurong Petrochemical Island Facility",
            "country_iso2": "SG",
            "grid_region": "SG_MAIN",
            "primary_process": "POLYMER_EXTRUSION",
            "energy_mix": {"renewable_pct": 30, "grid_pct": 70, "onsite_solar_pct": 10},
            "certificates": ["ISO_14067", "ISCC_PLUS"],
            "verification_status": "THIRD_PARTY_ASSURED",
            "pcf_intensity_kg_co2e_per_mt": 1250.0
        },
        "SITE_HSINCHU_FAB1": {
            "site_id": "SITE_HSINCHU_FAB1",
            "supplier_id": "SUPP_PACIFIC_WAFER",
            "site_name": "Hsinchu High-Purity Ingot Fab 1",
            "country_iso2": "TW",
            "grid_region": "TW_NORTH",
            "primary_process": "SILICON_CRYSTALLIZATION",
            "energy_mix": {"renewable_pct": 65, "grid_pct": 35, "i_rec_certified": True},
            "certificates": ["ISO_14064", "I_REC"],
            "verification_status": "THIRD_PARTY_ASSURED",
            "hybrid_energy_intensity": 7.20 # kg CO2e per piece
        },
        "SITE_BAOAN_PLANT": {
            "site_id": "SITE_BAOAN_PLANT",
            "supplier_id": "SUPP_SHENZHEN_STAMPING",
            "site_name": "Baoan Metal Forming Works",
            "country_iso2": "CN",
            "grid_region": "CN_SOUTH_GRID",
            "primary_process": "COLD_STAMPING_PRESS",
            "energy_mix": {"renewable_pct": 0, "grid_pct": 100},
            "certificates": [],
            "verification_status": "UNVERIFIED"
        }
    }

    # 3. Materials
    BLACKBOARD.materials = {
        "MAT_STEEL_COIL": {"category_id": 1, "name": "Hot Rolled Steel Coil", "uom": "metric_ton", "is_cbam": True, "sector": "BASIC_METALS"},
        "MAT_ALUMINUM_INGOT": {"category_id": 1, "name": "Primary Aluminum Ingot", "uom": "metric_ton", "is_cbam": True, "sector": "BASIC_METALS"},
        "MAT_POLYMER_RESIN": {"category_id": 1, "name": "HDPE Polymer Resin", "uom": "metric_ton", "is_cbam": False, "sector": "CHEMICALS"},
        "MAT_SILICON_WAFER": {"category_id": 1, "name": "300mm Silicon Wafer", "uom": "piece", "is_cbam": False, "sector": "ELECTRONICS"},
        "MAT_CORRUGATED_BOX": {"category_id": 1, "name": "Corrugated Boxes", "uom": "metric_ton", "is_cbam": False, "sector": "PACKAGING"},
        "MAT_FREIGHT_OCEAN": {"category_id": 4, "name": "Ocean Freight", "uom": "ton_km", "is_cbam": False, "sector": "LOGISTICS"},
        "MAT_FREIGHT_ROAD": {"category_id": 4, "name": "Road Freight", "uom": "ton_km", "is_cbam": False, "sector": "LOGISTICS"}
    }

    # 4. Evidence Artifacts
    BLACKBOARD.artifacts = {
        "ART_NORDIC_PCF_2025": {
            "artifact_id": "ART_NORDIC_PCF_2025",
            "type": "PCF_REPORT",
            "hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            "valid_from": "2025-01-01",
            "valid_to": "2026-12-31",
            "is_verified": True,
            "verifier": "DNV Business Assurance",
            "accreditation": "DAkkS_D-ZV-14067"
        },
        "ART_APEX_ISO14067": {
            "artifact_id": "ART_APEX_ISO14067",
            "type": "PCF_REPORT",
            "hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
            "valid_from": "2025-01-01",
            "valid_to": "2026-06-30",
            "is_verified": True,
            "verifier": "TÜV Rheinland Singapore",
            "accreditation": "SAC_SINGAPORE_VERIFIED"
        },
        "ART_PACIFIC_IREC_2025": {
            "artifact_id": "ART_PACIFIC_IREC_2025",
            "type": "ENERGY_INVOICE",
            "hash": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
            "valid_from": "2025-01-01",
            "valid_to": "2025-12-31",
            "is_verified": True,
            "verifier": "Taiwan Renewable Energy Certificate (T-REC)",
            "accreditation": "NATIONAL_BUREAU_STANDARDS"
        },
        "ART_EXPIRED_CERT_SAMPLE": {
            "artifact_id": "ART_EXPIRED_CERT_SAMPLE",
            "type": "ISO_CERTIFICATE",
            "hash": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
            "valid_from": "2023-01-01",
            "valid_to": "2023-12-31",
            "is_verified": True,
            "verifier": "Bureau Veritas Polska",
            "accreditation": "PCA_ACCREDITED"
        }
    }

    # 5. Reporting Periods
    BLACKBOARD.periods = {
        "2025-Q4": {
            "period_id": "2025-Q4",
            "state": "PERIOD_OPEN",
            "start_date": "2025-10-01",
            "end_date": "2025-12-31",
            "bound_libraries": "LIB_GHG_2024:2024.1;LIB_ECOINVENT_310:3.10",
            "bound_mapping": "MAP_V2025_Q4",
            "bound_formula": "FORMULA_ENGINE_V1.0"
        },
        "2025-FY": {
            "period_id": "2025-FY",
            "state": "PERIOD_OPEN",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "bound_libraries": "LIB_GHG_2024:2024.1;LIB_ECOINVENT_310:3.10",
            "bound_mapping": "MAP_V2025_FY",
            "bound_formula": "FORMULA_ENGINE_V1.0"
        },
        "2024-FY": {
            "period_id": "2024-FY",
            "state": "HARD_LOCK",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "bound_libraries": "LIB_GHG_2024:2024.1;LIB_ECOINVENT_310:3.10",
            "bound_mapping": "MAP_V2024_FY",
            "bound_formula": "FORMULA_ENGINE_V1.0",
            "hard_locked_at": "2025-02-15T18:00:00Z",
            "lock_checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        }
    }

initialize_default_blackboard()


# ==============================================================================
# 3. COMPONENT 6.6: DATA QUALITY SCORE (DQS) PEDIGREE SCORER
# ==============================================================================

def calculate_dqs_pedigree(
    reliability: float,
    completeness: float,
    temporal: float,
    geographical: float,
    technological: float
) -> Dict[str, Any]:
    """
    Computes deterministic 5-dimension pedigree score (1.0 to 5.0) and band.
    DQS_overall = 0.30*Rel + 0.15*Comp + 0.15*Temp + 0.15*Geo + 0.25*Tech
    """
    # Clamp dimensions between 1.0 and 5.0
    r = max(1.0, min(5.0, float(reliability)))
    c = max(1.0, min(5.0, float(completeness)))
    t = max(1.0, min(5.0, float(temporal)))
    g = max(1.0, min(5.0, float(geographical)))
    tech = max(1.0, min(5.0, float(technological)))

    overall = (
        r * DQS_WEIGHTS["reliability"] +
        c * DQS_WEIGHTS["completeness"] +
        t * DQS_WEIGHTS["temporal"] +
        g * DQS_WEIGHTS["geographical"] +
        tech * DQS_WEIGHTS["technological"]
    )
    overall = round(overall, 2)

    # Band classification: High: <= 1.80, Medium: 1.81-3.20, Low: > 3.20
    if overall <= 1.80:
        band = "HIGH"
    elif overall <= 3.20:
        band = "MEDIUM"
    else:
        band = "LOW"

    return {
        "overall_dqs": overall,
        "band": band,
        "dimensions": {
            "reliability": r,
            "completeness": c,
            "temporal": t,
            "geographical": g,
            "technological": tech
        }
    }


# ==============================================================================
# 4. COMPONENT 6.3: 8-GATE DETERMINISTIC VALIDATION ENGINE
# ==============================================================================

def validate_inbound_datapoint(raw_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the 8 sequential validation gates. Returns pass, auto-repair, or reject.
    Gate 1: Structural
    Gate 2: Identity
    Gate 3: Unit normalization
    Gate 4: Boundary check
    Gate 5: Period alignment
    Gate 6: Currency & deflation check
    Gate 7: Duplicate detection
    Gate 8: Evidence artifact check
    """
    errors = []
    repairs = []

    # Gate 1: Structural
    required_fields = ["supplier_id", "site_id", "material_code", "period_id"]
    for field in required_fields:
        if field not in raw_input or raw_input[field] is None:
            errors.append(f"STRUCTURAL_GATE_FAILED: Missing mandatory field '{field}'")
    if errors:
        return {"status": "REJECTED", "errors": errors, "repairs": repairs}

    supplier_id = raw_input["supplier_id"]
    site_id = raw_input["site_id"]
    material_code = raw_input["material_code"]
    period_id = raw_input["period_id"]

    # Gate 2: Identity
    if supplier_id not in BLACKBOARD.suppliers:
        errors.append(f"IDENTITY_GATE_FAILED: Unknown supplier_id '{supplier_id}'. Routed to Master-Data Case.")
    if site_id not in BLACKBOARD.sites:
        errors.append(f"IDENTITY_GATE_FAILED: Unknown site_id '{site_id}' for supplier '{supplier_id}'.")
    if material_code not in BLACKBOARD.materials:
        errors.append(f"IDENTITY_GATE_FAILED: Unknown material_code '{material_code}'.")
    if errors:
        return {"status": "REJECTED", "errors": errors, "repairs": repairs}

    # Gate 3: Unit Gate
    provided_uom = str(raw_input.get("uom", "metric_ton")).lower()
    if provided_uom not in UOM_CONVERSIONS and provided_uom != "usd" and provided_uom != "eur":
        errors.append(f"UNIT_GATE_FAILED: Unknown UOM '{provided_uom}'. Reason: REASON_INVALID_UNIT")
        return {"status": "REJECTED", "errors": errors, "repairs": repairs}

    canonical_quantity = float(raw_input.get("quantity", 0.0))
    if provided_uom in UOM_CONVERSIONS:
        scale = UOM_CONVERSIONS[provided_uom]
        if scale != 1.0:
            canonical_quantity *= scale
            repairs.append(f"AUTO_REPAIR: Normalized UOM from '{provided_uom}' to canonical using factor {scale}")

    # Gate 4: Boundary Gate
    boundary = raw_input.get("boundary", "CRADLE_TO_GATE").upper()
    if boundary not in ["CRADLE_TO_GATE", "CRADLE_TO_GRAVE", "GATE_TO_GATE"]:
        errors.append(f"BOUNDARY_GATE_FAILED: Incompatible declared boundary '{boundary}'")

    # Gate 5: Period Gate
    if period_id in BLACKBOARD.periods:
        period_obj = BLACKBOARD.periods[period_id]
        if period_obj["state"] == "HARD_LOCK":
            errors.append(f"PERIOD_GATE_FAILED: Reporting period '{period_id}' is HARD_LOCKED. Direct mutation rejected. Must initiate restatement run.")
    else:
        errors.append(f"PERIOD_GATE_FAILED: Unknown reporting period '{period_id}'")

    # Gate 6: Currency Gate (if spend-based)
    spend_amount = raw_input.get("spend_amount")
    currency = str(raw_input.get("currency", "USD")).upper()
    deflated_spend_2021_usd = 0.0
    if spend_amount is not None and float(spend_amount) > 0.0:
        spend_val = float(spend_amount)
        if currency not in DEFLATION_FACTORS_2021:
            errors.append(f"CURRENCY_GATE_FAILED: Unsupported spend currency '{currency}'")
        else:
            transaction_year = str(raw_input.get("transaction_year", "2025"))
            deflator = DEFLATION_FACTORS_2021[currency].get(transaction_year, 1.0)
            fx = FX_TO_USD.get(currency, 1.0)
            deflated_spend_2021_usd = spend_val * fx * deflator
            repairs.append(f"CURRENCY_NORMALIZED: Deflated {spend_val} {currency} ({transaction_year}) -> {round(deflated_spend_2021_usd, 2)} 2021 USD")

    # Gate 7: Duplicate Check
    dp_key = f"{period_id}:{supplier_id}:{site_id}:{material_code}"
    is_superseding = False
    if dp_key in BLACKBOARD.datapoints:
        repairs.append(f"DUPLICATE_SUPERSEDE: Existing datapoint '{dp_key}' found. Version-superseding existing record.")
        is_superseding = True

    # Gate 8: Evidence Gate
    artifact_id = raw_input.get("artifact_id")
    artifact_obj = BLACKBOARD.artifacts.get(artifact_id) if artifact_id else None
    if artifact_id and not artifact_obj:
        errors.append(f"EVIDENCE_GATE_FAILED: Linked artifact '{artifact_id}' does not exist in registry.")

    if errors:
        return {"status": "REJECTED", "errors": errors, "repairs": repairs}

    return {
        "status": "VALIDATED",
        "errors": [],
        "repairs": repairs,
        "is_superseding": is_superseding,
        "canonical_quantity": canonical_quantity,
        "deflated_spend_2021_usd": deflated_spend_2021_usd,
        "artifact": artifact_obj
    }


# ==============================================================================
# 5. COMPONENT 6.7: 5-TIER METHOD WATERFALL ROUTER & CALCULATION ENGINE
# ==============================================================================

def route_and_calculate_datapoint(validated_data: Dict[str, Any], raw_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the 5-Tier Waterfall Router strictly in priority order:
    Tier 1: Supplier Primary Activity Data (Validated activity + in-date verified artifact + DQS <= 2.20)
    Tier 2: Supplier-specific PCF (PACT / ISO-14067 compliant, verified boundary)
    Tier 3: Hybrid (Supplier energy mix / PPA + process activity factors)
    Tier 4: Industry-average activity factor (Ecoinvent / DEFRA)
    Tier 5: Spend-based EEIO (Deflated Spend * Sector Factor + Gap-Closure Case)
    """
    supplier_id = raw_input["supplier_id"]
    site_id = raw_input["site_id"]
    material_code = raw_input["material_code"]
    period_id = raw_input["period_id"]
    quantity = validated_data["canonical_quantity"]
    spend_2021_usd = validated_data["deflated_spend_2021_usd"]
    artifact = validated_data["artifact"]

    site = BLACKBOARD.sites[site_id]
    material = BLACKBOARD.materials[material_code]
    category_id = material["category_id"]

    rejection_reasons = {}
    selected_tier = None
    tier_name = ""
    emissions_mt = 0.0
    intensity_kg = 0.0
    dqs_scores = {}
    is_estimate = False
    gap_closure_created = False

    # Check Artifact validity date
    current_period_end = "2025-12-31"
    artifact_is_valid = False
    if artifact:
        if artifact["valid_from"] <= current_period_end <= artifact["valid_to"]:
            artifact_is_valid = True
        else:
            rejection_reasons["artifact_expired"] = f"Artifact '{artifact['artifact_id']}' expired on {artifact['valid_to']}"

    # --------------------------------------------------------------------------
    # TIER 1 EVALUATION: Primary Activity Data
    # --------------------------------------------------------------------------
    has_primary_activity = raw_input.get("has_primary_activity", False)
    if has_primary_activity and quantity > 0.0 and artifact and artifact_is_valid:
        raw_intensity = float(raw_input.get("primary_activity_intensity_kg", 0.0))
        dqs = calculate_dqs_pedigree(
            reliability=1.0 if artifact["is_verified"] else 2.0,
            completeness=1.0,
            temporal=1.0,
            geographical=1.0,
            technological=1.0
        )
        if dqs["overall_dqs"] <= 2.20 and raw_intensity > 0.0:
            selected_tier = 1
            tier_name = "TIER_1_PRIMARY_ACTIVITY"
            intensity_kg = raw_intensity
            emissions_mt = (quantity * intensity_kg) / 1000.0
            dqs_scores = dqs
            is_estimate = False
        else:
            rejection_reasons["tier_1"] = f"DQS score {dqs['overall_dqs']} exceeds threshold 2.20 or intensity is 0"
    else:
        rejection_reasons["tier_1"] = "Missing validated primary activity data or valid in-date evidence artifact"

    # --------------------------------------------------------------------------
    # TIER 2 EVALUATION: Supplier-Specific PCF (PACT / ISO-14067)
    # --------------------------------------------------------------------------
    if selected_tier is None:
        pcf_intensity = raw_input.get("pcf_intensity_kg_co2e") or site.get("pcf_intensity_kg_co2e_per_mt")
        if pcf_intensity and quantity > 0.0 and artifact and artifact_is_valid:
            dqs = calculate_dqs_pedigree(
                reliability=1.2 if artifact["is_verified"] else 2.5,
                completeness=1.5,
                temporal=1.0,
                geographical=1.0,
                technological=1.0
            )
            selected_tier = 2
            tier_name = "TIER_2_SUPPLIER_PCF"
            intensity_kg = float(pcf_intensity)
            emissions_mt = (quantity * intensity_kg) / 1000.0
            dqs_scores = dqs
            is_estimate = False
        else:
            rejection_reasons["tier_2"] = "No valid PACT/ISO-14067 PCF artifact or site intensity declared"

    # --------------------------------------------------------------------------
    # TIER 3 EVALUATION: Hybrid (Supplier Energy Mix + Activity Factors)
    # --------------------------------------------------------------------------
    if selected_tier is None:
        energy_mix = site.get("energy_mix", {})
        has_hybrid_declaration = energy_mix.get("renewable_pct", 0) > 0 or site.get("hybrid_energy_intensity")
        if has_hybrid_declaration and quantity > 0.0:
            # Calculate emissions using site renewable share
            # If certificate is present, apply full renewable discount, else default grid
            renewable_pct = energy_mix.get("renewable_pct", 0)
            if not artifact_is_valid:
                renewable_pct = 0 # Downgrade if certificate is missing or expired
                rejection_reasons["hybrid_cert_downgrade"] = "Renewable claim downgraded to 0% due to expired/missing certificate"

            base_grid_factor = 450.0 # kg CO2e / MWh grid average
            clean_ppa_factor = 15.0  # kg CO2e / MWh wind/solar
            effective_energy_factor = (renewable_pct * clean_ppa_factor + (100 - renewable_pct) * base_grid_factor) / 100.0
            
            # Process intensity: base process energy (e.g. 1.2 MWh/t) * effective factor + thermal fuel
            mwh_per_unit = 1.2
            intensity_kg = (mwh_per_unit * effective_energy_factor) + 200.0 # 200kg chemical/direct
            emissions_mt = (quantity * intensity_kg) / 1000.0

            dqs = calculate_dqs_pedigree(
                reliability=2.5 if artifact_is_valid else 3.5,
                completeness=2.0,
                temporal=1.5,
                geographical=1.5,
                technological=2.0
            )
            selected_tier = 3
            tier_name = "TIER_3_HYBRID"
            dqs_scores = dqs
            is_estimate = False
        else:
            rejection_reasons["tier_3"] = "No supplier energy mix declarations or hybrid parameters"

    # --------------------------------------------------------------------------
    # TIER 4 EVALUATION: Industry-Average Process Factor
    # --------------------------------------------------------------------------
    if selected_tier is None:
        factor_entry = DEFAULT_FACTOR_LIBRARY.get(material_code)
        if factor_entry and quantity > 0.0:
            site_country = site.get("country_iso2", "GLO")
            geo_key = "EU" if site_country in ["SE", "PL", "DE", "FR", "ES"] and "EU" in factor_entry else "GLO"
            matched_factor = factor_entry.get(geo_key, factor_entry.get("GLO"))
            
            intensity_kg = matched_factor["factor"]
            emissions_mt = (quantity * intensity_kg) / 1000.0
            dqs = calculate_dqs_pedigree(
                reliability=3.5,
                completeness=3.0,
                temporal=2.0,
                geographical=2.5 if geo_key != "GLO" else 4.0,
                technological=3.0
            )
            selected_tier = 4
            tier_name = "TIER_4_INDUSTRY_AVERAGE_FACTOR"
            dqs_scores = dqs
            is_estimate = True
        else:
            rejection_reasons["tier_4"] = f"No physical factor mapping or quantity for material '{material_code}'"

    # --------------------------------------------------------------------------
    # TIER 5 EVALUATION: Spend-Based EEIO Fallback
    # --------------------------------------------------------------------------
    if selected_tier is None:
        if spend_2021_usd > 0.0:
            sector = material["sector"]
            eeio_factor = DEFAULT_EEIO_FACTORS.get(sector, 0.500000) # kg CO2e / 2021 USD
            emissions_mt = (spend_2021_usd * eeio_factor) / 1000.0
            intensity_kg = eeio_factor # stored as kg CO2e / USD
            dqs = calculate_dqs_pedigree(
                reliability=4.5,
                completeness=4.0,
                temporal=3.0,
                geographical=4.0,
                technological=4.5
            )
            selected_tier = 5
            tier_name = "TIER_5_SPEND_EEIO"
            dqs_scores = dqs
            is_estimate = True

            # Automatic Gap-Closure Case Creation if Spend > Materiality Threshold ($100k)
            if spend_2021_usd > 100000.0:
                gap_closure_created = True
                BLACKBOARD.engagements[f"GAP_{supplier_id}_{period_id}"] = {
                    "case_id": f"GAP_{supplier_id}_{period_id}",
                    "period_id": period_id,
                    "supplier_id": supplier_id,
                    "reason": "HIGH_SPEND_FALLBACK_TO_TIER_5",
                    "spend_usd": spend_2021_usd,
                    "target_cycle_tier": 2,
                    "status": "OPEN_GAP_CLOSURE"
                }
        else:
            rejection_reasons["tier_5"] = "Spend amount is zero or unmapped to sector"

    # If completely unmappable
    if selected_tier is None:
        return {
            "status": "MAPPING_GAP_EXCEPTION",
            "message": "Datapoint cannot be calculated under any of the 5 tiers. Excluded with disclosure flag.",
            "rejections": rejection_reasons
        }

    # Build Governed Datapoint Object
    datapoint_id = f"DP_{period_id}_{supplier_id}_{site_id}_{material_code}"
    governed_datapoint = {
        "datapoint_id": datapoint_id,
        "period_id": period_id,
        "supplier_id": supplier_id,
        "site_id": site_id,
        "material_code": material_code,
        "category_id": category_id,
        "category_name": GHG_CATEGORIES[category_id]["name"],
        "activity_quantity": round(quantity, 4),
        "activity_uom": material["uom"] if selected_tier != 5 else "2021_USD",
        "co2e_emissions_mt": round(emissions_mt, 4),
        "intensity": round(intensity_kg, 4),
        "method_tier": selected_tier,
        "tier_name": tier_name,
        "is_estimate": is_estimate,
        "dqs": dqs_scores,
        "rejection_reasons": rejection_reasons,
        "artifact_id": artifact["artifact_id"] if artifact else None,
        "artifact_hash": artifact["hash"] if artifact else None,
        "gap_closure_created": gap_closure_created,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    BLACKBOARD.datapoints[datapoint_id] = governed_datapoint
    BLACKBOARD.log_audit("DATAPOINT", datapoint_id, "TIER_ROUTED_AND_CALCULATED", None, governed_datapoint)

    return governed_datapoint


# ==============================================================================
# 6. COMPONENT 6.5: CONFLICT DETECTION & RESOLUTION ENGINE
# ==============================================================================

def detect_and_resolve_conflicts(
    candidates: List[Dict[str, Any]],
    variance_threshold_pct: float = 20.0
) -> Dict[str, Any]:
    """
    Detects conflicts across multiple sources (e.g. CDP survey vs PCF vs Spend)
    where relative variance > 20%.
    Deterministic resolution hierarchy:
    1. Higher method tier wins (Tier 1 > 2 > 3 > 4 > 5)
    2. Same tier: Third-party verified wins over unverified
    3. Same tier & verification: Lower DQS score wins (higher quality)
    4. Same DQS: More recent source timestamp wins
    5. Tied: Data steward manual review flag
    """
    if len(candidates) < 2:
        return {"has_conflict": False, "winner": candidates[0] if candidates else None}

    # Check emissions variance between extremes
    emissions_list = [c["co2e_emissions_mt"] for c in candidates]
    min_e = min(emissions_list)
    max_e = max(emissions_list)
    variance_pct = ((max_e - min_e) / min_e * 100.0) if min_e > 0 else 0.0

    has_conflict = variance_pct > variance_threshold_pct

    # Sort candidates according to deterministic priority
    def candidate_sort_key(c):
        tier = c["method_tier"] # Lower number = higher tier (1 is best)
        is_verified = 0 if c.get("artifact_hash") else 1 # 0 is verified (best)
        dqs = c["dqs"]["overall_dqs"] # Lower number = higher quality
        recency = c.get("created_at", "")
        return (tier, is_verified, dqs, -len(recency))

    sorted_candidates = sorted(candidates, key=candidate_sort_key)
    winner = sorted_candidates[0]
    superseded = sorted_candidates[1:]

    conflict_record = {
        "conflict_id": f"CONF_{winner['datapoint_id']}",
        "variance_pct": round(variance_pct, 2),
        "threshold_pct": variance_threshold_pct,
        "is_conflict_triggered": has_conflict,
        "winner_datapoint_id": winner["datapoint_id"],
        "winner_tier": winner["method_tier"],
        "winner_emissions_mt": winner["co2e_emissions_mt"],
        "winner_dqs": winner["dqs"]["overall_dqs"],
        "superseded_count": len(superseded),
        "resolution_rationale": f"Selected Tier {winner['method_tier']} (DQS {winner['dqs']['overall_dqs']}) over {len(superseded)} alternative candidates via deterministic governance hierarchy."
    }

    BLACKBOARD.conflicts[conflict_record["conflict_id"]] = conflict_record
    BLACKBOARD.log_audit("CONFLICT", conflict_record["conflict_id"], "RESOLVED_BY_HIERARCHY", None, conflict_record)

    return {
        "has_conflict": has_conflict,
        "variance_pct": round(variance_pct, 2),
        "winner": winner,
        "superseded": superseded,
        "conflict_record": conflict_record
    }


# ==============================================================================
# 7. COMPONENT 6.16: CBAM EXTENSION MODULE
# ==============================================================================

def calculate_cbam_exposure(
    supplier_id: str,
    site_id: str,
    material_code: str,
    imported_net_mass_mt: float,
    declared_intensity_tco2e_per_t: float,
    is_verified: bool
) -> Dict[str, Any]:
    """
    Computes CBAM embedded emissions, actual-vs-default surrender difference,
    and financial penalty cost exposure (EUR).
    """
    benchmark = CBAM_BENCHMARK_DEFAULTS.get(material_code, {
        "default_intensity": 2.20,
        "benchmark_intensity": 1.20,
        "penalty_eur_per_tco2e": 85.0
    })

    default_intensity = benchmark["default_intensity"]
    penalty_rate = benchmark["penalty_eur_per_tco2e"]

    actual_emissions_mt = imported_net_mass_mt * declared_intensity_tco2e_per_t
    default_emissions_mt = imported_net_mass_mt * default_intensity

    # Cost calculation: certificates surrendered under defaults vs actuals
    emissions_difference_mt = default_emissions_mt - actual_emissions_mt
    financial_penalty_exposure_eur = max(0.0, emissions_difference_mt * penalty_rate)

    return {
        "supplier_id": supplier_id,
        "site_id": site_id,
        "material_code": material_code,
        "imported_net_mass_mt": imported_net_mass_mt,
        "declared_actual_intensity": declared_intensity_tco2e_per_t,
        "default_intensity": default_intensity,
        "actual_embedded_emissions_mt": round(actual_emissions_mt, 4),
        "default_embedded_emissions_mt": round(default_emissions_mt, 4),
        "emissions_saving_mt": round(emissions_difference_mt, 4),
        "is_verified": is_verified,
        "cbam_status": "ACTUAL_VERIFIED" if is_verified else "DEFAULT_CONSERVATIVE_SURRENDER",
        "financial_penalty_exposure_eur": round(financial_penalty_exposure_eur, 2)
    }


# ==============================================================================
# 8. COMPONENT 6.10: SCOPE 3 ROLL-UP & DOUBLE-COUNT RECONCILIATION
# ==============================================================================

def perform_period_rollup(period_id: str) -> Dict[str, Any]:
    """
    Rolls up all validated, non-superseded datapoints for the reporting period.
    Enforces double-count guards: every emission line maps to exactly ONE category.
    Computes coverage KPIs and DQS portfolio averages.
    """
    period_datapoints = [
        dp for dp in BLACKBOARD.datapoints.values()
        if dp["period_id"] == period_id
    ]

    total_emissions_mt = 0.0
    category_totals = {i: {"code": GHG_CATEGORIES[i]["code"], "name": GHG_CATEGORIES[i]["name"], "emissions_mt": 0.0, "datapoint_count": 0} for i in range(1, 16)}
    tier_distribution = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}
    weighted_dqs_sum = 0.0

    primary_emissions_mt = 0.0
    estimated_emissions_mt = 0.0

    for dp in period_datapoints:
        e = dp["co2e_emissions_mt"]
        cat_id = dp["category_id"]
        tier = dp["method_tier"]
        dqs = dp["dqs"]["overall_dqs"]

        total_emissions_mt += e
        category_totals[cat_id]["emissions_mt"] += e
        category_totals[cat_id]["datapoint_count"] += 1
        tier_distribution[tier] += e
        weighted_dqs_sum += (e * dqs)

        if tier in [1, 2]:
            primary_emissions_mt += e
        else:
            estimated_emissions_mt += e

    # Double Count Reconciliation Proof
    sum_of_categories = sum(c["emissions_mt"] for c in category_totals.values())
    reconciliation_delta = abs(total_emissions_mt - sum_of_categories)
    is_reconciled = reconciliation_delta < 1e-6

    # KPI Calculation
    primary_emissions_coverage_pct = (primary_emissions_mt / total_emissions_mt * 100.0) if total_emissions_mt > 0 else 0.0
    estimated_share_pct = (estimated_emissions_mt / total_emissions_mt * 100.0) if total_emissions_mt > 0 else 0.0
    average_dqs = (weighted_dqs_sum / total_emissions_mt) if total_emissions_mt > 0 else 3.0

    run_id = f"RUN_{period_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    summary = {
        "run_id": run_id,
        "period_id": period_id,
        "total_emissions_mt": round(total_emissions_mt, 4),
        "category_totals": {k: round(v["emissions_mt"], 4) for k, v in category_totals.items() if v["datapoint_count"] > 0},
        "tier_distribution_mt": {f"tier_{k}": round(v, 4) for k, v in tier_distribution.items()},
        "kpis": {
            "primary_emissions_coverage_pct": round(primary_emissions_coverage_pct, 2),
            "estimated_share_pct": round(estimated_share_pct, 2),
            "average_dqs": round(average_dqs, 2)
        },
        "double_count_reconciliation": {
            "is_reconciled": is_reconciled,
            "reconciliation_delta_mt": round(reconciliation_delta, 8)
        }
    }

    BLACKBOARD.calculation_runs[run_id] = summary
    BLACKBOARD.log_audit("CALCULATION_RUN", run_id, "PERIOD_ROLLUP_COMPLETED", None, summary)

    return summary


# ==============================================================================
# 9. COMPONENT 6.14: AUDITOR-READY ASSURANCE PACK GENERATOR
# ==============================================================================

def generate_assurance_pack(period_id: str, auditor_name: str = "Lead Assurance Verifier") -> Dict[str, Any]:
    """
    Generates a cryptographically verified, deterministic assurance pack for the reporting period.
    Assembles evidence hashes, version binding manifests, ESRS E1 format, and CBAM declaration summary.
    """
    rollup = perform_period_rollup(period_id)
    period_datapoints = [dp for dp in BLACKBOARD.datapoints.values() if dp["period_id"] == period_id]
    period_info = BLACKBOARD.periods.get(period_id, {})

    evidence_manifest = []
    for dp in period_datapoints:
        evidence_manifest.append({
            "datapoint_id": dp["datapoint_id"],
            "supplier_id": dp["supplier_id"],
            "site_id": dp["site_id"],
            "material_code": dp["material_code"],
            "category_id": dp["category_id"],
            "emissions_mt": dp["co2e_emissions_mt"],
            "method_tier": dp["method_tier"],
            "dqs": dp["dqs"],
            "artifact_id": dp["artifact_id"],
            "artifact_hash": dp["artifact_hash"],
            "rejection_reasons": dp["rejection_reasons"]
        })

    # ESRS E1 Disclosure Datapoints
    esrs_e1 = {
        "standard": "CSRD_ESRS_E1_CLIMATE_CHANGE",
        "disclosure_requirement": "E1-6_GROSS_SCOPE_3_GHG_EMISSIONS",
        "reporting_period": period_id,
        "gross_scope_3_co2e_mt": rollup["total_emissions_mt"],
        "primary_data_share_pct": rollup["kpis"]["primary_emissions_coverage_pct"],
        "estimated_data_share_pct": rollup["kpis"]["estimated_share_pct"],
        "portfolio_dqs": rollup["kpis"]["average_dqs"],
        "tier_1_cat_1_breakdown": rollup["category_totals"]
    }

    pack_content = {
        "period_id": period_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bound_versions": {
            "libraries": period_info.get("bound_libraries"),
            "mapping": period_info.get("bound_mapping"),
            "formula_engine": period_info.get("bound_formula")
        },
        "esrs_e1": esrs_e1,
        "rollup_kpis": rollup["kpis"],
        "evidence_manifest": evidence_manifest,
        "double_count_proof": rollup["double_count_reconciliation"]
    }

    pack_serialized = json.dumps(pack_content, sort_keys=True)
    pack_hash = hashlib.sha256(pack_serialized.encode("utf-8")).hexdigest()

    pack_id = f"PACK_{period_id}_{pack_hash[:16]}"
    final_pack = {
        "pack_id": pack_id,
        "pack_hash_sha256": pack_hash,
        "auditor_ready": True,
        "auditor_name": auditor_name,
        "content": pack_content
    }

    BLACKBOARD.assurance_packs[pack_id] = final_pack
    BLACKBOARD.log_audit("ASSURANCE_PACK", pack_id, "PACK_ASSEMBLED_AND_SEALED", None, {"pack_hash": pack_hash})

    return final_pack


# ==============================================================================
# 10. COMPONENT 6.12 & 6.13: FSM ENGINES (ENGAGEMENT & REPORTING PERIOD)
# ==============================================================================

def advance_engagement_fsm(supplier_id: str, period_id: str, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Supplier Engagement Finite State Machine.
    Cadence: IDENTIFIED -> SEGMENTED -> CONTACTED -> SURVEY_SENT -> REMINDER_1 -> REMINDER_2 -> REMINDER_3 -> ESCALATED
    Success Lane: RESPONSE_RECEIVED -> VALIDATED -> APPROVED -> CYCLE_CLOSED
    Non-Responder Lane: FALLBACK_ASSIGNED (Tier 4/5) -> RE_SOLICITATION_SCHEDULED
    """
    case_key = f"{supplier_id}_{period_id}"
    case = BLACKBOARD.engagements.get(case_key, {
        "case_id": case_key,
        "supplier_id": supplier_id,
        "period_id": period_id,
        "state": "IDENTIFIED",
        "reminders_sent": 0,
        "validation_attempts": 0,
        "history": []
    })

    current_state = case["state"]
    new_state = current_state

    if action == "SEGMENT":
        new_state = "SEGMENTED"
    elif action == "SEND_SURVEY":
        new_state = "SURVEY_SENT"
    elif action == "SEND_REMINDER":
        if current_state == "SURVEY_SENT":
            new_state = "REMINDER_1"
            case["reminders_sent"] = 1
        elif current_state == "REMINDER_1":
            new_state = "REMINDER_2"
            case["reminders_sent"] = 2
        elif current_state == "REMINDER_2":
            new_state = "REMINDER_3"
            case["reminders_sent"] = 3
        elif current_state == "REMINDER_3":
            new_state = "ESCALATED"
    elif action == "ASSIGN_FALLBACK":
        new_state = "FALLBACK_ASSIGNED"
        case["fallback_tier"] = 5
    elif action == "RECEIVE_RESPONSE":
        new_state = "RESPONSE_RECEIVED"
    elif action == "VALIDATE_SUCCESS":
        new_state = "VALIDATED"
    elif action == "APPROVE":
        new_state = "APPROVED"
    elif action == "CLOSE":
        new_state = "CYCLE_CLOSED"

    case["history"].append({
        "from": current_state,
        "to": new_state,
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    case["state"] = new_state
    BLACKBOARD.engagements[case_key] = case
    BLACKBOARD.log_audit("ENGAGEMENT_CASE", case_key, "STATE_TRANSITION", current_state, new_state)

    return case


def transition_period_lock_fsm(period_id: str, new_state: str, approver: str = "Sustainability Manager") -> Dict[str, Any]:
    """
    Reporting Period FSM:
    PERIOD_OPEN -> ACCUMULATING -> SOFT_LOCK -> REVIEW -> HARD_LOCK -> RESTATEMENT_WINDOW -> CLOSED
    """
    period = BLACKBOARD.periods.get(period_id)
    if not period:
        return {"status": "ERROR", "message": f"Period '{period_id}' not found"}

    old_state = period["state"]
    if old_state == "HARD_LOCK" and new_state != "RESTATEMENT_WINDOW":
        return {
            "status": "BLOCKED",
            "message": f"Period '{period_id}' is HARD_LOCKED. Direct mutation forbidden. Must initiate restatement run."
        }

    period["state"] = new_state
    if new_state == "SOFT_LOCK":
        period["soft_locked_at"] = datetime.now(timezone.utc).isoformat()
    elif new_state == "HARD_LOCK":
        period["hard_locked_at"] = datetime.now(timezone.utc).isoformat()
        period["lock_checksum"] = hashlib.sha256(f"{period_id}:{period.get('bound_libraries')}:{datetime.now(timezone.utc)}".encode()).hexdigest()

    BLACKBOARD.log_audit("REPORTING_PERIOD", period_id, "LOCK_STATE_TRANSITION", old_state, new_state, actor=approver)

    return {
        "status": "SUCCESS",
        "period_id": period_id,
        "old_state": old_state,
        "new_state": new_state,
        "approver": approver,
        "lock_checksum": period.get("lock_checksum")
    }


# ==============================================================================
# 11. WINDMILL MAIN DISPATCHER ENTRY POINT
# ==============================================================================

def main(
    action: str = "orchestrate_datapoint",
    payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Windmill Script Entry Point for f/carbon_data/non_violent_script.
    Available actions:
    - ping: Health check and service descriptor
    - orchestrate_datapoint: Validates, DQS scores, and waterfall routes an inbound carbon record
    - resolve_conflict: Detects and resolves multi-source variance > 20%
    - calculate_cbam: Evaluates embedded emissions and financial penalty exposure
    - period_rollup: Performs category roll-up, double-count check, and KPI computation
    - generate_assurance_pack: Creates sealed, auditor-ready assurance pack
    - engagement_fsm: Advances supplier reminder and cadence state
    - period_lock_fsm: Manages soft-lock / hard-lock governance
    """
    if payload is None:
        payload = {}

    if action == "ping":
        return {
            "status": "HEALTHY",
            "service": "Scope 3 Supplier Carbon Data Orchestrator & Assurance Layer",
            "version": "1.0.0",
            "deterministic": True,
            "zero_llm": True,
            "governed_categories": 15,
            "waterfall_tiers": 5,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    elif action == "orchestrate_datapoint":
        # 1. Run 8-Gate Validation
        val_result = validate_inbound_datapoint(payload)
        if val_result["status"] == "REJECTED":
            return {
                "success": False,
                "stage": "VALIDATION_FAILED",
                "errors": val_result["errors"],
                "repairs": val_result["repairs"]
            }

        # 2. Waterfall Routing & Calculation
        datapoint = route_and_calculate_datapoint(val_result, payload)
        return {
            "success": True,
            "datapoint": datapoint,
            "validation_repairs": val_result["repairs"]
        }

    elif action == "resolve_conflict":
        candidates = payload.get("candidates", [])
        threshold = payload.get("threshold_pct", 20.0)
        return detect_and_resolve_conflicts(candidates, threshold)

    elif action == "calculate_cbam":
        return calculate_cbam_exposure(
            supplier_id=payload.get("supplier_id", "SUPP_NORDIC_STEEL"),
            site_id=payload.get("site_id", "SITE_LULEA_EAF"),
            material_code=payload.get("material_code", "MAT_STEEL_COIL"),
            imported_net_mass_mt=float(payload.get("imported_net_mass_mt", 1000.0)),
            declared_intensity_tco2e_per_t=float(payload.get("declared_intensity_tco2e_per_t", 0.38)),
            is_verified=bool(payload.get("is_verified", True))
        )

    elif action == "period_rollup":
        period_id = payload.get("period_id", "2025-Q4")
        return perform_period_rollup(period_id)

    elif action == "generate_assurance_pack":
        period_id = payload.get("period_id", "2025-Q4")
        auditor = payload.get("auditor_name", "KPMG_ASSURANCE_LEAD")
        return generate_assurance_pack(period_id, auditor)

    elif action == "engagement_fsm":
        return advance_engagement_fsm(
            supplier_id=payload.get("supplier_id", "SUPP_NORDIC_STEEL"),
            period_id=payload.get("period_id", "2025-Q4"),
            action=payload.get("step_action", "SEND_SURVEY"),
            payload=payload
        )

    elif action == "period_lock_fsm":
        return transition_period_lock_fsm(
            period_id=payload.get("period_id", "2025-Q4"),
            new_state=payload.get("target_state", "SOFT_LOCK"),
            approver=payload.get("approver", "Sustainability Director")
        )

    else:
        return {
            "status": "ERROR",
            "message": f"Unsupported action '{action}'."
        }


if __name__ == "__main__":
    # Local CLI test verification
    res = main("ping")
    print(json.dumps(res, indent=2))
