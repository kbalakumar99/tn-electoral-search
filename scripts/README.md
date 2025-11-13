# Scripts Directory

Utility scripts for managing the TN Electoral Search application.

## Available Scripts

### `init_db.py`
Initialize the database with schema and populate with default electoral location data.

**Usage:**
```bash
python scripts/init_db.py
```

**What it does:**
- Creates database schema (districts, constituencies, polling_stations, voters tables)
- Populates with Tamil Nadu electoral location data from `config/electoral_rolls_complete.json`
- Sets up FTS5 search indexes
- Provides summary statistics

**Output:**
- 29 districts
- 197 constituencies
- 38,397+ polling stations
- Ready-to-use database for searching

### `populate_data.py`
Populate database with electoral location data only (preserves existing voter data).

**Usage:**
```bash
python scripts/populate_data.py
```

**What it does:**
- Loads electoral location data from JSON
- Clears existing location data but preserves any imported voter data
- Repopulates districts, constituencies, and polling stations
- Interactive confirmation if voter data exists

### `dev_server.py`
Run development server with auto-reload.

**Usage:**
```bash
python scripts/dev_server.py
```

**Features:**
- Auto-reload on code changes
- Development-friendly logging
- Watches the `app/` directory for changes

### `run_server.py`
Run production server.

**Usage:**
```bash
python scripts/run_server.py
```

**Features:**
- Production-optimized settings  
- No auto-reload
- Suitable for deployment

### `verify_setup.py`
Verify that the application setup is correct.

**Usage:**
```bash
python scripts/verify_setup.py
```

**Checks:**
- Required dependencies installed
- Module imports working
- Database configuration correct
- Schema file exists

## Quick Start Workflow

1. **First Time Setup:**
```bash
python scripts/verify_setup.py  # Verify everything is ready
python scripts/init_db.py       # Initialize database with data
python scripts/dev_server.py    # Start development server
```

2. **Reset Location Data:**
```bash
python scripts/populate_data.py  # Repopulate just location data
```

3. **Development:**
```bash
python scripts/dev_server.py     # Auto-reload development server
```

4. **Production:**
```bash
python scripts/run_server.py     # Production server
```

## Data Sources

- **Electoral Data:** `config/electoral_rolls_complete.json`
  - Contains Tamil Nadu districts, constituencies, and polling stations
  - Structured as: district → constituency → parts (polling stations)
  - Used by both `init_db.py` and `populate_data.py`