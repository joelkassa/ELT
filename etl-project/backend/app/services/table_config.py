"""
Single source of truth for the 8 target tables, matching Safe Minds' real Excel exports.

year_source:
  "manual"      -> year comes from the folder name (passed in per-file)
  ("date", fld) -> year is auto-extracted from the row's date field `fld`

numeric_fields: columns that should silently default to 0 (not flagged) when missing/blank,
since they represent quantities where "no value" means "zero", not "unknown".

system_managed_fields: columns the app populates/manages itself (not expected in the
source Excel), so they are never flagged as "missing" even though they're in `columns`.

id_label_pairs: (id_field, label_field) pairs to check for consistency -- if the same
id appears with a different label (after normalizing case/whitespace) either elsewhere
in the same upload batch or already in the database, both rows are flagged, regardless
of what any other column contains.
"""

FINAL_TABLES = {
    "budget": {
        "columns": ["grant_id", "year", "program", "budget_code", "activity",
                    "program_activity_amt", "procurement_amt", "amount_etb",
                    "amount_usd", "adjusted_usd", "exchange_rate", "cost_category"],
        "date_fields": [],
        "numeric_fields": ["program_activity_amt", "procurement_amt", "amount_etb",
                            "amount_usd", "adjusted_usd", "exchange_rate"],
        "year_source": "manual",
        "unique_key": ["grant_id", "year", "program", "budget_code", "activity"],
        "keywords": ["budget"],
        "system_managed_fields": [],
        "id_label_pairs": [],
    },
    "income": {
        "columns": ["grant_id", "year", "account_description", "date", "reference",
                    "journal", "trans_description", "debit", "credit", "balance",
                    "job_id", "customer_id"],
        "date_fields": ["date"],
        "numeric_fields": ["debit", "credit", "balance"],
        "year_source": ("date", "date"),
        "unique_key": ["grant_id", "year", "reference", "date", "debit", "credit"],
        "keywords": ["income"],
        "system_managed_fields": [],
        "id_label_pairs": [],
    },
    "expenditure": {
        "columns": ["grant_id", "year", "date", "reference", "journal", "trans_description",
                    "account_id", "account_description", "debit", "credit", "balance",
                    "job_id", "customer_id"],
        "date_fields": ["date"],
        "numeric_fields": ["debit", "credit", "balance"],
        "year_source": ("date", "date"),
        "unique_key": ["grant_id", "year", "reference", "date", "debit", "credit"],
        "keywords": ["expenditure", "expense"],
        "system_managed_fields": [],
        "id_label_pairs": [("account_id", "account_description")],
    },
    "liquidation": {
        "columns": ["grant_id", "year", "customer_id", "customer", "date", "trans_no",
                    "type", "debit", "credit", "balance", "date_due"],
        "date_fields": ["date", "date_due"],
        "numeric_fields": ["debit", "credit", "balance"],
        "year_source": ("date", "date"),
        "unique_key": ["grant_id", "year", "customer_id", "trans_no", "date"],
        "keywords": ["liquidation"],
        "system_managed_fields": [],
        "id_label_pairs": [("customer_id", "customer")],
    },
    "ageing": {
        "columns": ["grant_id", "year", "customer_id", "customer_name", "invoice_number",
                    "less_than_6m", "six_m_to_1yr", "one_to_2yr", "over_2yr", "amount_due",
                    "date", "date_due", "job_id", "total"],
        "date_fields": ["date", "date_due"],
        "numeric_fields": ["less_than_6m", "six_m_to_1yr", "one_to_2yr", "over_2yr", "amount_due", "total"],
        "year_source": ("date", "date"),
        "unique_key": ["grant_id", "year", "customer_id", "invoice_number"],
        "keywords": ["ageing", "aging"],
        "system_managed_fields": [],
        "id_label_pairs": [("customer_id", "customer_name")],
    },
    "customer_list": {
        "columns": ["grant_id", "year", "customer_id", "customer_name", "category"],
        "date_fields": [],
        "numeric_fields": [],
        "year_source": "manual",
        "unique_key": ["grant_id", "year", "customer_id"],
        "keywords": ["customer"],
        "system_managed_fields": ["category"],
        "id_label_pairs": [("customer_id", "customer_name")],
    },
    "job_list": {
        "columns": ["grant_id", "year", "job_id", "job_description"],
        "date_fields": [],
        "numeric_fields": [],
        "year_source": "manual",
        "unique_key": ["grant_id", "year", "job_id"],
        "keywords": ["job"],
        "system_managed_fields": [],
        "id_label_pairs": [("job_id", "job_description")],
    },
    "trial_balance": {
        "columns": ["grant_id", "year", "account_id", "account_description", "debit",
                    "credit", "account_type", "current_bal", "last_fye_bal"],
        "date_fields": [],
        "numeric_fields": ["debit", "credit", "current_bal", "last_fye_bal"],
        "year_source": "manual",
        "unique_key": ["grant_id", "year", "account_id"],
        "keywords": ["trial balance", "trial_balance", "tb"],
        "system_managed_fields": [],
        "id_label_pairs": [("account_id", "account_description")],
    },
}

FIELD_SYNONYMS = {
    "program": ["program"],
    "budget_code": ["budget code"],
    "activity": ["activity"],
    "program_activity_amt": ["program activity amt", "program activity amount"],
    "procurement_amt": ["procurement amt", "procurement amount"],
    "amount_etb": ["amount etb", "amount birr"],
    "amount_usd": ["amount usd", "amount dollar", "amount $"],
    "adjusted_usd": ["adjusted usd", "adjusted amount", "adjusted $"],
    "exchange_rate": ["exchange rate", "fx rate"],
    "cost_category": ["cost category"],
    "account_description": ["account description"],
    "date": ["date"],
    "reference": ["reference", "ref"],
    "journal": ["jrnl", "journal"],
    "trans_description": ["trans description", "transaction description"],
    "debit": ["debit amt", "debit", "dr"],
    "credit": ["credit amt", "credit", "cr"],
    "balance": ["balance", "bal"],
    "job_id": ["job id"],
    "customer_id": ["customer id"],
    "account_id": ["account id"],
    "customer": ["customer"],
    "trans_no": ["trans no", "transaction no", "trans number"],
    "type": ["type"],
    "date_due": ["date due", "due date"],
    "customer_name": ["customer name", "customername"],
    "invoice_number": ["invoice cm", "invoice number", "invoice/cm"],
    "less_than_6m": ["less than 6m"],
    "six_m_to_1yr": ["6m 1yer", "6m 1yr", "6 months to 1 year"],
    "one_to_2yr": ["1yr 2yr", "1 to 2 years"],
    "over_2yr": ["over 2yrs", "over 2 years"],
    "amount_due": ["amount due"],
    "total": ["total"],
    "category": ["category"],
    "job_description": ["job description"],
    "account_type": ["account type"],
    "current_bal": ["current bal", "current balance"],
    "last_fye_bal": ["last fye bal", "last fye balance"],
}

ALL_TABLE_NAMES = list(FINAL_TABLES.keys())