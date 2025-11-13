# TN Electoral Search

A modern web application for searching Tamil Nadu electoral roll data from SIR 2002 (Supplementary Image Roll).

## Features

- **Fast Search**: FTS5-powered full-text search with caching
- **PDF Import**: Extract voter data from scanned electoral roll PDFs
- **Smart UI**: Context-aware messaging and guided data import
- **Multiple Search Types**: Fuzzy search, exact match, voter ID, and prefix search
- **Location Filtering**: Search by district, constituency, and polling station

## Quick Start

### Prerequisites

- Python 3.8+
- SQLite 3.35+ (for FTS5 support)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/[username]/tn-electoral-search.git
cd tn-electoral-search
```

2. Quick setup with Make:
```bash
make install    # Create venv and install dependencies
make init-db    # Initialize database with schema and sample data
make dev        # Run development server
```

Or manual setup:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt          # Core dependencies (search only)
# OR for full functionality including PDF import:
# pip install -r requirements-full.txt

# Verify setup
python scripts/verify_setup.py

# Initialize database with sample data
python scripts/init_db.py

# Run development server
python scripts/dev_server.py
```

3. Open http://localhost:8000 in your browser

### Sample Data

The database is automatically populated with Tamil Nadu electoral location data including:
- 29 districts
- 197 constituencies  
- 38,397+ polling stations

To repopulate just the location data (preserving any imported voter data):
```bash
make populate-data
# or
python scripts/populate_data.py
```

### PDF Import Feature

To use the PDF import functionality, install full dependencies:
```bash
pip install -r requirements-full.txt
```

This includes:
- Google Gemini AI API for high-accuracy extraction
- PDF processing libraries (PyMuPDF, pdf2image, Pillow)
- Additional data processing tools

Without these dependencies, the core search functionality works perfectly, but PDF import will show an error message with installation instructions.

## Project Structure

```
tn-electoral-search/
├── app/                    # Core application
│   ├── __init__.py
│   ├── main.py            # FastAPI application
│   ├── database.py        # Database operations
│   ├── search_service.py  # Search logic
│   ├── pdf_service.py     # PDF import service
│   └── extractors/        # PDF extraction modules
├── config/                # Configuration files
│   └── schema.sql         # Database schema
├── database/              # Database files (gitignored)
├── scripts/               # Utility scripts
├── tests/                 # Test files
├── docs/                  # Documentation
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## API Documentation

Once running, visit:
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions, please use the GitHub issue tracker.