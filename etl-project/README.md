# Grant ETL System

A complete, production-ready **Extract-Transform-Load (ETL) pipeline** for grant financial data. 

**Workflow:** Upload Excel files → auto-detect & map data into 8 grant reporting tables → validate & review flagged rows → accept/reject → commit to PostgreSQL → visualize in Superset.

---

## 📋 Table of Contents

1. [Overview & Features](#overview--features)
2. [The 8 Grant Tables](#the-8-grant-tables)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [Backend Setup](#backend-setup)
6. [Frontend Setup](#frontend-setup)
7. [Usage Guide](#usage-guide)
8. [API Reference](#api-reference)
9. [Key Features Deep Dive](#key-features-deep-dive)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview & Features

### What It Does

- **Batch Upload**: Drag & drop or select folders containing `.xlsx` files organized in `YYYY/GrantName/` structure
- **Intelligent Auto-Detection**: Analyzes filenames, sheet names, and column headers to suggest the correct target table for each sheet
- **Smart Field Mapping**: Uses fuzzy matching and synonym libraries to map your Excel columns to the database schema
- **Comprehensive Validation**: 
  - Detects duplicates (both within upload batch and against existing database)
  - **ID/Label Consistency Check**: Flags when the same ID (e.g., customer_id) appears with different spellings of labels (e.g., customer_name)
  - Flags missing required fields, unparseable dates, non-standard country names
  - Identifies total/subtotal rows for manual review
  - Silently defaults numeric fields to 0 (e.g., budget amounts)
- **Data Quality Scoring**: Computes completeness, validity, uniqueness, and consistency metrics for all final tables
- **Customer Intelligence**: Auto-classifies customer names by region, donor, agency, university, or hospital with smart alias mapping
- **Interactive Review**: Web UI shows every flagged row with inline editing
- **Flexible Actions**: Accept, reject, or edit each row before committing
- **Database Commit**: Only rows you accept are inserted; rejected rows are discarded
- **Post-Upload Summary**: Compares what was parsed from Excel against what landed in the database
- **Export Options**: Download summaries as XLSX, CSV, or PDF

### Key Validations & Standardizations

| Issue | Handling |
|-------|----------|
| **Missing numeric field** | Auto-defaults to 0 (not flagged) |
| **Missing required field** | Flagged; requires manual edit or rejection |
| **Duplicate (in batch)** | Flagged; compares ALL columns with formatting-aware matching |
| **Duplicate (in DB)** | Flagged; compares ALL columns with formatting-aware matching |
| **ID/Label mismatch** | Flagged when same ID (e.g., customer_id) appears with different label spellings |
| **Invalid date format** | Reformatted to DD/MM/YYYY; flagged if input changed |
| **Non-standard country** | Standardized using pycountry; flagged if changed |
| **Total/Subtotal row** | Detected & flagged; suggested for rejection |

---

## 📊 The 8 Grant Tables

Each table has a unique schema matched to Safe Minds' real Excel exports. All tables include `grant_id` and `year` as foreign key / grouping dimensions.

### 1. **budget**
Financial allocations and procurement budgets.
- **Unique Key**: `(grant_id, year, program, budget_code, activity)`
- **Key Fields**: `budget_code`, `activity`, `program_activity_amt`, `procurement_amt`, `amount_etb`, `amount_usd`, `adjusted_usd`, `exchange_rate`
- **Year Source**: Manual (from folder name)
- **Keywords**: `budget`

### 2. **income**
Receipts, journal entries with debit/credit totals.
- **Unique Key**: `(grant_id, year, reference, date, debit, credit)`
- **Key Fields**: `date`, `reference`, `journal`, `debit`, `credit`, `balance`, `job_id`, `customer_id`
- **Year Source**: Extracted from `date` field
- **Keywords**: `income`

### 3. **expenditure**
Payments, outflows, journal entries by account.
- **Unique Key**: `(grant_id, year, reference, date, debit, credit)`
- **Key Fields**: `date`, `reference`, `journal`, `account_id`, `account_description`, `debit`, `credit`, `balance`, `job_id`, `customer_id`
- **Year Source**: Extracted from `date` field
- **Keywords**: `expenditure`, `expense`

### 4. **liquidation**
Customer balances, accounts receivable aging.
- **Unique Key**: `(grant_id, year, customer_id, trans_no, date)`
- **Key Fields**: `customer_id`, `customer`, `date`, `trans_no`, `type`, `debit`, `credit`, `balance`, `date_due`
- **Year Source**: Extracted from `date` field
- **Keywords**: `liquidation`

### 5. **ageing**
Aged customer balances (bucketed by time periods).
- **Unique Key**: `(grant_id, year, customer_id, invoice_number)`
- **Key Fields**: `invoice_number`, `less_than_6m`, `six_m_to_1yr`, `one_to_2yr`, `over_2yr`, `amount_due`, `total`, `job_id`
- **Year Source**: Extracted from `date` field
- **Keywords**: `ageing`, `aging`

### 6. **customer_list**
Master list of customers/counterparties per grant.
- **Unique Key**: `(grant_id, year, customer_id)`
- **Key Fields**: `customer_id`, `customer_name`, `category`
- **Year Source**: Manual (from folder name)
- **Keywords**: `customer`

### 7. **job_list**
Master list of jobs/projects per grant.
- **Unique Key**: `(grant_id, year, job_id)`
- **Key Fields**: `job_id`, `job_description`
- **Year Source**: Manual (from folder name)
- **Keywords**: `job`

### 8. **trial_balance**
Chart of accounts with debit/credit balances.
- **Unique Key**: `(grant_id, year, account_id)`
- **Key Fields**: `account_id`, `account_description`, `account_type`, `debit`, `credit`, `current_bal`, `last_fye_bal`
- **Year Source**: Manual (from folder name)
- **Keywords**: `trial balance`, `trial_balance`, `tb`

---

## 🏗️ Architecture

### Backend (FastAPI + SQLAlchemy + PostgreSQL)

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, CORS config
│   ├── routers/
│   │   └── upload.py            # All HTTP endpoints
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response models
│   ├── services/
│   │   ├── excel_parser.py      # Reads Excel, suggests tables & column mappings
│   │   ├── staging_service.py   # Batch ingest: creates staging rows, runs validations
│   │   ├── row_processor.py     # Maps raw → schema-compliant data
│   │   ├── commit_service.py    # Review decisions → final table inserts
│   │   ├── summary_service.py   # Post-upload comparison: Excel vs Database
│   │   ├── export_service.py    # XLSX, CSV, PDF generation
│   │   ├── table_config.py      # Schema definitions, field synonyms
│   │   └── ethiopian_calendar.py # Ethiopian date handling
│   ├── database/
│   │   ├── connection.py        # SQLAlchemy engine & session
│   │   ├── create_tables.py     # Runs schema.sql on startup
│   │   ├── schema.sql           # DDL for all 9 tables
│   │   ├── db_helpers.py        # Insert, query, update helpers
│   │   ├── reset_schema.py      # Dev utility to wipe & recreate
│   │   └── clear_data.py        # Dev utility to clear data only
│   └── utils/
│       ├── matching.py          # Fuzzy field name matching
│       └── validators.py        # Date & country normalization
├── requirements.txt             # Python dependencies
└── .env.example                 # Database connection template
```

**Database Schema:**
- **staging_uploads** (9 columns): Temporary holding for all parsed rows before review
- **8 final tables** (varying columns): Committed, deduplicated data
- **grants** (2 columns): Grant master list (grant_id, name)

**Key Services:**
- **staging_service.ingest_files()**: Orchestrates batch upload → parsing → validation → staging insert
- **commit_service.apply_review_decisions()**: Processes review actions (accept/reject/edit) → final table inserts with idempotency guards
- **summary_service.compute_summary()**: Compares staging counts, statuses, and totals vs. final tables
- **export_service**: Renders XLSX, CSV, PDF from summary data

### Frontend (React + Vite)

```
frontend/
├── src/
│   ├── main.jsx                 # Entry point
│   ├── App.jsx                  # Main container (orchestrates 3 phases)
│   ├── api.js                   # Fetch wrapper for all endpoints
│   ├── index.css                # Global styles
│   └── components/
│       ├── FolderUploadForm.jsx  # Phase 1: Folder selection & upload
│       ├── DataReview.jsx        # Phase 2: Interactive review of flagged rows
│       ├── SummaryReport.jsx     # Phase 3: Post-commit summary & export
│       └── ErrorBoundary.jsx     # Error fallback
├── vite.config.js               # Vite build config
├── package.json                 # Dependencies & build scripts
└── .env.example                 # API base URL template
```

**3-Phase Workflow UI:**
1. **Upload**: Drag folder, confirm selections, set default grant/year
2. **Review**: Grouped by table & status; flag by issue; edit inline; accept/reject
3. **Summary**: Row counts (committed vs. rejected), optional export

---

## ✅ Prerequisites

- **Python 3.10+** (with pip, venv)
- **Node.js 18+** with npm
- **PostgreSQL 12+** with an existing database connected to your Superset instance
- **Internet** (first time setup downloads ~50 MB of Python & npm packages)

---

## 🔧 Backend Setup

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv

# Activate
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS/Linux
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `fastapi`, `uvicorn` → HTTP server
- `sqlalchemy`, `psycopg2-binary` → Database ORM & PostgreSQL driver
- `pandas`, `openpyxl` → Excel reading
- `pydantic` → Request validation
- `python-dateutil`, `pycountry` → Date & country normalization
- `reportlab` → PDF generation
- `python-multipart` → Multipart form data

### 3. Configure Database Connection

```bash
# Copy template
copy .env.example .env          # Windows
cp .env.example .env            # macOS/Linux

# Edit .env
```

Edit `.env` and set your real PostgreSQL connection:

```env
DATABASE_URL=postgresql+psycopg2://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME
CORS_ORIGINS=http://localhost:5173
```

**⚠️ Important:** Double-check the password segment—make sure it doesn't contain special characters that need URL encoding (e.g., `@` or `:` in the password must be URL-encoded as `%40` and `%3A`).

### 4. Create Tables

```bash
python -m app.database.create_tables
```

**Output:**
```
✅ staging_uploads + all 8 final tables created/verified successfully.
```

This runs `schema.sql`, which uses `CREATE TABLE IF NOT EXISTS` — safe to re-run, won't touch existing data.

### 5. Start Backend Server

```bash
uvicorn app.main:app --reload --port 8000
```

**Verify:** Visit `http://localhost:8000/docs` in your browser. You should see an interactive Swagger UI listing all endpoints.

---

## 🎨 Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

This installs React, Vite, and build tools (~200 MB).

### 2. Configure API URL (Optional)

If your backend isn't on `localhost:8000`:

```bash
copy .env.example .env          # Windows
cp .env.example .env            # macOS/Linux
```

Edit `.env`:

```env
VITE_API_BASE=http://YOUR_BACKEND_HOST:PORT/api
```

### 3. Start Dev Server

```bash
npm run dev
```

**Output:**
```
VITE v5.x.x  ready in 123 ms

➜  Local:   http://localhost:5173/
➜  press h to show help
```

Visit `http://localhost:5173` in your browser.

---

## 📖 Usage Guide

### Step 1: Prepare Your Files

Organize Excel files in this structure on your local filesystem:

```
MyGrants/
├── 2024/
│   ├── Grant-A/
│   │   ├── budget.xlsx
│   │   ├── income.xlsx
│   │   └── ageing.xlsx
│   └── Grant-B/
│       ├── expenditure.xlsx
│       └── trial_balance.xlsx
└── 2023/
    └── Grant-A/
        └── customer_list.xlsx
```

The ETL system will parse the folder structure as:
- **Year**: `2024` or `2023` (must be a 4-digit number)
- **Grant Name**: `Grant-A`, `Grant-B`, etc.
- **Files**: Any `.xlsx` or `.xls` files inside

### Step 2: Upload

1. In the browser, click **"Choose Folder"** and select `MyGrants/`
2. Review the file tree—you'll see:
   - ✅ Valid files grouped by year/grant
   - ❌ Invalid files (wrong extension, wrong folder depth) listed with reasons
3. Check/uncheck individual files, grants, or entire years to control what's uploaded
4. Choose **Summary Mode**: 
   - `per_grant` → one row per table per grant per year
   - `combined` → one row per table per year (all grants merged)
5. Optionally check **Auto-generate Summary** to skip manual trigger in Phase 3
6. Click **Upload**

**Backend Processing (~1-5 sec):**
- Parses all Excel sheets
- Suggests target table for each sheet (filename + sheet name + column header scoring)
- Maps raw columns to schema fields using fuzzy matching
- Detects duplicates (both in-batch and against DB)
- Identifies validation issues (missing fields, bad dates, etc.)
- Inserts all rows into `staging_uploads` table with status="pending"
- Returns `session_id` and preview grouped by table

### Step 3: Review Flagged Rows

The app shows a **grouped list**:
- **⚠ Needs manual table selection**: Rows the system couldn't auto-map
- **⚠ Duplicates**: Rows matching existing DB or repeated in this batch
- **⚠ Total / Subtotal rows**: Detected by pattern matching
- **Other flagged rows**: Missing fields, reformatted dates, standardized countries, etc.
- **Clean rows** (collapsed): No issues; auto-detect succeeded

For each row:

1. **Review the meta** (grant name, year, source file, sheet, staging ID)
2. **Read the flags** (yellow issue box lists all problems)
3. **Edit fields** inline if needed (direct text input on each field)
4. **Set target table** (if originally unmapped; dropdown of 8 tables)
5. **Action:**
   - ✅ **Accept**: Row will be inserted into the final table
   - ❌ **Reject**: Row is discarded (status="rejected")

**Bulk Actions** (available soon):
- Accept all clean rows in a group
- Reject all duplicates

### Step 4: Commit

Once you finish reviewing:
1. Click **"Submit All Decisions"**
2. The backend applies your accept/reject/edit actions in a single transaction
3. Accepted rows are inserted into their final tables
4. Staging rows are marked as "committed", "rejected", or "duplicate_skipped"
5. You're redirected to Phase 3

### Step 5: Summary & Export

A summary is generated automatically (if you checked "Auto Summary") or on demand:

**Summary shows:**
- **Table** + **Grant** + **Year**: Which data was loaded
- **excel_row_count**: How many non-total rows were parsed
- **db_row_count**: How many were actually committed
- **rejected_count**: How many you rejected
- **duplicate_skipped_count**: How many were duplicates (auto-skipped)
- **Comparison totals** (for income): Excel debit/credit sum vs. DB debit/credit sum, difference

**Export Options:**
- 📊 **XLSX**: Open in Excel, ready for charts
- 📄 **CSV**: Import to other tools
- 📑 **PDF**: Print-friendly report

---

## 📡 API Reference

All endpoints are under `/api/` prefix. Base URL: `http://localhost:8000/api`

### **GET /tables**
Lists the 8 target tables.

**Response:**
```json
{ "tables": ["budget", "income", "expenditure", "liquidation", "ageing", "customer_list", "job_list", "trial_balance"] }
```

---

### **GET /grants**
Lists all grant names currently in the database.

**Response:**
```json
{ "grants": ["Grant-A", "Grant-B", "Grant-C"] }
```

---

### **POST /upload**
Batch ingest Excel files and run validations.

**Request:**
```
multipart/form-data:
  - files: (file) ← multiple .xlsx files
  - manifest: (text/json) ← JSON array of {filename, grant_name, year}
```

**Manifest example:**
```json
[
  {"filename": "budget.xlsx", "grant_name": "Grant-A", "year": 2024},
  {"filename": "income.xlsx", "grant_name": "Grant-B", "year": 2024}
]
```

**Response:**
```json
{
  "session_id": "abc123def456...",
  "preview": {
    "budget": [{staging_id, source_filename, sheet_name, grant_name, year, mapped_data, issues, suggested_target_table, mapping_confidence}, ...],
    "income": [...],
    "_unmapped": [...]
  }
}
```

---

### **GET /staging/pending**
Fetch all pending rows for a session (or all sessions).

**Query Parameters:**
- `session_id` (optional): Filter to one session; omit to get all pending rows

**Response:**
```json
{
  "rows": [
    {staging_id, source_filename, sheet_name, grant_name, year, mapped_data, issues, suggested_target_table, mapping_confidence},
    ...
  ]
}
```

---

### **POST /review**
Apply accept/reject/edit decisions to pending rows.

**Request (JSON Body):**
```json
{
  "decisions": [
    {"staging_id": 1, "action": "accept"},
    {"staging_id": 2, "action": "reject"},
    {"staging_id": 3, "action": "edit", "target_table": "budget", "edited_data": {"budget_code": "NEW-CODE"}},
    {"staging_id": 4, "action": "accept", "target_table": "income"}
  ]
}
```

**Response:**
```json
{
  "results": [
    {"staging_id": 1, "outcome": "committed"},
    {"staging_id": 2, "outcome": "rejected"},
    {"staging_id": 3, "outcome": "committed"},
    {"staging_id": 4, "outcome": "already_processed", "detail": "..."}
  ]
}
```

---

### **GET /session/{session_id}/pending-count**
Get count of pending rows in a session.

**Response:**
```json
{"session_id": "abc123...", "pending_count": 42}
```

---

### **GET /summary/{session_id}**
Compute post-upload summary (Excel counts vs. DB counts).

**Query Parameters:**
- `mode` (optional, default="per_grant"): `per_grant` or `combined`

**Response:**
```json
{
  "session_id": "abc123...",
  "mode": "per_grant",
  "summary": [
    {
      "grant_name": "Grant-A",
      "year": 2024,
      "table": "budget",
      "excel_row_count": 50,
      "db_row_count": 48,
      "rejected_count": 2,
      "duplicate_skipped_count": 0,
      "still_pending_count": 0
    },
    ...
  ]
}
```

---

### **GET /summary/{session_id}/export**
Export summary as XLSX, CSV, or PDF.

**Query Parameters:**
- `format` (required): `xlsx`, `csv`, or `pdf`
- `mode` (optional, default="per_grant"): `per_grant` or `combined`

**Response:**
- Binary file with appropriate media type and `Content-Disposition: attachment` header

---

### **GET /final/{table_name}/count**
Get row count in a final table.

**Path Parameters:**
- `table_name`: One of the 8 table names (e.g., "budget", "income")

**Response:**
```json
{"table": "budget", "row_count": 1250}
```

---

## 🔍 Key Features Deep Dive

### 1. Duplicate Detection

Duplicates are checked at **two levels** by comparing **ALL columns** (not just the unique key):

#### In-Batch Duplicates
When processing rows from the same upload session, the system compares each row against all previously seen rows in the batch. A row is flagged as duplicate **only if every column matches**:
```
issues.duplicate = "duplicate row within this upload batch"
```

#### Database Duplicates
For each row, the system queries the final table and compares against existing rows. A row is flagged as duplicate **only if all columns are identical**:
```
issues.duplicate = "a matching record already exists in the database"
```

#### Formatting-Aware Comparison
The duplicate detection ignores formatting variations:
- **Case-insensitive**: "John Smith" = "john smith" = "JOHN SMITH"
- **Numeric normalization**: "100" = 100 = 100.0
- **Whitespace**: Leading/trailing spaces are ignored
- **Empty values**: None and empty strings are treated as equivalent

**Example:**
- Two rows with identical `(grant_id, year, reference, date, debit, credit)` but different `account_description` → **NOT flagged as duplicate** (account_description differs)
- Two rows with ALL columns identical, including `account_description` → **Flagged as duplicate**

**Note on Unique Keys:**
Unique keys (defined per table in `table_config.py`) are still used for schema design and efficient indexing, but are **no longer used for duplicate detection**. The system now does complete row comparison:
- **budget**: `(grant_id, year, program, budget_code, activity)`
- **income**: `(grant_id, year, reference, date, debit, credit)`
- **expenditure**: `(grant_id, year, reference, date, debit, credit)`
- **liquidation**: `(grant_id, year, customer_id, trans_no, date)`
- **ageing**: `(grant_id, year, customer_id, invoice_number)`
- **customer_list**: `(grant_id, year, customer_id)`
- **job_list**: `(grant_id, year, job_id)`
- **trial_balance**: `(grant_id, year, account_id)`

### 2. Field Mapping (Fuzzy Matching)

Column headers in your Excel files rarely match the database schema exactly. The system uses:

1. **Synonym Library** (`table_config.py` → `FIELD_SYNONYMS`)
   - Maps standard field names to common aliases
   - E.g., `amount_usd` ← `["amount usd", "amount dollar", "amount $"]`

2. **Best-Match Algorithm** (`matching.py` → `best_field_for_header()`)
   - Fuzzy string matching (Levenshtein distance) if not in synonym list
   - Case-insensitive, ignores punctuation
   - Returns (field_name, confidence 0–1)

3. **Automatic Application**
   - Extracts value from your column
   - Applies field-specific transformation (e.g., normalize dates)
   - Stores in `mapped_data` alongside original value

If a header can't be matched, the column is ignored (no error).

### 3. Validation & Flagging Rules

**Mandatory Fields** (must not be null):
- Flagged if missing; requires manual entry or row rejection
- Example: `budget_code` in the budget table

**Optional Fields** (can be null):
- No flag; left empty in database

**Numeric Fields with Silent Defaults**:
- If blank/null, auto-filled with `0` (not flagged)
- Example: `amount_etb`, `debit`, `credit`
- Rationale: These fields represent quantities where "no value" = "zero"

**Date Fields**:
- Parsed using `dateutil.parser` with heuristic day-first ordering
- Reformatted to ISO (YYYY-MM-DD) for database
- Display format: DD/MM/YYYY
- Flagged if reformatted AND original didn't match expected format

**Country Fields**:
- Validated against ISO 3166-1 (pycountry library)
- Common aliases handled (e.g., "USA" → "United States")
- Flagged if standardized to a different name

**Total/Subtotal Rows**:
- Pattern detected by keywords: "Total", "Subtotal", "Grand Total" in first column
- Flagged for manual review (typically rejected)

### 4. Transaction Safety & Idempotency

**During Commit:**
- Review decisions are processed row-by-row in a single database transaction
- If any insert fails, the entire transaction rolls back

**Idempotency Guard:**
- If a staging row is already finalized (`status="committed"`, `"rejected"`, or `"duplicate_skipped"`) and a duplicate decision arrives:
  - The decision is ignored
  - Response: `"outcome": "already_processed"`
  - Protects against double-submission, browser refresh, network retry

### 5. Summary Reporting

**Per-Grant Summary:**
- One row per table per grant per year
- Counts: parsed from Excel, committed to DB, rejected, duplicates skipped
- Comparison totals (income debit/credit): sum in Excel vs. sum in database

**Combined Summary:**
- Aggregated across all grants per year per table
- Useful for board-level reporting

**Export Formats:**
- **XLSX**: OpenPyXL → formatted spreadsheet with headers
- **CSV**: Comma-separated, UTF-8 encoded
- **PDF**: ReportLab → print-friendly layout with title, date, totals

---

## 🚨 Troubleshooting

### Backend won't start: `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
cd backend
venv\Scripts\activate     # Windows
source venv/bin/activate # macOS/Linux
pip install -r requirements.txt
```

---

### Database connection error: `psycopg2.OperationalError`

**Check:**
1. PostgreSQL is running: `psql -U postgres -d [database_name]`
2. `.env` has correct credentials:
   ```
   DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DB
   ```
3. Special characters in password are URL-encoded:
   - `@` → `%40`
   - `:` → `%3A`
   - `#` → `%23`

**Test:**
```python
python -c "from app.database.connection import engine; print(engine.execute('SELECT 1').scalar())"
```

---

### Tables don't exist: `psycopg2.ProgrammingError: relation "budget" does not exist`

**Solution:**
```bash
python -m app.database.create_tables
```

Verify output:
```
✅ staging_uploads + all 8 final tables created/verified successfully.
```

---

### Frontend can't reach backend: Network error in browser console

**Check:**
1. Backend running on `http://localhost:8000/docs`?
2. `.env` in frontend folder has correct API URL:
   ```
   VITE_API_BASE=http://localhost:8000/api
   ```
3. No CORS errors? Backend should log:
   ```
   cors_origins = "http://localhost:5173"
   ```

---

### Upload succeeds but review page shows "No rows"

**Possible causes:**
1. All files were mapped to unmapped: check preview in console
2. Session ID was lost (browser refresh): clear localStorage, re-upload
3. Backend crashed during staging insert: check backend logs, restart

---

### Export button doesn't work

**Check:**
1. At least one row is committed (`db_row_count > 0`)
2. Backend is still running (test `/api/tables` in browser)
3. Browser console for error messages

---

### Date formatting looks wrong

The system uses DD/MM/YYYY for display (Safe Minds standard). If your Excel uses MM/DD/YYYY:

**Workaround:**
- Pre-convert Excel dates to DD/MM/YYYY before upload
- Or edit rows in the review step

---

## 📝 Development Notes

### Running Migrations

To safely reset & recreate the schema (dev only):

```bash
python -m app.database.reset_schema
```

⚠️ **WARNING**: This **deletes all data**. Use only in development.

### Clearing Data Only

To keep tables but remove all rows:

```bash
python -m app.database.clear_data
```

### Adding a New Field to a Table

1. Edit `backend/app/services/table_config.py` → `FINAL_TABLES[table_name]["columns"]`
2. Add synonyms to `FIELD_SYNONYMS` if applicable
3. Run `python -m app.database.reset_schema` (dev) or write a migration script (prod)
4. Add validation logic to `backend/app/services/row_processor.py` if needed

---

## 📚 Dependencies Summary

### Backend
- **FastAPI** (0.115): Web framework
- **Uvicorn** (0.30): ASGI server
- **SQLAlchemy** (2.0): ORM
- **psycopg2** (2.9): PostgreSQL driver
- **Pandas** (2.2): Data frame operations
- **openpyxl** (3.1): Excel parsing
- **pydantic** (2.9): Request validation
- **python-dateutil** (2.9): Date parsing
- **pycountry** (24.6): Country validation
- **reportlab** (4.4): PDF generation

### Frontend
- **React** (18.3): UI framework
- **Vite** (5.4): Build tool & dev server
- **Fetch API**: HTTP (no axios/jQuery)

---

## 🎓 Example Workflow

```bash
# Terminal 1: Backend
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Browser
# 1. Navigate to http://localhost:5173
# 2. Click "Choose Folder"
# 3. Select ~/MyGrants/
# 4. Uncheck files you don't want
# 5. Click "Upload"
# 6. Wait 2–5 seconds for processing
# 7. Review: Accept clean rows, edit flagged ones, reject duplicates
# 8. Click "Submit All Decisions"
# 9. View summary or export as XLSX/CSV/PDF
```

---

## ✉️ Support

- **Database errors**: Check `.env` connection string and PostgreSQL logs
- **File format errors**: Ensure Excel files are `.xlsx` (not `.xls`, `.csv`, etc.)
- **Field mapping**: Add synonyms to `table_config.py` if your column names are unique
- **Performance**: For uploads >1000 rows, consider splitting into smaller batches

---

**Last Updated:** 2025-01-21  
**Version:** 1.0.0  
**Status:** Production-Ready
