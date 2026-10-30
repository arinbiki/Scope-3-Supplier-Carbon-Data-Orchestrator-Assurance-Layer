-- ============================================================================
-- Scope 3 Supplier Carbon Data Orchestrator & Assurance Layer
-- PostgreSQL DDL: Schema and Core Governance Tables
-- Schema: scope3_carbon
-- Version: 1.0.0 (Deterministic, Zero-LLM Architecture)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS scope3_carbon;

SET search_path TO scope3_carbon, public;

-- 1. Supplier Master
CREATE TABLE IF NOT EXISTS supplier_master (
    supplier_id VARCHAR(64) PRIMARY KEY,
    legal_name VARCHAR(255) NOT NULL,
    country_iso2 CHAR(2) NOT NULL,
    segment VARCHAR(32) NOT NULL DEFAULT 'TIER_1_DIRECT', -- TIER_1_DIRECT, RAW_MATERIAL, LOGISTICS, PACKAGING, SERVICES
    priority_class VARCHAR(16) NOT NULL DEFAULT 'STRATEGIC', -- STRATEGIC, CRITICAL, STANDARD, LONG_TAIL
    annual_spend_usd NUMERIC(16, 2) NOT NULL DEFAULT 0.00,
    has_cbam_exposure BOOLEAN NOT NULL DEFAULT FALSE,
    contact_email VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Supplier Site Master (Site-level Granularity: Supplier-Site x Process x Period)
CREATE TABLE IF NOT EXISTS supplier_site (
    site_id VARCHAR(64) PRIMARY KEY,
    supplier_id VARCHAR(64) NOT NULL REFERENCES supplier_master(supplier_id) ON DELETE CASCADE,
    site_name VARCHAR(255) NOT NULL,
    country_iso2 CHAR(2) NOT NULL,
    grid_region VARCHAR(64) NOT NULL, -- e.g., US_WECC, DE_GRID, SE_ZONE_1, CN_NORTH
    primary_process VARCHAR(128) NOT NULL, -- e.g., ELECTRIC_ARC_FURNACE, BLAST_FURNACE_BOF, POLYMER_EXTRUSION
    energy_mix_declarations JSONB NOT NULL DEFAULT '{"renewable_pct": 0, "grid_pct": 100, "onsite_solar_pct": 0}'::jsonb,
    certificates_held JSONB NOT NULL DEFAULT '[]'::jsonb, -- e.g., ["ISO_14064", "ISO_14067", "RECs"]
    verification_status VARCHAR(32) NOT NULL DEFAULT 'UNVERIFIED', -- UNVERIFIED, SELF_DECLARED, THIRD_PARTY_ASSURED
    annual_capacity_mt NUMERIC(14, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Scope 3 Category Registry (GHG Protocol Scope 3 Categories 1 - 15)
CREATE TABLE IF NOT EXISTS scope3_category (
    category_id INT PRIMARY KEY,
    category_code VARCHAR(32) NOT NULL UNIQUE,
    category_name VARCHAR(255) NOT NULL,
    ghg_scope VARCHAR(16) NOT NULL DEFAULT 'SCOPE_3',
    assignment_rule_version VARCHAR(32) NOT NULL DEFAULT 'GHG_PROTOCOL_V2024'
);

-- 4. Material Master
CREATE TABLE IF NOT EXISTS material_master (
    material_code VARCHAR(64) PRIMARY KEY,
    material_name VARCHAR(255) NOT NULL,
    category_id INT NOT NULL REFERENCES scope3_category(category_id),
    standard_hs_code VARCHAR(16),
    canonical_uom VARCHAR(64) NOT NULL, -- kg, metric_ton, m2, kwh, piece, compute_core_hour
    is_cbam_covered BOOLEAN NOT NULL DEFAULT FALSE,
    sector_classification VARCHAR(64) NOT NULL -- e.g., BASIC_METALS, CHEMICALS, ELECTRONICS
);

-- 5. Reporting Period Master (Finite State Machine: OPEN -> ACCUMULATING -> SOFT_LOCK -> REVIEW -> HARD_LOCK -> RESTATEMENT_WINDOW -> CLOSED)
CREATE TABLE IF NOT EXISTS reporting_period (
    period_id VARCHAR(32) PRIMARY KEY, -- e.g., '2025-Q4', '2025-FY'
    period_code VARCHAR(32) NOT NULL UNIQUE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    state VARCHAR(32) NOT NULL DEFAULT 'PERIOD_OPEN',
    bound_factor_library_version VARCHAR(64),
    bound_mapping_version VARCHAR(64),
    bound_formula_version VARCHAR(64),
    soft_locked_at TIMESTAMPTZ,
    hard_locked_at TIMESTAMPTZ,
    data_steward_approver VARCHAR(128),
    sustainability_manager_approver VARCHAR(128),
    lock_checksum VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Evidence Artifact Registry (SHA-256 Content Addressed)
CREATE TABLE IF NOT EXISTS evidence_artifact (
    artifact_id VARCHAR(64) PRIMARY KEY,
    artifact_type VARCHAR(64) NOT NULL, -- PCF_REPORT, AUDIT_STATEMENT, ENERGY_INVOICE, ISO_CERTIFICATE, SURVEY_SUBMISSION
    file_name VARCHAR(255) NOT NULL,
    file_hash_sha256 CHAR(64) NOT NULL UNIQUE,
    source VARCHAR(64) NOT NULL, -- SUPPLIER_PORTAL, CDP_API, EMAIL_DROP, ERP_CONNECTOR
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verifier_name VARCHAR(255),
    verifier_accreditation VARCHAR(128),
    storage_uri TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Factor Library Registry (Immutable, Versioned)
CREATE TABLE IF NOT EXISTS factor_library (
    library_id VARCHAR(64) PRIMARY KEY,
    publisher VARCHAR(128) NOT NULL, -- e.g., 'GHG_PROTOCOL', 'ECOINVENT', 'US_EPA_EEIO', 'DEFRA'
    version_tag VARCHAR(64) NOT NULL, -- e.g., '2024.1', '3.10', 'v2.0.1'
    vintage_year INT NOT NULL,
    license_type VARCHAR(64) NOT NULL, -- OPEN_DATA, COMMERCIAL_SUBSCRIPTION, ACADEMIC
    license_expiry DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    base_currency CHAR(3) NOT NULL DEFAULT 'USD',
    base_year INT NOT NULL DEFAULT 2024,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unq_pub_ver UNIQUE (publisher, version_tag)
);

-- 8. Factor Mapping Table
CREATE TABLE IF NOT EXISTS factor_mapping (
    mapping_id VARCHAR(64) PRIMARY KEY,
    library_id VARCHAR(64) NOT NULL REFERENCES factor_library(library_id),
    material_code VARCHAR(64) REFERENCES material_master(material_code),
    sector_classification VARCHAR(64),
    process_key VARCHAR(128) NOT NULL,
    geography VARCHAR(16) NOT NULL DEFAULT 'GLO', -- GLO, EU, US, CN, etc.
    factor_value NUMERIC(14, 6) NOT NULL, -- kg CO2e per unit
    factor_unit VARCHAR(32) NOT NULL, -- kg_co2e_per_kg, kg_co2e_per_usd, etc.
    data_quality_pedigree JSONB NOT NULL DEFAULT '{"reliability": 2, "temporal": 1, "geographical": 2, "technological": 2}'::jsonb,
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 9. Currency Deflator Table (For Tier 5 Spend Deflation to Library Base Year)
CREATE TABLE IF NOT EXISTS currency_deflator (
    deflator_id VARCHAR(32) PRIMARY KEY,
    currency CHAR(3) NOT NULL,
    transaction_year INT NOT NULL,
    target_base_year INT NOT NULL,
    deflation_factor NUMERIC(8, 6) NOT NULL, -- e.g. 2025 USD to 2021 EEIO USD = 0.852104
    fx_rate_to_usd NUMERIC(10, 6) NOT NULL DEFAULT 1.000000,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unq_cur_yr UNIQUE (currency, transaction_year, target_base_year)
);

-- 10. Carbon Datapoint (The Central Governed Object)
CREATE TABLE IF NOT EXISTS carbon_datapoint (
    datapoint_id VARCHAR(64) PRIMARY KEY,
    period_id VARCHAR(32) NOT NULL REFERENCES reporting_period(period_id),
    supplier_id VARCHAR(64) NOT NULL REFERENCES supplier_master(supplier_id),
    site_id VARCHAR(64) NOT NULL REFERENCES supplier_site(site_id),
    material_code VARCHAR(64) NOT NULL REFERENCES material_master(material_code),
    category_id INT NOT NULL REFERENCES scope3_category(category_id),
    
    -- Quantities and Emissions
    activity_quantity NUMERIC(16, 4) NOT NULL,
    activity_uom VARCHAR(16) NOT NULL,
    co2e_emissions_mt NUMERIC(16, 4) NOT NULL, -- Output in Metric Tons CO2e
    emission_intensity_kg_co2e_per_unit NUMERIC(14, 6) NOT NULL,
    
    -- Governance and Method Tier (1 to 5)
    method_tier INT NOT NULL CHECK (method_tier BETWEEN 1 AND 5),
    tier_name VARCHAR(32) NOT NULL, -- TIER_1_PRIMARY, TIER_2_PCF, TIER_3_HYBRID, TIER_4_FACTOR, TIER_5_SPEND
    
    -- 5-Dimension Pedigree DQS (1.0 = Best, 5.0 = Worst)
    dqs_overall NUMERIC(4, 2) NOT NULL,
    dqs_reliability NUMERIC(4, 2) NOT NULL,
    dqs_completeness NUMERIC(4, 2) NOT NULL,
    dqs_temporal NUMERIC(4, 2) NOT NULL,
    dqs_geographical NUMERIC(4, 2) NOT NULL,
    dqs_technological NUMERIC(4, 2) NOT NULL,
    dqs_band VARCHAR(16) NOT NULL, -- HIGH, MEDIUM, LOW
    
    -- Flags and Links
    status VARCHAR(32) NOT NULL DEFAULT 'VALIDATED', -- INGESTED, VALIDATED, CALCULATED, SOFT_LOCKED, HARD_LOCKED, SUPERSEDED, REJECTED
    is_estimate BOOLEAN NOT NULL DEFAULT FALSE,
    is_material BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_artifact_id VARCHAR(64) REFERENCES evidence_artifact(artifact_id),
    factor_library_id VARCHAR(64) REFERENCES factor_library(library_id),
    calculation_run_id VARCHAR(64),
    superseded_by VARCHAR(64),
    
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. Conflict Case Registry (>20% Relative Variance between Sources)
CREATE TABLE IF NOT EXISTS conflict_case (
    conflict_id VARCHAR(64) PRIMARY KEY,
    period_id VARCHAR(32) NOT NULL REFERENCES reporting_period(period_id),
    supplier_id VARCHAR(64) NOT NULL REFERENCES supplier_master(supplier_id),
    site_id VARCHAR(64) NOT NULL REFERENCES supplier_site(site_id),
    material_code VARCHAR(64) NOT NULL REFERENCES material_master(material_code),
    candidate_datapoints JSONB NOT NULL, -- Array of candidate objects with tier, value, artifact, dqs
    variance_pct NUMERIC(6, 2) NOT NULL,
    resolution_state VARCHAR(32) NOT NULL DEFAULT 'PENDING_REVIEW', -- AUTO_RESOLVED, MANUAL_REVIEW, ESCALATED
    winning_tier INT,
    winner_datapoint_id VARCHAR(64),
    resolution_rationale TEXT,
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(128)
);

-- 12. Supplier Engagement Case FSM
CREATE TABLE IF NOT EXISTS engagement_case (
    case_id VARCHAR(64) PRIMARY KEY,
    period_id VARCHAR(32) NOT NULL REFERENCES reporting_period(period_id),
    supplier_id VARCHAR(64) NOT NULL REFERENCES supplier_master(supplier_id),
    current_state VARCHAR(32) NOT NULL DEFAULT 'IDENTIFIED',
    -- IDENTIFIED -> SEGMENTED -> CONTACTED -> SURVEY_SENT -> REMINDER_1 -> REMINDER_2 -> REMINDER_3 -> ESCALATED -> RESPONSE_RECEIVED -> VALIDATED -> APPROVED -> CYCLE_CLOSED
    -- Non-responder lane: FALLBACK_ASSIGNED -> RE_SOLICITATION_SCHEDULED -> COVERAGE_TARGET_ASSIGNED
    priority_class VARCHAR(16) NOT NULL,
    survey_sent_at TIMESTAMPTZ,
    reminder_1_at TIMESTAMPTZ,
    reminder_2_at TIMESTAMPTZ,
    reminder_3_at TIMESTAMPTZ,
    escalated_at TIMESTAMPTZ,
    response_received_at TIMESTAMPTZ,
    validation_attempts INT NOT NULL DEFAULT 0,
    validation_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    fallback_tier_assigned INT,
    next_cycle_target_tier INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13. Calculation Run (Immutable Period Run)
CREATE TABLE IF NOT EXISTS calculation_run (
    run_id VARCHAR(64) PRIMARY KEY,
    period_id VARCHAR(32) NOT NULL REFERENCES reporting_period(period_id),
    run_type VARCHAR(32) NOT NULL DEFAULT 'STANDARD_CLOSE', -- STANDARD_CLOSE, RESTATED_RUN, SIMULATION
    inputs_hash CHAR(64) NOT NULL,
    bound_versions JSONB NOT NULL,
    total_emissions_mt NUMERIC(16, 4) NOT NULL,
    primary_spend_coverage_pct NUMERIC(6, 2) NOT NULL,
    primary_emissions_coverage_pct NUMERIC(6, 2) NOT NULL,
    estimated_emissions_pct NUMERIC(6, 2) NOT NULL,
    average_dqs NUMERIC(4, 2) NOT NULL,
    tier_distribution JSONB NOT NULL, -- e.g. {"tier1_mt": 1200, "tier2_mt": 5000, ...}
    category_summary JSONB NOT NULL, -- Category 1 to 15 breakdown
    executed_by VARCHAR(128) NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 14. Assurance Pack Registry
CREATE TABLE IF NOT EXISTS assurance_pack (
    pack_id VARCHAR(64) PRIMARY KEY,
    period_id VARCHAR(32) NOT NULL REFERENCES reporting_period(period_id),
    calculation_run_id VARCHAR(64) NOT NULL REFERENCES calculation_run(run_id),
    pack_hash_sha256 CHAR(64) NOT NULL,
    bound_manifest JSONB NOT NULL,
    esrs_e1_datapoints JSONB NOT NULL,
    cbam_declaration_summary JSONB NOT NULL,
    tier_breakdown JSONB NOT NULL,
    evidence_index JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    generated_by VARCHAR(128) NOT NULL
);

-- 15. Audit Event Log (Append-Only)
CREATE TABLE IF NOT EXISTS audit_event (
    event_id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL, -- STATE_CHANGE, TIER_SELECTED, CONFLICT_DETECTED, LOCK_ENGAGED, RESTATEMENT_INITIATED
    before_state JSONB,
    after_state JSONB,
    actor VARCHAR(128) NOT NULL,
    rule_version VARCHAR(32) NOT NULL DEFAULT 'V1.0',
    event_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 16. CBAM Goods & Declaration Registry
CREATE TABLE IF NOT EXISTS cbam_declaration (
    declaration_id VARCHAR(64) PRIMARY KEY,
    period_id VARCHAR(32) NOT NULL REFERENCES reporting_period(period_id),
    supplier_id VARCHAR(64) NOT NULL REFERENCES supplier_master(supplier_id),
    site_id VARCHAR(64) NOT NULL REFERENCES supplier_site(site_id),
    material_code VARCHAR(64) NOT NULL REFERENCES material_master(material_code),
    cn_code VARCHAR(16) NOT NULL,
    imported_net_mass_mt NUMERIC(14, 4) NOT NULL,
    direct_emissions_intensity NUMERIC(12, 6) NOT NULL, -- tCO2e / t
    indirect_emissions_intensity NUMERIC(12, 6) NOT NULL, -- tCO2e / t
    total_embedded_emissions_mt NUMERIC(14, 4) NOT NULL,
    data_source_type VARCHAR(32) NOT NULL, -- ACTUAL_VERIFIED, ESTIMATED_DEFAULT
    default_penalty_cost_eur NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create Indexes for performance
CREATE INDEX IF NOT EXISTS idx_datapoint_period ON carbon_datapoint(period_id);
CREATE INDEX IF NOT EXISTS idx_datapoint_supplier ON carbon_datapoint(supplier_id);
CREATE INDEX IF NOT EXISTS idx_datapoint_site ON carbon_datapoint(site_id);
CREATE INDEX IF NOT EXISTS idx_datapoint_tier ON carbon_datapoint(method_tier);
CREATE INDEX IF NOT EXISTS idx_artifact_hash ON evidence_artifact(file_hash_sha256);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_event(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_factor_map_lookup ON factor_mapping(material_code, geography, is_active);
