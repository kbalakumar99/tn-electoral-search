# API Documentation

## Overview

The TN Electoral Search API provides endpoints for searching electoral data and importing PDF files.

## Base URL

```
http://localhost:8000
```

## Endpoints

### Search Endpoints

#### GET `/api/search`
Search for voters with various filters and search types.

**Parameters:**
- `query` (string): Search query (* for all entries)
- `search_type` (string): fuzzy, exact, voter_id, prefix (default: fuzzy)
- `district` (string, optional): Filter by district
- `constituency` (string, optional): Filter by constituency  
- `polling_station` (string, optional): Filter by polling station
- `limit` (integer): Results per page (1-500, default: 50)
- `offset` (integer): Pagination offset (default: 0)

**Example:**
```bash
curl "http://localhost:8000/api/search?query=ram&district=Tiruchirappalli&constituency=Tiruveumbur&limit=10"
```

#### GET `/api/check-data`
Check if voter data exists for given location filters.

**Parameters:**
- `district` (string, optional): District name
- `constituency` (string, optional): Constituency name
- `polling_station` (string, optional): Polling station name

**Response:**
```json
{
  "exists": true,
  "count": 87,
  "district": "Tiruchirappalli",
  "constituency": "Tiruveumbur",
  "polling_station": null
}
```

#### GET `/api/locations`
Get all available districts, constituencies, and polling stations.

**Response:**
```json
{
  "districts": [...],
  "constituencies": [...], 
  "polling_stations": [...]
}
```

### Import Endpoints

#### POST `/api/import/identify`
Upload PDF and get basic information.

**Form Data:**
- `file`: PDF file

#### POST `/api/import/start`
Start PDF extraction process.

**Form Data:**
- `temp_file_path`: Temporary file path from identify
- `district`: District name
- `constituency`: Constituency name
- `polling_station`: Polling station name
- `station_number`: Part number (optional)
- `extraction_method`: gemini or tesseract

#### GET `/api/import/status/{import_id}`
Get status of import job.

### Utility Endpoints

#### GET `/api/health`
Health check endpoint.

#### GET `/api/stats`
Get database statistics.

#### POST `/api/cache/clear`
Clear search cache.

## Error Handling

All endpoints return appropriate HTTP status codes:
- 200: Success
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

Error responses include a detail message:
```json
{
  "detail": "Error description"
}
```