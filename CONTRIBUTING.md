# Contributing to Scope 3 Supplier Carbon Data Orchestrator & Assurance Layer

Thank you for your interest in contributing to the **Scope 3 Supplier Carbon Data Orchestrator & Assurance Layer**.

## Architectural Invariants (Non-Negotiable)

To maintain regulatory defensibility and assurance readiness, all contributions must uphold these core principles:

1. **Zero LLM / Non-Deterministic Calls**:
   * All routing, data quality scoring, unit conversions, currency deflations, and emissions math must be **100% deterministic, closed-form algebraic equations**.
   * No probabilistic AI, LLM prompt chains, or heuristic guesses are permitted in the calculation or governance path.

2. **Site-Level Truth Granularity**:
   * All data must be modeled at `(supplier-site × process/material × reporting_period)`. Never introduce blended supplier averages that blur clean versus dirty production plants.

3. **5-Tier Waterfall Hierarchy**:
   * Tier 1 (Supplier Primary Activity) > Tier 2 (Supplier PCF) > Tier 3 (Hybrid Energy Mix) > Tier 4 (Industry Average Factor) > Tier 5 (Spend EEIO).
   * Rejections of higher tiers must record explicit reason codes.

4. **5-Dimension Pedigree Scoring**:
   * Every datapoint must carry its 5-dimension pedigree vector (Reliability, Completeness, Temporal, Geographical, Technological) and resulting banded DQS.

5. **Double-Counting Guarantee**:
   * Every emission line must map to exactly one GHG Protocol Scope 3 category (1–15). Mathematical proof `Sum(Cat 1..15) == Total Inventory` must always hold.

6. **Full Test Coverage**:
   * All pull requests must pass the complete Golden Test Suite:
     ```bash
     python tests/golden_carbon_test_suite.py
     ```
