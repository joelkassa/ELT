CREATE TABLE IF NOT EXISTS grants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ethiopian_calendar (
    gregorian_date DATE PRIMARY KEY,
    ethiopian_year INTEGER NOT NULL,
    ethiopian_month INTEGER NOT NULL,
    ethiopian_month_name VARCHAR(20) NOT NULL,
    ethiopian_day INTEGER NOT NULL,
    ethiopian_fiscal_year INTEGER NOT NULL,
    ethiopian_fiscal_quarter INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging_uploads (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    source_filename VARCHAR(255) NOT NULL,
    sheet_name VARCHAR(255),
    row_index INTEGER NOT NULL,
    grant_name VARCHAR(255),
    year INTEGER,
    raw_data JSONB NOT NULL,
    suggested_target_table VARCHAR(50),
    confirmed_target_table VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    validation_issues JSONB,
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS budget (
    id SERIAL PRIMARY KEY,
    grant_id INTEGER NOT NULL REFERENCES grants(id),
    year INTEGER NOT NULL,
    program VARCHAR(255),
    budget_code VARCHAR(100),
    activity VARCHAR(255),
    program_activity_amt NUMERIC(18,2),
    procurement_amt NUMERIC(18,2),
    amount_etb NUMERIC(18,2),
    amount_usd NUMERIC(18,2),
    adjusted_usd NUMERIC(18,2),
    exchange_rate NUMERIC(10,4),
    cost_category VARCHAR(255),
    source_filename VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (grant_id, year, program, budget_code, activity)
);

CREATE TABLE IF NOT EXISTS income (
    id SERIAL PRIMARY KEY,
    grant_id INTEGER NOT NULL REFERENCES grants(id),
    year INTEGER NOT NULL,
    account_description VARCHAR(255),
    date DATE,
    reference VARCHAR(100),
    journal VARCHAR(100),
    trans_description TEXT,
    debit NUMERIC(18,2),
    credit NUMERIC(18,2),
    balance NUMERIC(18,2),
    job_id VARCHAR(100),
    customer_id VARCHAR(100),
    source_filename VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (grant_id, year, reference, date, debit, credit)
);

CREATE TABLE IF NOT EXISTS expenditure (
    id SERIAL PRIMARY KEY,
    grant_id INTEGER NOT NULL REFERENCES grants(id),
    year INTEGER NOT NULL,
    date DATE,
    reference VARCHAR(100),
    journal VARCHAR(100),
    trans_description TEXT,
    account_id VARCHAR(100),
    account_description VARCHAR(255),
    debit NUMERIC(18,2),
    credit NUMERIC(18,2),
    balance NUMERIC(18,2),
    job_id VARCHAR(100),
    customer_id VARCHAR(100),
    source_filename VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (grant_id, year, reference, date, debit, credit)
);

CREATE TABLE IF NOT EXISTS liquidation (
    id SERIAL PRIMARY KEY,
    grant_id INTEGER NOT NULL REFERENCES grants(id),
    year INTEGER NOT NULL,
    customer_id VARCHAR(100),
    customer VARCHAR(255),
    date DATE,
    trans_no VARCHAR(100),
    type VARCHAR(100),
    debit NUMERIC(18,2),
    credit NUMERIC(18,2),
    balance NUMERIC(18,2),
    date_due DATE,
    source_filename VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (grant_id, year, customer_id, trans_no, date)
);

CREATE TABLE IF NOT EXISTS ageing (
    id SERIAL PRIMARY KEY,
    grant_id INTEGER NOT NULL REFERENCES grants(id),
    year INTEGER NOT NULL,
    customer_id VARCHAR(100),
    customer_name VARCHAR(255),
    invoice_number VARCHAR(100),
    less_than_6m NUMERIC(18,2),
    six_m_to_1yr NUMERIC(18,2),
    one_to_2yr NUMERIC(18,2),
    over_2yr NUMERIC(18,2),
    amount_due NUMERIC(18,2),
    date DATE,
    date_due DATE,
    job_id VARCHAR(100),
    total NUMERIC(18,2),
    source_filename VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (grant_id, year, customer_id, invoice_number)
);

CREATE TABLE IF NOT EXISTS customer_list (
    id SERIAL PRIMARY KEY,
    grant_id INTEGER NOT NULL REFERENCES grants(id),
    year INTEGER NOT NULL,
    customer_id VARCHAR(100),
    customer_name VARCHAR(255),
    category VARCHAR(255),
    source_filename VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (grant_id, year, customer_id)
);

CREATE TABLE IF NOT EXISTS job_list (
    id SERIAL PRIMARY KEY,
    grant_id INTEGER NOT NULL REFERENCES grants(id),
    year INTEGER NOT NULL,
    job_id VARCHAR(100),
    job_description TEXT,
    source_filename VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (grant_id, year, job_id)
);

CREATE TABLE IF NOT EXISTS trial_balance (
    id SERIAL PRIMARY KEY,
    grant_id INTEGER NOT NULL REFERENCES grants(id),
    year INTEGER NOT NULL,
    account_id VARCHAR(100),
    account_description VARCHAR(255),
    debit NUMERIC(18,2),
    credit NUMERIC(18,2),
    account_type VARCHAR(100),
    current_bal NUMERIC(18,2),
    last_fye_bal NUMERIC(18,2),
    source_filename VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (grant_id, year, account_id)
);