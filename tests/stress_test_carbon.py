#!/usr/bin/env python3
"""
================================================================================
High-Volume Synthetic Stress Test Suite: Scope 3 Carbon Orchestrator
Path: tests/stress_test_carbon.py
Architecture: Zero-LLM Deterministic Governance & Waterfall Engine
================================================================================
"""

import sys
import os
import time
import json
import random
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "windmill")))
from non_violent_script import (
    validate_inbound_datapoint,
    route_and_calculate_datapoint,
    perform_period_rollup,
    BLACKBOARD,
    initialize_default_blackboard
)


def generate_synthetic_stream(batch_size: int = 50000) -> List[Dict[str, Any]]:
    """Generates realistic enterprise Scope 3 carbon ingestion payloads."""
    suppliers_sites = [
        ("SUPP_NORDIC_STEEL", "SITE_LULEA_EAF", "MAT_STEEL_COIL", "ART_NORDIC_PCF_2025"),
        ("SUPP_SILESIAN_STEEL", "SITE_KATOWICE_BOF", "MAT_STEEL_COIL", None),
        ("SUPP_APEX_POLYMERS", "SITE_JURONG_POLYMER", "MAT_POLYMER_RESIN", "ART_APEX_ISO14067"),
        ("SUPP_PACIFIC_WAFER", "SITE_HSINCHU_FAB1", "MAT_SILICON_WAFER", "ART_PACIFIC_IREC_2025"),
        ("SUPP_SHENZHEN_STAMPING", "SITE_BAOAN_PLANT", "MAT_CORRUGATED_BOX", None),
    ]

    payloads = []
    for i in range(batch_size):
        supp, site, mat, art = random.choice(suppliers_sites)
        is_spend_fallback = (supp == "SUPP_SHENZHEN_STAMPING" and random.random() < 0.4)
        
        p = {
            "period_id": "2025-Q4",
            "supplier_id": supp,
            "site_id": site,
            "material_code": mat,
            "quantity": round(random.uniform(10.0, 5000.0), 2),
            "uom": "metric_ton" if mat != "MAT_SILICON_WAFER" else "piece",
            "boundary": "CRADLE_TO_GATE",
            "artifact_id": art
        }
        if is_spend_fallback:
            p["quantity"] = 0.0
            p["spend_amount"] = round(random.uniform(5000.0, 500000.0), 2)
            p["currency"] = "USD"
            p["transaction_year"] = "2025"

        payloads.append(p)
    return payloads


def run_carbon_stress_test(total_records: int = 100000, batch_size: int = 10000):
    print("=" * 80)
    print(f"STARTING SCOPE 3 CARBON ORCHESTRATOR STRESS TEST: {total_records:,} RECORDS")
    print("Architecture: Zero-LLM Deterministic 5-Tier Waterfall & DQS Pedigree Engine")
    print("=" * 80)

    initialize_default_blackboard()

    latencies_ms = []
    processed_count = 0
    tier_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    dqs_bands = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    total_co2e_mt = 0.0

    t_start = time.perf_counter()

    num_batches = total_records // batch_size
    for b in range(num_batches):
        batch = generate_synthetic_stream(batch_size)
        b_start = time.perf_counter()

        for item in batch:
            t0 = time.perf_counter()
            val = validate_inbound_datapoint(item)
            if val["status"] == "VALIDATED":
                dp = route_and_calculate_datapoint(val, item)
                tier_counts[dp["method_tier"]] += 1
                dqs_bands[dp["dqs"]["band"]] += 1
                total_co2e_mt += dp["co2e_emissions_mt"]
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

        b_elapsed = time.perf_counter() - b_start
        processed_count += batch_size
        ops_batch = batch_size / b_elapsed
        print(f"Batch {b + 1:02d}/{num_batches:02d} | Processed: {processed_count:,} | Rate: {ops_batch:,.1f} records/sec")

    total_time = time.perf_counter() - t_start
    overall_ops = processed_count / total_time

    latencies_ms.sort()
    p50 = latencies_ms[int(len(latencies_ms) * 0.50)]
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
    p99 = latencies_ms[int(len(latencies_ms) * 0.99)]

    # Final Period Rollup & Double Count Reconciliation
    rollup = perform_period_rollup("2025-Q4")
    reconciliation = rollup["double_count_reconciliation"]

    report = {
        "benchmark_summary": {
            "total_records": processed_count,
            "total_execution_seconds": round(total_time, 4),
            "throughput_records_per_second": round(overall_ops, 2),
            "latency_p50_ms": round(p50, 4),
            "latency_p95_ms": round(p95, 4),
            "latency_p99_ms": round(p99, 4),
            "zero_llm_deterministic": True
        },
        "governance_distributions": {
            "tier_distribution": {f"tier_{k}": v for k, v in tier_counts.items()},
            "tier_share_pct": {f"tier_{k}": round(v / processed_count * 100.0, 2) for k, v in tier_counts.items()},
            "dqs_band_distribution": dqs_bands,
            "dqs_band_share_pct": {k: round(v / processed_count * 100.0, 2) for k, v in dqs_bands.items()}
        },
        "inventory_kpis": {
            "total_emissions_mt": round(total_co2e_mt, 2),
            "primary_data_coverage_pct": round((tier_counts[1] + tier_counts[2]) / processed_count * 100.0, 2),
            "estimated_data_share_pct": round((tier_counts[4] + tier_counts[5]) / processed_count * 100.0, 2),
            "double_count_reconciliation": reconciliation
        }
    }

    report_path = os.path.join(os.path.dirname(__file__), "stress_test_carbon_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("STRESS TEST COMPLETED SUCCESSFULLY")
    print(f"Total Processed: {processed_count:,} records in {total_time:.2f}s ({overall_ops:,.1f} OPS)")
    print(f"Latency: P50={p50:.3f}ms | P95={p95:.3f}ms | P99={p99:.3f}ms")
    print(f"Primary Coverage: {report['inventory_kpis']['primary_data_coverage_pct']}%")
    print(f"Double Counting Reconciled: {reconciliation['is_reconciled']} (Delta: {reconciliation['reconciliation_delta_mt']} MT)")
    print(f"Benchmark report saved to: {report_path}")
    print("=" * 80)


if __name__ == "__main__":
    run_carbon_stress_test(total_records=100000, batch_size=10000)
