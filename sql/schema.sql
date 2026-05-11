-- =====================================================================
-- Patent Intelligence schema (SQLite)
-- Drop-and-recreate is safe because all data is reloaded from clean CSVs.
-- =====================================================================

DROP TABLE IF EXISTS relationships;
DROP TABLE IF EXISTS patents;
DROP TABLE IF EXISTS inventors;
DROP TABLE IF EXISTS companies;

-- Core fact table: one row per granted patent.
CREATE TABLE patents (
    patent_id    TEXT PRIMARY KEY,
    title        TEXT,
    abstract     TEXT,
    filing_date  TEXT,        -- ISO date string; loaded from PatentsView grant date
    year         INTEGER
);

-- Disambiguated inventors. One row per unique inventor entity.
CREATE TABLE inventors (
    inventor_id  TEXT PRIMARY KEY,
    name         TEXT,
    country      TEXT          -- ISO 2-letter, derived from disambiguated location
);

-- Disambiguated assignees (companies). Individuals are filtered out
-- during cleaning so this table only contains organizations.
CREATE TABLE companies (
    company_id   TEXT PRIMARY KEY,
    name         TEXT
);

-- Many-to-many bridge: each row links a patent to (optionally) an inventor
-- and a company. A patent typically appears in multiple rows because it
-- has multiple inventors and/or multiple assignees.
CREATE TABLE relationships (
    patent_id    TEXT NOT NULL,
    inventor_id  TEXT,
    company_id   TEXT,
    FOREIGN KEY (patent_id)   REFERENCES patents(patent_id),
    FOREIGN KEY (inventor_id) REFERENCES inventors(inventor_id),
    FOREIGN KEY (company_id)  REFERENCES companies(company_id)
);

-- Indexes for the analytical queries.
CREATE INDEX idx_rel_patent    ON relationships(patent_id);
CREATE INDEX idx_rel_inventor  ON relationships(inventor_id);
CREATE INDEX idx_rel_company   ON relationships(company_id);
CREATE INDEX idx_patents_year  ON patents(year);
CREATE INDEX idx_inventors_country ON inventors(country);
