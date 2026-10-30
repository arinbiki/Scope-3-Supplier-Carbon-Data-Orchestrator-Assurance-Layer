-- ============================================================================
-- Scope 3 Supplier Carbon Data Orchestrator & Assurance Layer
-- PostgreSQL Seed Data: Master Data, Factor Libraries, Mappings, Suppliers & Sites
-- Schema: scope3_carbon
-- ============================================================================

SET search_path TO scope3_carbon, public;

-- 1. GHG Protocol Scope 3 Categories (1 to 15)
INSERT INTO scope3_category (category_id, category_code, category_name, ghg_scope, assignment_rule_version)
VALUES
    (1,  'CAT_01_PURCHASED_GOODS',       'Purchased Goods and Services',                       'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (2,  'CAT_02_CAPITAL_GOODS',          'Capital Goods',                                      'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (3,  'CAT_03_FUEL_ENERGY_ACTIVITIES', 'Fuel- and Energy-Related Activities (not in S1/S2)','SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (4,  'CAT_04_UPSTREAM_TRANSPORT',     'Upstream Transportation and Distribution',           'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (5,  'CAT_05_WASTE_OPERATIONS',       'Waste Generated in Operations',                      'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (6,  'CAT_06_BUSINESS_TRAVEL',        'Business Travel',                                    'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (7,  'CAT_07_EMPLOYEE_COMMUTING',     'Employee Commuting',                                 'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (8,  'CAT_08_UPSTREAM_LEASED',        'Upstream Leased Assets',                             'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (9,  'CAT_09_DOWNSTREAM_TRANSPORT',   'Downstream Transportation and Distribution',         'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (10, 'CAT_10_PROCESSING_SOLD_GOODS',  'Processing of Sold Products',                        'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (11, 'CAT_11_USE_SOLD_PRODUCTS',     'Use of Sold Products',                               'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (12, 'CAT_12_END_OF_LIFE',            'End-of-Life Treatment of Sold Products',             'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (13, 'CAT_13_DOWNSTREAM_LEASED',      'Downstream Leased Assets',                           'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (14, 'CAT_14_FRANCHISES',             'Franchises',                                         'SCOPE_3', 'GHG_PROTOCOL_V2024'),
    (15, 'CAT_15_INVESTMENTS',            'Investments',                                        'SCOPE_3', 'GHG_PROTOCOL_V2024')
ON CONFLICT (category_id) DO NOTHING;

-- 2. Factor Libraries
INSERT INTO factor_library (library_id, publisher, version_tag, vintage_year, license_type, license_expiry, is_active, base_currency, base_year)
VALUES
    ('LIB_GHG_2024',     'GHG_PROTOCOL', '2024.1', 2024, 'OPEN_DATA',               '2030-12-31', TRUE, 'USD', 2024),
    ('LIB_ECOINVENT_310','ECOINVENT',    '3.10',   2023, 'COMMERCIAL_SUBSCRIPTION', '2027-12-31', TRUE, 'EUR', 2023),
    ('LIB_US_EPA_EEIO',  'US_EPA_EEIO',  'v2.0.1', 2021, 'OPEN_DATA',               '2030-12-31', TRUE, 'USD', 2021),
    ('LIB_DEFRA_2024',   'DEFRA',        '2024.0', 2024, 'OPEN_DATA',               '2028-12-31', TRUE, 'GBP', 2024)
ON CONFLICT (library_id) DO NOTHING;

-- 3. Currency Deflators (Base Year 2021 for EEIO)
INSERT INTO currency_deflator (deflator_id, currency, transaction_year, target_base_year, deflation_factor, fx_rate_to_usd)
VALUES
    ('DEF_USD_2025_2021', 'USD', 2025, 2021, 0.852104, 1.000000),
    ('DEF_USD_2024_2021', 'USD', 2024, 2021, 0.881230, 1.000000),
    ('DEF_EUR_2025_2021', 'EUR', 2025, 2021, 0.835420, 1.085000),
    ('DEF_GBP_2025_2021', 'GBP', 2025, 2021, 0.821900, 1.285000),
    ('DEF_CNY_2025_2021', 'CNY', 2025, 2021, 0.941200, 0.138000),
    ('DEF_JPY_2025_2021', 'JPY', 2025, 2021, 0.965000, 0.006700)
ON CONFLICT (deflator_id) DO NOTHING;

-- 4. Material Master
INSERT INTO material_master (material_code, material_name, category_id, standard_hs_code, canonical_uom, is_cbam_covered, sector_classification)
VALUES
    ('MAT_STEEL_COIL',     'Hot Rolled Steel Coil',          1, '7208', 'metric_ton',       TRUE,  'BASIC_METALS'),
    ('MAT_ALUMINUM_INGOT', 'Primary Aluminum Ingot',         1, '7601', 'metric_ton',       TRUE,  'BASIC_METALS'),
    ('MAT_POLYMER_RESIN',  'High-Density Polyethylene (HDPE)',1, '3901', 'metric_ton',       FALSE, 'CHEMICALS'),
    ('MAT_SILICON_WAFER',  '300mm Monocrystalline Silicon',  1, '3818', 'piece',            FALSE, 'ELECTRONICS'),
    ('MAT_CORRUGATED_BOX', 'Heavy-Duty Corrugated Carton',   1, '4819', 'metric_ton',       FALSE, 'PACKAGING'),
    ('MAT_FREIGHT_OCEAN',  'Container Ocean Freight 40ft',   4, '9900', 'ton_km',           FALSE, 'LOGISTICS'),
    ('MAT_FREIGHT_ROAD',   'Heavy Duty Diesel Road Freight', 4, '9900', 'ton_km',           FALSE, 'LOGISTICS'),
    ('MAT_CLOUD_COMPUTE',  'Cloud Compute Virtual CPU Hour', 1, '8523', 'compute_core_hour',FALSE, 'SERVICES')
ON CONFLICT (material_code) DO NOTHING;

-- 5. Factor Mappings (Physical factors kg CO2e / unit, and EEIO factors kg CO2e / USD)
INSERT INTO factor_mapping (mapping_id, library_id, material_code, sector_classification, process_key, geography, factor_value, factor_unit, effective_from, effective_to, is_active)
VALUES
    -- Physical process factors (Tier 4 Fallback)
    ('MAP_STEEL_GLOBAL', 'LIB_ECOINVENT_310', 'MAT_STEEL_COIL',     'BASIC_METALS', 'STEEL_PRODUCTION_BLAST_FURNACE', 'GLO', 2150.000000, 'kg_co2e_per_metric_ton', '2023-01-01', '2028-12-31', TRUE),
    ('MAP_STEEL_EU',     'LIB_ECOINVENT_310', 'MAT_STEEL_COIL',     'BASIC_METALS', 'STEEL_PRODUCTION_EAF_ELECTRIC',  'EU',   420.000000, 'kg_co2e_per_metric_ton', '2023-01-01', '2028-12-31', TRUE),
    ('MAP_ALUM_GLOBAL',  'LIB_ECOINVENT_310', 'MAT_ALUMINUM_INGOT', 'BASIC_METALS', 'ALUMINUM_SMELTING_GLOBAL_MIX',   'GLO', 8600.000000, 'kg_co2e_per_metric_ton', '2023-01-01', '2028-12-31', TRUE),
    ('MAP_POLYMER_GLO',  'LIB_ECOINVENT_310', 'MAT_POLYMER_RESIN',  'CHEMICALS',    'HDPE_POLYMERIZATION_PETRO',       'GLO', 1890.000000, 'kg_co2e_per_metric_ton', '2023-01-01', '2028-12-31', TRUE),
    ('MAP_WAFER_GLO',    'LIB_ECOINVENT_310', 'MAT_SILICON_WAFER',  'ELECTRONICS',  'SILICON_INGOT_SLICING_CLEANROOM', 'GLO',   14.500000, 'kg_co2e_per_piece',      '2023-01-01', '2028-12-31', TRUE),
    ('MAP_BOX_GLO',      'LIB_DEFRA_2024',    'MAT_CORRUGATED_BOX', 'PACKAGING',    'CORRUGATED_CARDBOARD_VIRGIN',     'GLO',  810.000000, 'kg_co2e_per_metric_ton', '2024-01-01', '2028-12-31', TRUE),
    ('MAP_OCEAN_FREIGHT','LIB_DEFRA_2024',    'MAT_FREIGHT_OCEAN',  'LOGISTICS',    'MARITIME_CONTAINER_VESSEL_AVG',   'GLO',    0.016200, 'kg_co2e_per_ton_km',     '2024-01-01', '2028-12-31', TRUE),
    ('MAP_ROAD_FREIGHT', 'LIB_DEFRA_2024',    'MAT_FREIGHT_ROAD',   'LOGISTICS',    'ARTICULATED_TRUCK_DIESEL_EURO6',  'GLO',    0.084100, 'kg_co2e_per_ton_km',     '2024-01-01', '2028-12-31', TRUE),
    
    -- Spend EEIO factors (Tier 5 Fallback) kg CO2e / 2021 USD
    ('MAP_EEIO_METALS',  'LIB_US_EPA_EEIO', NULL, 'BASIC_METALS', 'EEIO_3311_IRON_STEEL_MILLS', 'US', 0.985400, 'kg_co2e_per_usd', '2021-01-01', '2030-12-31', TRUE),
    ('MAP_EEIO_CHEM',    'LIB_US_EPA_EEIO', NULL, 'CHEMICALS',    'EEIO_3251_BASIC_CHEMICAL',   'US', 0.742100, 'kg_co2e_per_usd', '2021-01-01', '2030-12-31', TRUE),
    ('MAP_EEIO_ELEC',    'LIB_US_EPA_EEIO', NULL, 'ELECTRONICS',  'EEIO_3344_SEMICONDUCTORS',   'US', 0.312500, 'kg_co2e_per_usd', '2021-01-01', '2030-12-31', TRUE),
    ('MAP_EEIO_PACK',    'LIB_US_EPA_EEIO', NULL, 'PACKAGING',    'EEIO_3222_PAPER_CONTAINERS', 'US', 0.512000, 'kg_co2e_per_usd', '2021-01-01', '2030-12-31', TRUE),
    ('MAP_EEIO_LOGIS',   'LIB_US_EPA_EEIO', NULL, 'LOGISTICS',    'EEIO_4840_TRUCK_TRANSPORT',  'US', 0.621400, 'kg_co2e_per_usd', '2021-01-01', '2030-12-31', TRUE),
    ('MAP_EEIO_SERV',    'LIB_US_EPA_EEIO', NULL, 'SERVICES',     'EEIO_5182_DATA_PROCESSING',  'US', 0.142000, 'kg_co2e_per_usd', '2021-01-01', '2030-12-31', TRUE)
ON CONFLICT (mapping_id) DO NOTHING;

-- 6. Supplier Master Data
INSERT INTO supplier_master (supplier_id, legal_name, country_iso2, segment, priority_class, annual_spend_usd, has_cbam_exposure, contact_email)
VALUES
    ('SUPP_NORDIC_STEEL',      'Nordic Green Steel AB',            'SE', 'RAW_MATERIAL',   'STRATEGIC', 14500000.00, TRUE,  'sustainability@nordicgreensteel.se'),
    ('SUPP_SILESIAN_STEEL',    'Silesian Blast Furnace Sp. z o.o.','PL', 'RAW_MATERIAL',   'STRATEGIC', 14200000.00, TRUE,  'compliance@silesiansteel.pl'),
    ('SUPP_APEX_POLYMERS',     'Apex Polymer Solutions Pte Ltd',   'SG', 'RAW_MATERIAL',   'CRITICAL',   8900000.00, FALSE, 'esg@apexpolymers.sg'),
    ('SUPP_PACIFIC_WAFER',     'Pacific Silicon Wafer Corp',       'TW', 'TIER_1_DIRECT',  'CRITICAL',  22400000.00, FALSE, 'carbon@pacificwafer.com.tw'),
    ('SUPP_SHENZHEN_STAMPING', 'Shenzhen Precision Stamping Co',   'CN', 'TIER_1_DIRECT',  'STANDARD',   3200000.00, FALSE, 'operations@sz-precision.cn'),
    ('SUPP_TRANSATLANTIC_LOG', 'Transatlantic Container Lines NV', 'BE', 'LOGISTICS',      'STANDARD',   5100000.00, FALSE, 'greenteam@transatlantic-lines.be'),
    ('SUPP_ECO_PACKAGING',     'EcoFiber Packaging Iberica SA',    'ES', 'PACKAGING',      'STANDARD',   2800000.00, FALSE, 'sustainability@ecofiber.es'),
    ('SUPP_ALPINE_COMPUTE',    'Alpine Cloud Infrastructure AG',   'CH', 'SERVICES',       'STANDARD',   1950000.00, FALSE, 'cloud-esg@alpinecompute.ch')
ON CONFLICT (supplier_id) DO NOTHING;

-- 7. Supplier Sites (Site-Level Truth)
INSERT INTO supplier_site (site_id, supplier_id, site_name, country_iso2, grid_region, primary_process, energy_mix_declarations, certificates_held, verification_status, annual_capacity_mt)
VALUES
    -- Nordic Green Steel (Solar/Wind powered EAF in Sweden)
    ('SITE_LULEA_EAF', 'SUPP_NORDIC_STEEL', 'Luleå Hydrogen & EAF Plant', 'SE', 'SE_ZONE_1', 'ELECTRIC_ARC_FURNACE', 
     '{"renewable_pct": 100, "grid_pct": 0, "wind_ppa_pct": 85, "hydro_pct": 15}'::jsonb, 
     '["ISO_14064", "ISO_14067", "EPD_SWEDEN", "RECs"]'::jsonb, 'THIRD_PARTY_ASSURED', 250000.00),
    
    -- Silesian Blast Furnace (Coal-powered BOF in Poland)
    ('SITE_KATOWICE_BOF', 'SUPP_SILESIAN_STEEL', 'Katowice Blast Furnace & BOF', 'PL', 'PL_GRID', 'BLAST_FURNACE_BOF', 
     '{"renewable_pct": 5, "grid_pct": 95, "coal_onsite_coke_pct": 90}'::jsonb, 
     '["ISO_9001"]'::jsonb, 'UNVERIFIED', 450000.00),
    
    -- Apex Polymers (Jurong Island, Singapore)
    ('SITE_JURONG_POLYMER', 'SUPP_APEX_POLYMERS', 'Jurong Petrochemical Island Facility', 'SG', 'SG_MAIN', 'POLYMER_EXTRUSION', 
     '{"renewable_pct": 30, "grid_pct": 70, "onsite_solar_pct": 10}'::jsonb, 
     '["ISO_14067", "ISCC_PLUS"]'::jsonb, 'THIRD_PARTY_ASSURED', 120000.00),
    
    -- Pacific Silicon Wafer (Hsinchu Science Park, Taiwan)
    ('SITE_HSINCHU_FAB1', 'SUPP_PACIFIC_WAFER', 'Hsinchu High-Purity Ingot Fab 1', 'TW', 'TW_NORTH', 'SILICON_CRYSTALLIZATION', 
     '{"renewable_pct": 65, "grid_pct": 35, "i_rec_certified": true}'::jsonb, 
     '["ISO_14064", "I_REC"]'::jsonb, 'THIRD_PARTY_ASSURED', 50000.00),
     
    -- Shenzhen Precision Stamping (Baoan, Shenzhen, China)
    ('SITE_BAOAN_PLANT', 'SUPP_SHENZHEN_STAMPING', 'Baoan Metal Forming Works', 'CN', 'CN_SOUTH_GRID', 'COLD_STAMPING_PRESS', 
     '{"renewable_pct": 0, "grid_pct": 100}'::jsonb, 
     '[]'::jsonb, 'UNVERIFIED', 80000.00),

    -- Transatlantic Container Lines (Rotterdam Marine Hub)
    ('SITE_ROTTERDAM_HUB', 'SUPP_TRANSATLANTIC_LOG', 'Port of Rotterdam Terminal', 'NL', 'NL_GRID', 'MARITIME_CONTAINER_SHIPPING',
     '{"renewable_pct": 20, "grid_pct": 80}'::jsonb,
     '["CLEAN_CARGO_VERIFIED"]'::jsonb, 'THIRD_PARTY_ASSURED', 1000000.00),

    -- EcoFiber Packaging (Valencia Plant)
    ('SITE_VALENCIA_MILL', 'SUPP_ECO_PACKAGING', 'Valencia Paper & Carton Mill', 'ES', 'ES_PENINSULA', 'PULP_AND_PAPER_FORMING',
     '{"renewable_pct": 45, "grid_pct": 55, "biomass_onsite_pct": 30}'::jsonb,
     '["FSC_CHAIN_OF_CUSTODY", "ISO_14001"]'::jsonb, 'SELF_DECLARED', 60000.00),

    -- Alpine Cloud Infrastructure (Zurich Datacenter)
    ('SITE_ZURICH_DC1', 'SUPP_ALPINE_COMPUTE', 'Zurich Green Datacenter 1', 'CH', 'CH_GRID', 'HIGH_DENSITY_COMPUTE',
     '{"renewable_pct": 100, "hydro_pct": 100}'::jsonb,
     '["ISO_50001", "GREEN_POWER_CH"]'::jsonb, 'THIRD_PARTY_ASSURED', 10000.00)
ON CONFLICT (site_id) DO NOTHING;

-- 8. Evidence Artifact Registry
INSERT INTO evidence_artifact (artifact_id, artifact_type, file_name, file_hash_sha256, source, valid_from, valid_to, is_verified, verifier_name, verifier_accreditation, storage_uri)
VALUES
    ('ART_NORDIC_PCF_2025', 'PCF_REPORT', 'Nordic_Green_Steel_Hot_Rolled_Coil_ISO14067.pdf',
     '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08', 'SUPPLIER_PORTAL', '2025-01-01', '2026-12-31',
     TRUE, 'DNV Business Assurance', 'DAkkS_D-ZV-14067', 's3://carbon-assurance-vault/evidence/2025/nordic_pcf_2025.pdf'),
     
    ('ART_APEX_ISO14067', 'PCF_REPORT', 'Apex_Polymers_HDPE_Cradle_to_Gate_Verification.pdf',
     '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'SUPPLIER_PORTAL', '2025-01-01', '2026-06-30',
     TRUE, 'TÜV Rheinland Singapore', 'SAC_SINGAPORE_VERIFIED', 's3://carbon-assurance-vault/evidence/2025/apex_hdpe_2025.pdf'),
     
    ('ART_PACIFIC_IREC_2025', 'ENERGY_INVOICE', 'Pacific_Wafer_IREC_Taiwan_Power_Certificate.pdf',
     '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a', 'SUPPLIER_PORTAL', '2025-01-01', '2025-12-31',
     TRUE, 'Taiwan Renewable Energy Certificate (T-REC)', 'NATIONAL_BUREAU_STANDARDS', 's3://carbon-assurance-vault/evidence/2025/pacific_irec.pdf'),

    ('ART_EXPIRED_CERT_SAMPLE', 'ISO_CERTIFICATE', 'Expired_Grid_Renewable_Guarantee_2023.pdf',
     '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae', 'SUPPLIER_PORTAL', '2023-01-01', '2023-12-31',
     TRUE, 'Bureau Veritas Polska', 'PCA_ACCREDITED', 's3://carbon-assurance-vault/evidence/2023/silesian_expired.pdf')
ON CONFLICT (artifact_id) DO NOTHING;

-- 9. Reporting Periods
INSERT INTO reporting_period (period_id, period_code, start_date, end_date, state, bound_factor_library_version, bound_mapping_version, bound_formula_version)
VALUES
    ('2025-Q4', '2025-Q4', '2025-10-01', '2025-12-31', 'PERIOD_OPEN', 'LIB_GHG_2024:2024.1;LIB_ECOINVENT_310:3.10', 'MAP_V2025_Q4', 'FORMULA_ENGINE_V1.0'),
    ('2025-FY', '2025-FY', '2025-01-01', '2025-12-31', 'PERIOD_OPEN', 'LIB_GHG_2024:2024.1;LIB_ECOINVENT_310:3.10', 'MAP_V2025_FY', 'FORMULA_ENGINE_V1.0'),
    ('2024-FY', '2024-FY', '2024-01-01', '2024-12-31', 'HARD_LOCK',   'LIB_GHG_2024:2024.1;LIB_ECOINVENT_310:3.10', 'MAP_V2024_FY', 'FORMULA_ENGINE_V1.0')
ON CONFLICT (period_id) DO NOTHING;
