-- Thusa core schema (draft v0.1, DuckDB dialect). Design: docs/design/application-design.md §6
-- Conventions: money = BIGINT cents (ZAR); timestamps = TIMESTAMPTZ stored UTC; NULL = unknown (never 0).
-- Migrations: each change to this file ships as migrations/NNNN_up.sql + NNNN_down.sql (ADR-0002).
-- NOTE (v0.1.0): the implemented MVP schema is defined by thusa/models/**/*.sql and thusa/staging.py (ADR-0007);
-- this file remains the target logical model. Coverage states implemented: present|partial|missing|n.a.

CREATE SCHEMA IF NOT EXISTS curated;
CREATE SCHEMA IF NOT EXISTS ops;

-- Provenance -------------------------------------------------------------
CREATE TABLE curated.source (
  source_id            VARCHAR PRIMARY KEY,        -- e.g. 'muni_api', 'etenders_ocds'
  name                 VARCHAR NOT NULL,
  owner_org            VARCHAR NOT NULL,
  url                  VARCHAR NOT NULL,
  licence              VARCHAR,
  cadence              VARCHAR,                    -- daily|weekly|monthly|quarterly|annual|adhoc
  sla_freshness_days   INTEGER
);

CREATE TABLE curated.source_snapshot (
  snapshot_id          VARCHAR PRIMARY KEY,        -- sha256 of bytes + source_id
  source_id            VARCHAR NOT NULL REFERENCES curated.source(source_id),
  url                  VARCHAR NOT NULL,
  retrieved_at_utc     TIMESTAMPTZ NOT NULL,
  http_status          INTEGER,
  sha256               VARCHAR NOT NULL,
  bytes                BIGINT,
  parser_version       VARCHAR,
  status               VARCHAR NOT NULL CHECK (status IN ('ok','unchanged','failed','blocked')),
  raw_path             VARCHAR
);

-- Dimensions -------------------------------------------------------------
CREATE TABLE curated.gov_body (
  gov_body_id          VARCHAR PRIMARY KEY,
  name                 VARCHAR NOT NULL,
  sphere               VARCHAR NOT NULL CHECK (sphere IN ('national','provincial','local','soe','public_entity','constitutional','education','health','legislature')),
  body_type            VARCHAR NOT NULL,           -- department|metro|district|local|soe|schedule3a|seta|tvet|university|...
  province             VARCHAR,
  demarcation_code     VARCHAR,                    -- MDB code for municipalities, e.g. 'CPT'
  nt_vote_no           VARCHAR,
  pfma_schedule        VARCHAR,
  parent_gov_body_id   VARCHAR,
  valid_from           DATE,
  valid_to             DATE
);

CREATE TABLE curated.gov_body_alias (
  alias                VARCHAR NOT NULL,
  source_id            VARCHAR NOT NULL,
  gov_body_id          VARCHAR NOT NULL REFERENCES curated.gov_body(gov_body_id),
  match_method         VARCHAR NOT NULL,           -- exact|crosswalk|manual
  confidence           DOUBLE,
  reviewed_by          VARCHAR,
  PRIMARY KEY (alias, source_id)
);

CREATE TABLE curated.supplier (
  supplier_id          VARCHAR PRIMARY KEY,
  canonical_name       VARCHAR NOT NULL,
  cipc_reg_no          VARCHAR,                    -- e.g. 2015/313861/07 when published
  supplier_type        VARCHAR,                    -- company|cc|person|soe|listed|foreign|unknown
  is_person            BOOLEAN NOT NULL DEFAULT FALSE,
  person_id_hmac       VARCHAR,                    -- HMAC(SA ID) for matching only; never published (POPIA)
  province             VARCHAR,
  first_seen           DATE
);

CREATE TABLE curated.supplier_alias (
  raw_name             VARCHAR NOT NULL,
  raw_reg_no           VARCHAR,
  source_id            VARCHAR NOT NULL,
  supplier_id          VARCHAR NOT NULL REFERENCES curated.supplier(supplier_id),
  match_method         VARCHAR NOT NULL,           -- reg_no|normalised_name|splink|manual
  confidence           DOUBLE,
  review_status        VARCHAR DEFAULT 'auto' CHECK (review_status IN ('auto','pending','accepted','rejected'))
);

CREATE TABLE curated.commodity (
  commodity_id         VARCHAR PRIMARY KEY,
  scheme               VARCHAR NOT NULL CHECK (scheme IN ('UNSPSC','SCOA','MIIN','COICOP','INTERNAL')),
  code                 VARCHAR NOT NULL,
  label                VARCHAR NOT NULL,
  parent_id            VARCHAR
);

CREATE TABLE curated.period (
  period_id            VARCHAR PRIMARY KEY,        -- e.g. 'NAT-FY2025-26', 'MUN-FY2025-26-Q2'
  fiscal_scheme        VARCHAR NOT NULL CHECK (fiscal_scheme IN ('national','municipal','calendar')),
  fy_label             VARCHAR NOT NULL,
  quarter              INTEGER,
  month                INTEGER,
  start_date           DATE NOT NULL,
  end_date             DATE NOT NULL
);

CREATE TABLE curated.geography (
  geo_id               VARCHAR PRIMARY KEY,
  level                VARCHAR NOT NULL,           -- country|province|district|local
  code                 VARCHAR,
  name                 VARCHAR NOT NULL,
  population           BIGINT,
  households           BIGINT,
  source_year          INTEGER
);

-- Facts -----------------------------------------------------------------
CREATE TABLE curated.budget_line (
  gov_body_id VARCHAR NOT NULL, period_id VARCHAR NOT NULL, item_code VARCHAR, item_label VARCHAR,
  budget_phase VARCHAR,                            -- original|adjusted|audited|preaudit
  amount_cents BIGINT, source_snapshot_id VARCHAR NOT NULL, source_locator VARCHAR
);

CREATE TABLE curated.actual_line (
  gov_body_id VARCHAR NOT NULL, period_id VARCHAR NOT NULL, item_code VARCHAR, item_label VARCHAR,
  amount_cents BIGINT, source_snapshot_id VARCHAR NOT NULL, source_locator VARCHAR
);

CREATE TABLE curated.award (
  ocid VARCHAR NOT NULL, award_id VARCHAR NOT NULL, buyer_gov_body_id VARCHAR, supplier_id VARCHAR,
  procurement_method VARCHAR, award_date DATE, value_cents BIGINT, currency VARCHAR DEFAULT 'ZAR',
  title VARCHAR, source_snapshot_id VARCHAR NOT NULL, source_locator VARCHAR,
  PRIMARY KEY (ocid, award_id)
);

CREATE TABLE curated.payment_agg (                 -- Procurement Payments Dashboard grain
  gov_body_id VARCHAR NOT NULL, supplier_id VARCHAR, commodity_id VARCHAR, period_id VARCHAR NOT NULL,
  system VARCHAR CHECK (system IN ('BAS','LOGIS','OCPO_UPLOAD')),
  contract_type VARCHAR,                           -- LOGIS: departmental|provincial|non_contract|transversal|regional|facility
  amount_cents BIGINT, txn_count INTEGER, quantity DOUBLE, avg_unit_price_cents BIGINT,
  source_snapshot_id VARCHAR NOT NULL, source_locator VARCHAR
);

CREATE TABLE curated.uifw_line (
  gov_body_id VARCHAR NOT NULL, period_id VARCHAR NOT NULL,
  uifw_type VARCHAR CHECK (uifw_type IN ('unauthorised','irregular','fruitless_wasteful')),
  measure VARCHAR CHECK (measure IN ('incurred','opening','condoned','written_off','recovered','under_assessment','closing')),
  amount_cents BIGINT, source_snapshot_id VARCHAR NOT NULL, source_locator VARCHAR
);

CREATE TABLE curated.audit_outcome (
  gov_body_id VARCHAR NOT NULL, fy_label VARCHAR NOT NULL,
  opinion VARCHAR,                                 -- clean|unqualified_findings|qualified|adverse|disclaimer|outstanding
  afs_submitted BOOLEAN, mi_count INTEGER, ie_completeness_qualified BOOLEAN,
  source_snapshot_id VARCHAR NOT NULL, source_locator VARCHAR,
  PRIMARY KEY (gov_body_id, fy_label)
);

CREATE TABLE curated.restriction (
  supplier_id VARCHAR NOT NULL, authority_gov_body_id VARCHAR, restriction_type VARCHAR, reason VARCHAR,
  period_from DATE, period_to DATE, source_snapshot_id VARCHAR NOT NULL, source_locator VARCHAR
);

CREATE TABLE curated.enforcement_event (
  case_ref VARCHAR NOT NULL, gov_body_id VARCHAR, agency VARCHAR, event_type VARCHAR,
  event_date DATE, amount_cents BIGINT, description VARCHAR, source_snapshot_id VARCHAR NOT NULL, source_locator VARCHAR
);

CREATE TABLE curated.benchmark_observation (
  series_id VARCHAR NOT NULL,                      -- e.g. 'dmpr_diesel_50ppm_wholesale_coastal'
  region VARCHAR, obs_date DATE NOT NULL, value DOUBLE NOT NULL, unit VARCHAR NOT NULL,
  source_snapshot_id VARCHAR NOT NULL, source_locator VARCHAR
);

-- Analytical outputs ------------------------------------------------------
CREATE TABLE curated.flag (
  flag_id VARCHAR PRIMARY KEY, detector_id VARCHAR NOT NULL, detector_version VARCHAR NOT NULL,
  subject_type VARCHAR NOT NULL, subject_id VARCHAR NOT NULL, period_id VARCHAR,
  severity VARCHAR CHECK (severity IN ('info','low','med','high')), score DOUBLE,
  explanation_md VARCHAR NOT NULL, evidence_json JSON NOT NULL, benchmark_ref VARCHAR,
  status VARCHAR NOT NULL DEFAULT 'open' CHECK (status IN ('open','reviewed','dismissed','published')),
  reviewed_by VARCHAR, created_run_id VARCHAR NOT NULL
);

CREATE TABLE curated.coverage_cell (
  entity_id VARCHAR NOT NULL, dataset_id VARCHAR NOT NULL, period_id VARCHAR NOT NULL,
  expected BOOLEAN NOT NULL, observed BOOLEAN NOT NULL, completeness_pct DOUBLE,
  state VARCHAR NOT NULL CHECK (state IN ('complete','partial','missing','late','unaudited','out_of_scope','not_applicable')),
  reason_code VARCHAR, reason_source_snapshot_id VARCHAR,
  PRIMARY KEY (entity_id, dataset_id, period_id)
);

-- Ops ---------------------------------------------------------------------
CREATE TABLE ops.ingest_run (
  run_id VARCHAR PRIMARY KEY, source_id VARCHAR NOT NULL, started_at_utc TIMESTAMPTZ, ended_at_utc TIMESTAMPTZ,
  status VARCHAR CHECK (status IN ('ok','unchanged','failed','blocked','partial')), rows_loaded BIGINT,
  error_class VARCHAR, error_detail VARCHAR, git_commit VARCHAR
);

CREATE TABLE ops.dq_result (
  build_id VARCHAR NOT NULL, test_name VARCHAR NOT NULL, status VARCHAR NOT NULL, failures BIGINT, run_at_utc TIMESTAMPTZ
);

CREATE TABLE ops.paia_request (
  paia_id VARCHAR PRIMARY KEY, body VARCHAR NOT NULL, records_requested VARCHAR NOT NULL,
  lodged_on DATE, deemed_refusal_on DATE, outcome VARCHAR, publishable BOOLEAN
);
