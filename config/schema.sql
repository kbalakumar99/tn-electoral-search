-- Electoral Data Database Schema
-- Hierarchical structure: District -> Constituency -> Polling Station -> Voters

-- Districts table
CREATE TABLE IF NOT EXISTS districts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Constituencies table
CREATE TABLE IF NOT EXISTS constituencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    code TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (district_id) REFERENCES districts(id),
    UNIQUE(district_id, name)
);

-- Polling Stations table
CREATE TABLE IF NOT EXISTS polling_stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    constituency_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    station_number TEXT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (constituency_id) REFERENCES constituencies(id),
    UNIQUE(constituency_id, station_number)
);

-- Voters table
CREATE TABLE IF NOT EXISTS voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    polling_station_id INTEGER NOT NULL,
    serial_number TEXT NOT NULL,
    division_no TEXT,
    house_no TEXT,
    voter_name TEXT NOT NULL,
    voter_name_tamil TEXT,
    relationship_code TEXT,
    relative_name TEXT,
    relative_name_tamil TEXT,
    age INTEGER,
    gender TEXT,
    caste_code TEXT,
    voter_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (polling_station_id) REFERENCES polling_stations(id),
    UNIQUE(polling_station_id, serial_number)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_voters_polling_station ON voters(polling_station_id);
CREATE INDEX IF NOT EXISTS idx_voters_voter_id ON voters(voter_id);
CREATE INDEX IF NOT EXISTS idx_voters_serial ON voters(serial_number);
CREATE INDEX IF NOT EXISTS idx_polling_stations_constituency ON polling_stations(constituency_id);
CREATE INDEX IF NOT EXISTS idx_constituencies_district ON constituencies(district_id);

-- FTS5 Virtual Table for Full-Text Search
-- This enables blazingly fast text search with ranking
CREATE VIRTUAL TABLE IF NOT EXISTS voters_fts USING fts5(
    voter_name,
    voter_name_tamil,
    relative_name,
    relative_name_tamil,
    voter_id,
    serial_number,
    house_no,
    content='voters',
    content_rowid='id'
);

-- View for easy querying with all hierarchical information
CREATE VIEW IF NOT EXISTS voters_complete AS
SELECT
    v.id,
    v.serial_number,
    v.division_no,
    v.house_no,
    v.voter_name,
    v.voter_name_tamil,
    v.relationship_code,
    v.relative_name,
    v.relative_name_tamil,
    v.age,
    v.gender,
    v.caste_code,
    v.voter_id,
    ps.name as polling_station_name,
    ps.station_number as polling_station_number,
    c.name as constituency_name,
    c.code as constituency_code,
    d.name as district_name,
    d.code as district_code
FROM voters v
JOIN polling_stations ps ON v.polling_station_id = ps.id
JOIN constituencies c ON ps.constituency_id = c.id
JOIN districts d ON c.district_id = d.id;
