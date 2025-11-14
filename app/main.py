"""
FastAPI application for electoral data search.
Blazingly fast search with FTS5, caching, and async operations.
"""
from fastapi import FastAPI, Query, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional
from pydantic import BaseModel, Field
from database import db
from search_service import search_service
from pdf_service import pdf_import_service
import time
import tempfile
import os
import uuid


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    print("🚀 Initializing electoral search system...")
    await db.initialize()
    print("✓ Database initialized")

    stats = await db.get_stats()
    print(f"📊 Database contains:")
    print(f"   - {stats['districts']} districts")
    print(f"   - {stats['constituencies']} constituencies")
    print(f"   - {stats['polling_stations']} polling stations")
    print(f"   - {stats['voters']} voters")
    print(f"   - Database size: {stats['db_size_mb']} MB")

    print("\n🔥 Server ready! Search is blazingly fast!")
    print("📍 API Docs: http://localhost:8000/docs")
    print("🌐 Web UI: http://localhost:8000/\n")

    yield

    print("\n👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="TN - SIR 2002 - Electoral Search API",
    description="Tamil Nadu electoral data search system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    search_type: str = Field(default="fuzzy", description="Search type: fuzzy, exact, voter_id, prefix")
    district: Optional[str] = Field(None, description="Filter by district")
    constituency: Optional[str] = Field(None, description="Filter by constituency")
    polling_station: Optional[str] = Field(None, description="Filter by polling station")
    limit: int = Field(default=50, ge=1, le=500, description="Results per page")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class HealthResponse(BaseModel):
    status: str
    timestamp: float
    database: dict


# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TN - SIR 2002 - Electoral Search</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', sans-serif;
                background: #f5f5f7;
                min-height: 100vh;
                padding: 20px;
                color: #1d1d1f;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
            }

            .header {
                text-align: center;
                margin-bottom: 48px;
                padding-top: 40px;
            }

            .header h1 {
                font-size: 56px;
                font-weight: 600;
                letter-spacing: -0.03em;
                color: #1d1d1f;
                margin-bottom: 8px;
                line-height: 1.07;
            }

            .header p {
                font-size: 21px;
                line-height: 1.38;
                font-weight: 400;
                letter-spacing: 0.012em;
                color: #6e6e73;
            }
            .search-box {
                background: white;
                border-radius: 18px;
                padding: 32px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
                margin-bottom: 24px;
                border: 1px solid rgba(0, 0, 0, 0.04);
            }

            .search-input-group {
                display: flex;
                gap: 12px;
                margin-bottom: 16px;
            }

            input, select, button {
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
                font-size: 17px;
                padding: 12px 16px;
                border-radius: 10px;
                border: 1px solid #d2d2d7;
                outline: none;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                background: white;
            }

            input:focus, select:focus {
                border-color: #0071e3;
                box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.1);
            }

            #searchInput {
                flex: 1;
                font-size: 17px;
            }

            #searchInput::placeholder {
                color: #86868b;
            }

            #searchType {
                width: 160px;
                cursor: pointer;
            }

            select:disabled {
                background: #f5f5f7;
                color: #86868b;
                cursor: not-allowed;
                border-color: #e5e5ea;
            }

            button {
                background: #0071e3;
                color: white;
                border: none;
                cursor: pointer;
                font-weight: 500;
                padding: 12px 24px;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            }

            button:hover:not(:disabled) {
                background: #0077ed;
                transform: scale(1.02);
            }

            button:active:not(:disabled) {
                transform: scale(0.98);
            }

            button:disabled {
                background: #d2d2d7;
                color: #86868b;
                cursor: not-allowed;
                opacity: 0.6;
            }

            .filters {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 12px;
            }
            .results-container {
                background: white;
                border-radius: 18px;
                padding: 32px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
                border: 1px solid rgba(0, 0, 0, 0.04);
            }

            .stats {
                display: flex;
                justify-content: space-around;
                margin-bottom: 24px;
                padding: 20px;
                background: #f5f5f7;
                border-radius: 12px;
                gap: 16px;
            }

            .stat-item {
                text-align: center;
                flex: 1;
            }

            .stat-value {
                font-size: 32px;
                font-weight: 600;
                color: #1d1d1f;
                margin-bottom: 4px;
                letter-spacing: -0.02em;
            }

            .stat-label {
                font-size: 14px;
                color: #6e6e73;
                font-weight: 400;
                letter-spacing: 0.01em;
            }
            .results-table {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                margin-top: 20px;
            }

            .results-table th {
                background: #f5f5f7;
                color: #1d1d1f;
                padding: 14px 16px;
                text-align: left;
                font-weight: 600;
                font-size: 14px;
                letter-spacing: 0.01em;
                border-bottom: 1px solid #d2d2d7;
            }

            .results-table th:first-child {
                border-top-left-radius: 10px;
            }

            .results-table th:last-child {
                border-top-right-radius: 10px;
            }

            .results-table td {
                padding: 14px 16px;
                border-bottom: 1px solid #f5f5f7;
                font-size: 15px;
                color: #1d1d1f;
            }

            .results-table tr:hover {
                background: #fbfbfb;
            }

            .results-table tr:last-child td {
                border-bottom: none;
            }

            .pagination {
                display: flex;
                justify-content: center;
                gap: 12px;
                margin-top: 24px;
            }

            .pagination button {
                padding: 10px 20px;
                border-radius: 10px;
            }

            .loading {
                text-align: center;
                padding: 60px 20px;
                color: #6e6e73;
                font-size: 17px;
            }

            .no-results {
                text-align: center;
                padding: 60px 20px;
                color: #86868b;
                font-size: 17px;
            }

            .badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.02em;
                text-transform: uppercase;
                margin-left: 6px;
            }

            .badge-cache {
                background: #34c759;
                color: white;
            }

            .badge-search {
                background: #0071e3;
                color: white;
            }

            /* Import Button */
            .import-btn {
                position: fixed;
                bottom: 30px;
                right: 30px;
                background: #34c759;
                color: white;
                border: none;
                border-radius: 50px;
                padding: 16px 28px;
                font-size: 16px;
                font-weight: 600;
                box-shadow: 0 8px 24px rgba(52, 199, 89, 0.3);
                cursor: pointer;
                z-index: 999;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .import-btn:hover {
                background: #30b350;
                transform: translateY(-2px);
                box-shadow: 0 12px 32px rgba(52, 199, 89, 0.4);
            }

            /* Slider Panel */
            .slider-panel {
                position: fixed;
                top: 0;
                right: -500px;
                width: 500px;
                height: 100vh;
                background: white;
                box-shadow: -4px 0 24px rgba(0, 0, 0, 0.2);
                z-index: 1000;
                transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                overflow-y: auto;
            }

            .slider-panel.open {
                right: 0;
            }

            .slider-panel.minimized {
                right: -450px;
            }

            .slider-header {
                background: linear-gradient(135deg, #34c759, #30b350);
                color: white;
                padding: 24px;
                position: sticky;
                top: 0;
                z-index: 1;
            }

            .slider-header h2 {
                font-size: 24px;
                font-weight: 600;
                margin-bottom: 4px;
            }

            .slider-header p {
                font-size: 14px;
                opacity: 0.9;
            }

            .close-btn, .toggle-btn {
                position: absolute;
                top: 20px;
                background: rgba(255, 255, 255, 0.2);
                border: none;
                color: white;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                font-size: 20px;
                cursor: pointer;
                transition: background 0.2s;
                padding: 2px;
            }

            .close-btn {
                right: 20px;
            }

            .toggle-btn {
                right: 60px;
                font-size: 16px;
            }

            .close-btn:hover, .toggle-btn:hover {
                background: rgba(255, 255, 255, 0.3);
            }

            .slider-content {
                padding: 24px;
            }

            .form-group {
                margin-bottom: 20px;
            }

            .form-group label {
                display: block;
                font-size: 14px;
                font-weight: 600;
                color: #1d1d1f;
                margin-bottom: 8px;
            }

            .form-group input[type="file"] {
                width: 100%;
                padding: 12px;
                border: 2px dashed #d2d2d7;
                border-radius: 10px;
                cursor: pointer;
                background: #f5f5f7;
            }

            .metadata-display {
                background: #f5f5f7;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 20px;
            }

            .metadata-item {
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #e5e5ea;
            }

            .metadata-item:last-child {
                border-bottom: none;
            }

            .metadata-label {
                font-weight: 600;
                color: #6e6e73;
                font-size: 14px;
            }

            .metadata-value {
                color: #1d1d1f;
                font-weight: 500;
                font-size: 14px;
            }

            .progress-container {
                margin: 20px 0;
            }

            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e5e5ea;
                border-radius: 4px;
                overflow: hidden;
            }

            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #34c759, #30b350);
                transition: width 0.3s ease;
                width: 0%;
            }

            .progress-text {
                text-align: center;
                margin-top: 8px;
                font-size: 14px;
                color: #6e6e73;
            }

            .success-message {
                background: #d1f4e0;
                color: #1d8348;
                padding: 16px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
                font-weight: 600;
            }

            .error-message {
                background: #ffebee;
                color: #c62828;
                padding: 16px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
                font-weight: 600;
            }

            .btn-secondary {
                background: #6e6e73;
            }

            .btn-secondary:hover {
                background: #5a5a5f;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>TN - SIR 2002 - Electoral Search</h1>
                <p>Search voter data from electoral rolls.</p>
            </div>

            <div class="search-box">
                <div class="filters" style="margin-bottom: 16px;">
                    <select id="district" required>
                        <option value="">Select District *</option>
                    </select>
                    <select id="constituency" required disabled>
                        <option value="">Select Constituency *</option>
                    </select>
                    <select id="pollingStation">
                        <option value="">All Polling Stations</option>
                    </select>
                </div>

                <div class="search-input-group">
                    <input type="text" id="searchInput" placeholder="Search by name, voter ID, or serial number..." />
                    <select id="searchType">
                        <option value="fuzzy">Fuzzy Search</option>
                        <option value="exact">Exact Match</option>
                        <option value="voter_id">Voter ID</option>
                        <option value="prefix">Prefix</option>
                    </select>
                    <button onclick="search()" id="searchBtn" disabled>Search</button>
                </div>
            </div>

            <div class="results-container" id="resultsContainer" style="display: none;">
                <div class="stats" id="stats"></div>
                <div id="results"></div>
                <div class="pagination" id="pagination"></div>
            </div>
        </div>

        <!-- Import Button -->
        <button class="import-btn" onclick="openImportPanel()">📄 Import PDF</button>

        <!-- Slider Panel -->
        <div class="slider-panel" id="importPanel">
            <div class="slider-header">
                <button class="toggle-btn" onclick="toggleMinimize()" title="Minimize/Maximize">◀</button>
                <button class="close-btn" onclick="closeImportPanel()" title="Close">×</button>
                <h2>Import Voter List PDF</h2>
                <p>Extract data from scanned PDFs</p>
            </div>
            <div class="slider-content">
                <!-- Step 1: Upload & Enter Details -->
                <div id="uploadStep">
                    <div class="form-group">
                        <label>Select PDF File *</label>
                        <input type="file" id="pdfFile" accept=".pdf" onchange="handleFileUpload()" />
                    </div>
                    
                    <div id="pdfInfoSection" style="display: none;">
                        <div class="metadata-display" id="pdfInfo"></div>
                        
                        <h3 style="margin: 20px 0 16px 0;">Enter Details</h3>
                        
                        <div class="form-group">
                            <label>District *</label>
                            <select id="districtInput" required style="width: 100%;">
                                <option value="">-- Select District --</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label>Constituency *</label>
                            <select id="constituencyInput" required style="width: 100%;" disabled>
                                <option value="">-- Select Constituency --</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label>Polling Station (Part) *</label>
                            <select id="pollingStationInput" required style="width: 100%;" disabled>
                                <option value="">-- Select Polling Station --</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label>Part Number</label>
                            <input type="text" id="stationNumberInput" placeholder="Auto-filled" readonly style="background: #f5f5f7;" />
                        </div>
                        
                        <div class="form-group" id="apiKeyGroup">
                            <label>Gemini API Key * <span style="font-size: 12px; font-weight: normal; color: #6e6e73;">(session-only, not stored)</span></label>
                            <input type="password" id="geminiApiKey" placeholder="Enter your Gemini API key" style="width: 100%;" />
                            <div style="font-size: 11px; color: #6e6e73; margin-top: 6px; line-height: 1.4;">
                                🔒 Your API key is stored only in your browser session and is never saved to our servers.<br>
                                Get a free key: <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: #0071e3;">Google AI Studio</a>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label>Extraction Method *</label>
                            <select id="extractionMethod" style="width: 100%;" onchange="handleExtractionMethodChange()">
                                <option value="gemini">AI-Powered (High Accuracy, Slower)</option>
                                <option value="tesseract">OCR-Based (Faster, Standard Accuracy)</option>
                            </select>
                            <div style="font-size: 12px; color: #6e6e73; margin-top: 4px;">
                                <strong>AI-Powered:</strong> ~3-5 sec/page, 95% accuracy<br>
                                <strong>OCR-Based:</strong> ~1-2 sec/page, 75% accuracy
                            </div>
                        </div>
                        
                        <button onclick="startExtraction()" style="width: 100%; margin-top: 10px;">
                            Start Extraction
                        </button>
                        <button onclick="cancelImport()" class="btn-secondary" style="width: 100%; margin-top: 10px;">
                            Cancel
                        </button>
                    </div>
                </div>

                <!-- Step 2: Loading (removed metadata identification) -->

                <!-- Step 3: Extraction Progress -->
                <div id="progressStep" style="display: none;">
                    <h3 style="margin-bottom: 16px;">Extracting Data...</h3>
                    
                    <div class="progress-container">
                        <div class="progress-bar">
                            <div class="progress-fill" id="progressFill"></div>
                        </div>
                        <div class="progress-text" id="progressText">0%</div>
                    </div>
                    
                    <div id="progressDetails" style="margin-top: 20px; font-size: 14px; color: #6e6e73;">
                        <p>Status: <span id="statusText">Starting...</span></p>
                        <p>Page: <span id="pageText">-</span></p>
                        <p>Voters Extracted: <span id="votersText">0</span></p>
                    </div>
                </div>

                <div id="completeStep" style="display: none;">
                    <div class="success-message">
                        ✓ Import Completed Successfully!
                    </div>
                    <div id="completeSummary" style="margin: 20px 0; font-size: 14px;"></div>
                    <button onclick="minimizeAndContinue()" style="width: 100%; margin-bottom: 10px;">
                        Minimize & Search Now
                    </button>
                    <button onclick="refreshPage()" class="btn-secondary" style="width: 100%;">
                        Refresh Page
                    </button>
                </div>

                <!-- Error Display -->
                <div id="errorStep" style="display: none;">
                    <div class="error-message" id="errorMessage"></div>
                    <button onclick="resetImport()" style="width: 100%;">
                        Try Again
                    </button>
                </div>
            </div>
        </div>

        <script>
            let currentOffset = 0;
            const limit = 50;
            let locationsData = null;

            // Load locations on page load
            async function loadLocations() {
                try {
                    const response = await fetch('/api/locations');
                    locationsData = await response.json();

                    // Populate districts
                    const districtSelect = document.getElementById('district');
                    locationsData.districts.forEach(district => {
                        const option = document.createElement('option');
                        option.value = district.name;
                        option.textContent = district.name;
                        districtSelect.appendChild(option);
                    });
                } catch (error) {
                    console.error('Error loading locations:', error);
                }
            }

            // Handle district change
            document.getElementById('district').addEventListener('change', function() {
                const district = this.value;
                const constituencySelect = document.getElementById('constituency');
                const pollingStationSelect = document.getElementById('pollingStation');
                const searchBtn = document.getElementById('searchBtn');

                // Reset constituency and polling station
                constituencySelect.innerHTML = '<option value="">Select Constituency *</option>';
                pollingStationSelect.innerHTML = '<option value="">All Polling Stations</option>';
                constituencySelect.disabled = !district;
                pollingStationSelect.disabled = true;
                searchBtn.disabled = true;

                if (district && locationsData) {
                    // Populate constituencies for selected district
                    const constituencies = locationsData.constituencies.filter(c => c.district_name === district);
                    constituencies.forEach(constituency => {
                        const option = document.createElement('option');
                        option.value = constituency.name;
                        option.textContent = constituency.name;
                        constituencySelect.appendChild(option);
                    });
                }
            });

            // Handle constituency change
            document.getElementById('constituency').addEventListener('change', function() {
                const constituency = this.value;
                const district = document.getElementById('district').value;
                const pollingStationSelect = document.getElementById('pollingStation');
                const searchBtn = document.getElementById('searchBtn');

                // Reset polling station
                pollingStationSelect.innerHTML = '<option value="">All Polling Stations</option>';
                pollingStationSelect.disabled = !constituency;

                // Enable search button if both district and constituency are selected
                searchBtn.disabled = !(district && constituency);

                if (constituency && locationsData) {
                    // Populate polling stations for selected constituency
                    const pollingStations = locationsData.polling_stations.filter(
                        ps => ps.constituency_name === constituency && ps.district_name === district
                    );
                    
                    // Sort by station_number (numeric sort)
                    pollingStations.sort((a, b) => {
                        const numA = parseInt(a.station_number) || 0;
                        const numB = parseInt(b.station_number) || 0;
                        return numA - numB;
                    });
                    
                    pollingStations.forEach(station => {
                        const option = document.createElement('option');
                        option.value = station.name;
                        // Display format: "227 - Station Name"
                        option.textContent = station.station_number 
                            ? `${station.station_number} - ${station.name}` 
                            : station.name;
                        pollingStationSelect.appendChild(option);
                    });
                }
            });

            async function search(offset = 0) {
                const query = document.getElementById('searchInput').value.trim();
                const district = document.getElementById('district').value;
                const constituency = document.getElementById('constituency').value;

                // Validate required fields
                if (!district || !constituency) {
                    alert('Please select both District and Constituency');
                    return;
                }

                // Allow empty query - will return all entries
                currentOffset = offset;

                const searchType = document.getElementById('searchType').value;
                const pollingStation = document.getElementById('pollingStation').value;

                document.getElementById('resultsContainer').style.display = 'block';
                
                if (query) {
                    document.getElementById('results').innerHTML = '<div class="loading">🔍 Searching...</div>';
                } else {
                    document.getElementById('results').innerHTML = '<div class="loading">📋 Loading all entries...</div>';
                }

                try {
                    // First check if data exists for selected location
                    const checkParams = new URLSearchParams({
                        district,
                        constituency
                    });
                    if (pollingStation) checkParams.append('polling_station', pollingStation);

                    const checkResponse = await fetch(`/api/check-data?${checkParams}`);
                    const dataCheck = await checkResponse.json();

                    // If no data exists for the selected location, show alert
                    if (!dataCheck.exists) {
                        const locationStr = pollingStation 
                            ? `${district} → ${constituency} → ${pollingStation}`
                            : `${district} → ${constituency}`;
                        
                        document.getElementById('results').innerHTML = `
                            <div class="no-results">
                                <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
                                <div style="font-size: 20px; font-weight: 600; color: #ff6b6b; margin-bottom: 12px;">
                                    No Data Found
                                </div>
                                <div style="font-size: 16px; color: #6e6e73; margin-bottom: 20px;">
                                    No voter data is available for:<br>
                                    <strong>${locationStr}</strong>
                                </div>
                                <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 10px; padding: 16px; margin-bottom: 20px; font-size: 14px; color: #856404;">
                                    <strong>💡 To add data:</strong><br>
                                    1. Click the "📄 Import PDF" button<br>
                                    2. Upload the electoral roll PDF for this location<br>
                                    3. Select the correct district and constituency<br>
                                    4. Start the extraction process
                                </div>
                                <button onclick="openImportPanel()" style="background: #34c759; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; cursor: pointer;">
                                    📄 Import Data Now
                                </button>
                            </div>
                        `;
                        document.getElementById('stats').innerHTML = `
                            <div class="stat-item">
                                <div class="stat-value">0</div>
                                <div class="stat-label">Total Results</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">-</div>
                                <div class="stat-label">Search Time</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">0</div>
                                <div class="stat-label">Showing</div>
                            </div>
                        `;
                        document.getElementById('pagination').innerHTML = '';
                        return;
                    }

                    // Proceed with normal search if data exists
                    const params = new URLSearchParams({
                        query: query || '*',  // Use '*' for all entries when query is empty
                        search_type: searchType,
                        district,
                        constituency,
                        limit,
                        offset
                    });

                    if (pollingStation) params.append('polling_station', pollingStation);

                    const response = await fetch(`/api/search?${params}`);
                    const data = await response.json();

                    displayResults(data);
                } catch (error) {
                    document.getElementById('results').innerHTML = `<div class="no-results">❌ Error: ${error.message}</div>`;
                }
            }

            // Load locations when page loads
            window.addEventListener('DOMContentLoaded', loadLocations);

            function displayResults(data) {
                // Display stats
                const cacheBadge = data.from_cache ? '<span class="badge badge-cache">FROM CACHE</span>' : '<span class="badge badge-search">LIVE SEARCH</span>';
                document.getElementById('stats').innerHTML = `
                    <div class="stat-item">
                        <div class="stat-value">${data.total_results}</div>
                        <div class="stat-label">Total Results</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${data.search_time_ms}ms</div>
                        <div class="stat-label">Search Time ${cacheBadge}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${data.returned_results}</div>
                        <div class="stat-label">Showing</div>
                    </div>
                `;

                // Display results
                if (data.results.length === 0) {
                    const query = document.getElementById('searchInput').value.trim();
                    if (query && query !== '*') {
                        // Search query didn't match anything, but data exists for the location
                        document.getElementById('results').innerHTML = `
                            <div class="no-results">
                                <div style="font-size: 48px; margin-bottom: 16px;">🔍</div>
                                <div style="font-size: 18px; font-weight: 600; margin-bottom: 12px;">
                                    No Results Found
                                </div>
                                <div style="font-size: 16px; color: #6e6e73; margin-bottom: 16px;">
                                    No matches found for "<strong>${query}</strong>"
                                </div>
                                <div style="font-size: 14px; color: #86868b;">
                                    Try searching with different keywords or use the "All Entries" option (leave search empty)
                                </div>
                            </div>
                        `;
                    } else {
                        // No entries at all for this location (shouldn't happen as we check data existence first)
                        document.getElementById('results').innerHTML = '<div class="no-results">No results found</div>';
                    }
                    document.getElementById('pagination').innerHTML = '';
                    return;
                }

                let html = '<table class="results-table"><thead><tr>';
                html += '<th>Serial</th><th>Voter Name</th><th>Age</th><th>Gender</th><th>Voter ID</th>';
                html += '<th>House No</th><th>Relative Name</th><th>Polling Station</th><th>Constituency</th></tr></thead><tbody>';

                data.results.forEach(voter => {
                    html += '<tr>';
                    html += `<td>${voter.serial_number || '-'}</td>`;
                    html += `<td><strong>${voter.voter_name || voter.voter_name_tamil || '-'}</strong></td>`;
                    html += `<td>${voter.age || '-'}</td>`;
                    html += `<td>${voter.gender || '-'}</td>`;
                    html += `<td>${voter.voter_id || '-'}</td>`;
                    html += `<td>${voter.house_no || '-'}</td>`;
                    html += `<td>${voter.relative_name || voter.relative_name_tamil || '-'}</td>`;
                    html += `<td>${voter.polling_station_name || '-'}</td>`;
                    html += `<td>${voter.constituency_name || '-'}</td>`;
                    html += '</tr>';
                });

                html += '</tbody></table>';
                document.getElementById('results').innerHTML = html;

                // Pagination
                displayPagination(data);
            }

            function displayPagination(data) {
                const paginationDiv = document.getElementById('pagination');
                let html = '';

                if (currentOffset > 0) {
                    html += `<button onclick="search(${currentOffset - limit})">← Previous</button>`;
                }

                const currentPage = Math.floor(currentOffset / limit) + 1;
                const totalPages = Math.ceil(data.total_results / limit);
                html += `<button disabled>Page ${currentPage} of ${totalPages}</button>`;

                if (data.has_more) {
                    html += `<button onclick="search(${currentOffset + limit})">Next →</button>`;
                }

                paginationDiv.innerHTML = html;
            }

            // Enter key to search
            document.getElementById('searchInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') search();
            });

            // === IMPORT FUNCTIONALITY ===
            let currentImportId = null;
            let currentTempFilePath = null;
            let importMetadata = null;
            let isMinimized = false;
            let electoralData = null; // Cache electoral data

            // Session storage for API key
            function getGeminiApiKey() {
                return sessionStorage.getItem('gemini_api_key');
            }

            function setGeminiApiKey(key) {
                sessionStorage.setItem('gemini_api_key', key);
            }

            function clearGeminiApiKey() {
                sessionStorage.removeItem('gemini_api_key');
            }

            // Handle extraction method change to show/hide API key field
            function handleExtractionMethodChange() {
                const method = document.getElementById('extractionMethod').value;
                const apiKeyGroup = document.getElementById('apiKeyGroup');
                
                if (method === 'gemini') {
                    apiKeyGroup.style.display = 'block';
                    // Load API key from session if available
                    const savedKey = getGeminiApiKey();
                    if (savedKey) {
                        document.getElementById('geminiApiKey').value = savedKey;
                    }
                } else {
                    apiKeyGroup.style.display = 'none';
                }
            }

            function openImportPanel() {
                const panel = document.getElementById('importPanel');
                panel.classList.add('open');
                panel.classList.remove('minimized');
                isMinimized = false;
                
                // Load electoral data if not already loaded
                if (!electoralData) {
                    loadElectoralData();
                }
                
                // Load saved API key if exists
                handleExtractionMethodChange();
            }

            async function loadElectoralData() {
                try {
                    const response = await fetch('/api/electoral-data');
                    electoralData = await response.json();
                    
                    // Populate district dropdown
                    const districtSelect = document.getElementById('districtInput');
                    districtSelect.innerHTML = '<option value="">-- Select District --</option>';
                    
                    electoralData.forEach(district => {
                        const option = document.createElement('option');
                        option.value = district.district;
                        option.textContent = district.district;
                        districtSelect.appendChild(option);
                    });
                    
                    console.log('✓ Electoral data loaded:', electoralData.length, 'districts');
                } catch (error) {
                    console.error('Failed to load electoral data:', error);
                    alert('Failed to load electoral data. Please refresh the page.');
                }
            }

            // Handle district selection
            function handleDistrictChange() {
                const districtName = document.getElementById('districtInput').value;
                const constituencySelect = document.getElementById('constituencyInput');
                const pollingStationSelect = document.getElementById('pollingStationInput');
                const stationNumberInput = document.getElementById('stationNumberInput');
                
                // Reset downstream selects
                constituencySelect.innerHTML = '<option value="">-- Select Constituency --</option>';
                pollingStationSelect.innerHTML = '<option value="">-- Select Polling Station --</option>';
                stationNumberInput.value = '';
                
                constituencySelect.disabled = true;
                pollingStationSelect.disabled = true;
                
                if (!districtName || !electoralData) return;
                
                // Find selected district
                const district = electoralData.find(d => d.district === districtName);
                if (!district) return;
                
                // Populate constituencies
                district.constituencies.forEach(constituency => {
                    const option = document.createElement('option');
                    option.value = constituency.constituency;
                    option.textContent = constituency.constituency;
                    constituencySelect.appendChild(option);
                });
                
                constituencySelect.disabled = false;
            }

            // Handle constituency selection
            function handleConstituencyChange() {
                const districtName = document.getElementById('districtInput').value;
                const constituencyName = document.getElementById('constituencyInput').value;
                const pollingStationSelect = document.getElementById('pollingStationInput');
                const stationNumberInput = document.getElementById('stationNumberInput');
                
                // Reset downstream selects
                pollingStationSelect.innerHTML = '<option value="">-- Select Polling Station --</option>';
                stationNumberInput.value = '';
                pollingStationSelect.disabled = true;
                
                if (!constituencyName || !electoralData) return;
                
                // Find selected district and constituency
                const district = electoralData.find(d => d.district === districtName);
                if (!district) return;
                
                const constituency = district.constituencies.find(c => c.constituency === constituencyName);
                if (!constituency) return;
                
                // Sort parts by part_number (numeric sort)
                const sortedParts = [...constituency.parts].sort((a, b) => {
                    const numA = parseInt(a.part_number) || 0;
                    const numB = parseInt(b.part_number) || 0;
                    return numA - numB;
                });
                
                // Populate polling stations
                sortedParts.forEach(part => {
                    const option = document.createElement('option');
                    option.value = part.part_name;
                    option.dataset.partNumber = part.part_number;
                    // Display format: "227 - Station Name"
                    option.textContent = `${part.part_number} - ${part.part_name}`;
                    pollingStationSelect.appendChild(option);
                });
                
                pollingStationSelect.disabled = false;
            }

            // Handle polling station selection
            function handlePollingStationChange() {
                const pollingStationSelect = document.getElementById('pollingStationInput');
                const stationNumberInput = document.getElementById('stationNumberInput');
                
                const selectedOption = pollingStationSelect.options[pollingStationSelect.selectedIndex];
                if (selectedOption && selectedOption.dataset.partNumber) {
                    stationNumberInput.value = selectedOption.dataset.partNumber;
                }
            }

            // Add event listeners (call after page loads)
            document.addEventListener('DOMContentLoaded', function() {
                const districtInput = document.getElementById('districtInput');
                const constituencyInput = document.getElementById('constituencyInput');
                const pollingStationInput = document.getElementById('pollingStationInput');
                
                if (districtInput) districtInput.addEventListener('change', handleDistrictChange);
                if (constituencyInput) constituencyInput.addEventListener('change', handleConstituencyChange);
                if (pollingStationInput) pollingStationInput.addEventListener('change', handlePollingStationChange);
            });

            function closeImportPanel() {
                const panel = document.getElementById('importPanel');
                const toggleBtn = document.querySelector('.toggle-btn');
                
                // Remove all panel state classes
                panel.classList.remove('open');
                panel.classList.remove('minimized');
                
                // Reset state variables
                isMinimized = false;
                
                // Reset toggle button to default state
                if (toggleBtn) {
                    toggleBtn.textContent = '◀';
                }
                
                // Reset import state when closing
                resetImport();
            }

            function toggleMinimize() {
                const panel = document.getElementById('importPanel');
                const toggleBtn = document.querySelector('.toggle-btn');
                
                if (isMinimized) {
                    panel.classList.remove('minimized');
                    toggleBtn.textContent = '◀';
                    isMinimized = false;
                } else {
                    panel.classList.add('minimized');
                    toggleBtn.textContent = '▶';
                    isMinimized = true;
                }
            }

            function minimizeAndContinue() {
                toggleMinimize();
                // Reload locations to include new data
                loadLocations();
            }

            function resetImport() {
                // Reset all steps
                document.getElementById('uploadStep').style.display = 'block';
                document.getElementById('pdfInfoSection').style.display = 'none';
                document.getElementById('progressStep').style.display = 'none';
                document.getElementById('completeStep').style.display = 'none';
                document.getElementById('errorStep').style.display = 'none';
                
                // Reset file input
                document.getElementById('pdfFile').value = '';
                
                // Cleanup temp file if exists
                if (currentTempFilePath) {
                    cleanupTempFile(currentTempFilePath);
                    currentTempFilePath = null;
                }
                
                currentImportId = null;
                importMetadata = null;
            }

            async function handleFileUpload() {
                const fileInput = document.getElementById('pdfFile');
                const file = fileInput.files[0];
                
                if (!file) return;
                
                try {
                    // Upload and get basic info (no AI, instant)
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    const response = await fetch('/api/import/identify', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (!data.success) {
                        throw new Error(data.error || 'Failed to process PDF');
                    }
                    
                    // Store metadata
                    importMetadata = data;
                    currentTempFilePath = data.temp_file_path;
                    
                    // Show PDF info and form
                    displayPdfInfo(data);
                    document.getElementById('pdfInfoSection').style.display = 'block';
                    
                } catch (error) {
                    document.getElementById('uploadStep').style.display = 'none';
                    document.getElementById('errorStep').style.display = 'block';
                    document.getElementById('errorMessage').textContent = '❌ ' + error.message;
                }
            }

            function displayPdfInfo(data) {
                const infoHtml = `
                    <div class="metadata-item">
                        <span class="metadata-label">PDF Name:</span>
                        <span class="metadata-value">${data.pdf_name}</span>
                    </div>
                    <div class="metadata-item">
                        <span class="metadata-label">Total Pages:</span>
                        <span class="metadata-value">${data.total_pages}</span>
                    </div>
                `;
                
                document.getElementById('pdfInfo').innerHTML = infoHtml;
            }

            async function cancelImport() {
                if (currentTempFilePath) {
                    await cleanupTempFile(currentTempFilePath);
                }
                resetImport();
            }

            async function cleanupTempFile(filePath) {
                try {
                    const formData = new FormData();
                    formData.append('temp_file_path', filePath);
                    
                    await fetch('/api/import/cleanup-temp', {
                        method: 'POST',
                        body: formData
                    });
                } catch (error) {
                    console.error('Cleanup error:', error);
                }
            }

            async function startExtraction() {
                const district = document.getElementById('districtInput').value.trim();
                const constituency = document.getElementById('constituencyInput').value.trim();
                const pollingStation = document.getElementById('pollingStationInput').value.trim();
                const stationNumber = document.getElementById('stationNumberInput').value.trim();
                const extractionMethod = document.getElementById('extractionMethod').value;
                
                if (!district || !constituency || !pollingStation) {
                    alert('Please fill in all required fields (District, Constituency, Polling Station)');
                    return;
                }
                
                // Validate and save API key if using Gemini
                let apiKey = null;
                if (extractionMethod === 'gemini') {
                    apiKey = document.getElementById('geminiApiKey').value.trim();
                    if (!apiKey) {
                        alert('Please enter your Gemini API key for AI-powered extraction.\n\nGet a free key at: https://aistudio.google.com/app/apikey');
                        return;
                    }
                    // Save to session storage for this session only
                    setGeminiApiKey(apiKey);
                }
                
                // Show progress step
                document.getElementById('uploadStep').style.display = 'none';
                document.getElementById('progressStep').style.display = 'block';
                
                try {
                    // Start extraction
                    const formData = new FormData();
                    formData.append('temp_file_path', currentTempFilePath);
                    formData.append('district', district);
                    formData.append('constituency', constituency);
                    formData.append('polling_station', pollingStation);
                    formData.append('extraction_method', extractionMethod);
                    if (stationNumber) formData.append('station_number', stationNumber);
                    if (apiKey) formData.append('gemini_api_key', apiKey);
                    
                    const response = await fetch('/api/import/start', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (data.detail) {
                        throw new Error(data.detail);
                    }
                    
                    currentImportId = data.import_id;
                    
                    // Start polling for progress
                    pollImportProgress();
                    
                } catch (error) {
                    document.getElementById('progressStep').style.display = 'none';
                    document.getElementById('errorStep').style.display = 'block';
                    document.getElementById('errorMessage').textContent = '❌ ' + error.message;
                }
            }

            async function pollImportProgress() {
                if (!currentImportId) return;
                
                try {
                    const response = await fetch(`/api/import/status/${currentImportId}`);
                    const status = await response.json();
                    
                    // Update UI
                    updateProgressUI(status);
                    
                    // Check if complete or failed
                    if (status.status === 'completed') {
                        showCompleteSummary(status);
                        return;
                    }
                    
                    if (status.status === 'failed') {
                        document.getElementById('progressStep').style.display = 'none';
                        document.getElementById('errorStep').style.display = 'block';
                        document.getElementById('errorMessage').textContent = '❌ ' + (status.error || 'Import failed');
                        return;
                    }
                    
                    // Continue polling
                    setTimeout(pollImportProgress, 2000);
                    
                } catch (error) {
                    console.error('Polling error:', error);
                    setTimeout(pollImportProgress, 2000);
                }
            }

            function updateProgressUI(status) {
                // Update progress bar
                document.getElementById('progressFill').style.width = status.progress + '%';
                document.getElementById('progressText').textContent = status.progress + '%';
                
                // Update status text with method info
                let statusText = 'Processing...';
                const method = status.extraction_method === 'tesseract' ? 'OCR' : 'AI';
                
                if (status.status === 'extracting') {
                    statusText = `Extracting with ${method} (data searchable now!)...`;
                } else if (status.status === 'rebuilding_index') {
                    statusText = 'Rebuilding search index...';
                }
                document.getElementById('statusText').textContent = statusText;
                
                // Update details
                if (status.total_pages > 0) {
                    document.getElementById('pageText').textContent = 
                        `${status.current_page} / ${status.total_pages}`;
                }
                document.getElementById('votersText').textContent = status.voters_extracted || 0;
            }

            function showCompleteSummary(status) {
                document.getElementById('progressStep').style.display = 'none';
                document.getElementById('completeStep').style.display = 'block';
                
                const summaryHtml = `
                    <p><strong>Total Voters:</strong> ${status.voters_extracted}</p>
                    <p><strong>Pages Processed:</strong> ${status.total_pages}</p>
                    <p><strong>Time:</strong> ${calculateDuration(status.started_at, status.completed_at)}</p>
                `;
                document.getElementById('completeSummary').innerHTML = summaryHtml;
            }

            function calculateDuration(startTime, endTime) {
                const start = new Date(startTime);
                const end = new Date(endTime);
                const seconds = Math.floor((end - start) / 1000);
                const minutes = Math.floor(seconds / 60);
                const remainingSeconds = seconds % 60;
                return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${seconds}s`;
            }

            function refreshPage() {
                window.location.reload();
            }
        </script>
    </body>
    </html>
    """


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    stats = await db.get_stats()
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "database": stats
    }


@app.get("/api/search")
async def api_search(
    query: str = Query(default="*", description="Search query (* for all entries)"),
    search_type: str = Query(default="fuzzy", description="Search type"),
    district: Optional[str] = Query(None, description="Filter by district"),
    constituency: Optional[str] = Query(None, description="Filter by constituency"),
    polling_station: Optional[str] = Query(None, description="Filter by polling station"),
    limit: int = Query(default=50, ge=1, le=500, description="Results per page"),
    offset: int = Query(default=0, ge=0, description="Pagination offset")
):
    """
    Search for voters with multiple strategies.

    - **fuzzy**: Full-text search with typo tolerance (default, best for general search)
    - **exact**: Exact name match
    - **voter_id**: Search by voter ID
    - **prefix**: Prefix matching (good for autocomplete)
    - **query='*'**: Return all entries (with filters)
    """
    try:
        results = await search_service.search(
            query=query,
            search_type=search_type,
            district=district,
            constituency=constituency,
            polling_station=polling_station,
            limit=limit,
            offset=offset
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/suggest")
async def api_suggest(
    prefix: str = Query(..., min_length=1, description="Name prefix for autocomplete"),
    limit: int = Query(default=10, ge=1, le=50, description="Max suggestions")
):
    """Get autocomplete suggestions."""
    try:
        suggestions = await search_service.get_suggestions(prefix, limit)
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/locations")
async def api_locations():
    """Get all available districts, constituencies, and polling stations."""
    try:
        locations = await search_service.get_locations()
        return locations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/check-data")
async def api_check_data(
    district: Optional[str] = Query(None, description="District name"),
    constituency: Optional[str] = Query(None, description="Constituency name"),
    polling_station: Optional[str] = Query(None, description="Polling station name")
):
    """Check if voter data exists for the given location filters."""
    try:
        result = await search_service.check_data_exists(district, constituency, polling_station)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cache/clear")
async def clear_cache():
    """Clear search cache."""
    search_service.clear_cache()
    return {"status": "success", "message": "Cache cleared"}


@app.get("/api/stats")
async def api_stats():
    """Get database statistics."""
    try:
        stats = await db.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# PDF Import Endpoints
@app.post("/api/import/identify")
async def import_identify_pdf(file: UploadFile = File(...), gemini_api_key: str = Form(None)):
    """
    Upload PDF and get basic info (fast, no AI extraction)
    gemini_api_key: User's Gemini API key (optional, for validation only)
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Get basic PDF info (no AI, just page count)
        info = await pdf_import_service.get_pdf_info(tmp_file_path, gemini_api_key)
        
        # Store temp file path for later use
        info['temp_file_path'] = tmp_file_path
        
        return info
        
    except Exception as e:
        # Cleanup on error
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/import/start")
async def import_start_extraction(
    temp_file_path: str = Form(...),
    district: str = Form(...),
    constituency: str = Form(...),
    polling_station: str = Form(...),
    station_number: str = Form(None),
    extraction_method: str = Form('gemini'),
    gemini_api_key: str = Form(None)
):
    """
    Start extraction process after user confirms metadata
    extraction_method: 'gemini' for AI (slower, accurate) or 'tesseract' for OCR (faster, less accurate)
    gemini_api_key: User's Gemini API key (session-only, never persisted)
    """
    try:
        # Validate temp file exists
        if not os.path.exists(temp_file_path):
            raise HTTPException(status_code=400, detail="Temporary file not found")
        
        # Validate Gemini API key if using gemini extraction
        if extraction_method == 'gemini' and not gemini_api_key:
            raise HTTPException(status_code=400, detail="Gemini API key is required for AI-powered extraction")
        
        # Generate unique import ID
        import_id = str(uuid.uuid4())
        
        # Start import in background
        result = await pdf_import_service.start_import(
            import_id=import_id,
            pdf_path=temp_file_path,
            district=district,
            constituency=constituency,
            polling_station=polling_station,
            station_number=station_number,
            extraction_method=extraction_method,
            gemini_api_key=gemini_api_key
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/import/status/{import_id}")
async def import_get_status(import_id: str):
    """
    Get status of an import job
    """
    status = pdf_import_service.get_import_status(import_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    return status


@app.get("/api/electoral-data")
async def get_electoral_data():
    """
    Get complete electoral data from database (districts, constituencies, parts)
    """
    try:
        # Get all districts with their constituencies and parts
        districts_query = """
            SELECT d.id, d.name,
                   c.id as constituency_id, c.name as constituency_name,
                   ps.id as part_id, ps.name as part_name, ps.station_number
            FROM districts d
            LEFT JOIN constituencies c ON d.id = c.district_id
            LEFT JOIN polling_stations ps ON c.id = ps.constituency_id
            ORDER BY d.name, c.name, CAST(ps.station_number AS INTEGER)
        """
        
        rows = await db.fetch_all(districts_query)
        
        # Structure the data
        districts = {}
        for row in rows:
            district_id = row['id']
            district_name = row['name']
            constituency_id = row['constituency_id']
            constituency_name = row['constituency_name']
            
            if district_id not in districts:
                districts[district_id] = {
                    'district': district_name,
                    'constituencies': {}
                }
            
            if constituency_id and constituency_id not in districts[district_id]['constituencies']:
                districts[district_id]['constituencies'][constituency_id] = {
                    'constituency': constituency_name,
                    'parts': []
                }
            
            if row['part_id']:
                districts[district_id]['constituencies'][constituency_id]['parts'].append({
                    'part_number': row['station_number'],
                    'part_name': row['part_name']
                })
        
        # Convert to array format
        result = []
        for district_data in districts.values():
            result.append({
                'district': district_data['district'],
                'constituencies': [
                    {
                        'constituency': c['constituency'],
                        'parts': c['parts']
                    }
                    for c in district_data['constituencies'].values()
                ]
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/import/cleanup-temp")
async def import_cleanup_temp(temp_file_path: str = Form(...)):
    """
    Cleanup temporary file if user cancels
    """
    try:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        return {"status": "success", "message": "Temporary file cleaned up"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
