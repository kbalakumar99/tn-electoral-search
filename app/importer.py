"""
CSV Import module for loading electoral data into the database.
Handles hierarchical data structure and bulk inserts for performance.
"""
import pandas as pd
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from database import db
import re
import logging

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class ElectoralDataImporter:
    """Import electoral data from CSV files."""

    def __init__(self):
        self.district_cache: Dict[str, int] = {}
        self.constituency_cache: Dict[Tuple[int, str], int] = {}
        self.polling_station_cache: Dict[Tuple[int, str], int] = {}
        self._insert_lock = asyncio.Lock()  # Lock for thread-safe inserts

    async def import_csv(self, csv_path: str, district_name: str, constituency_name: str,
                        polling_station_name: str, station_number: str = None) -> dict:
        """
        Import a single CSV file into the database.

        Args:
            csv_path: Path to the CSV file
            district_name: Name of the district
            constituency_name: Name of the constituency
            polling_station_name: Name of the polling station
            station_number: Optional station number

        Returns:
            Dictionary with import statistics
        """
        print(f"Importing {csv_path}...")

        # Read CSV file
        df = pd.read_csv(csv_path)

        # Get or create district
        district_id = await self._get_or_create_district(district_name)

        # Get or create constituency
        constituency_id = await self._get_or_create_constituency(
            district_id, constituency_name
        )

        # Get or create polling station
        polling_station_id = await self._get_or_create_polling_station(
            constituency_id, polling_station_name, station_number
        )

        # Prepare voter records
        voters = []
        for _, row in df.iterrows():
            voter = self._parse_voter_row(row, polling_station_id)
            if voter:
                voters.append(voter)

        # Bulk insert voters
        if voters:
            await self._bulk_insert_voters(voters)

        stats = {
            'csv_file': csv_path,
            'district': district_name,
            'constituency': constituency_name,
            'polling_station': polling_station_name,
            'voters_imported': len(voters)
        }

        print(f"✓ Imported {len(voters)} voters from {Path(csv_path).name}")
        return stats

    async def _get_or_create_district(self, name: str) -> int:
        """Get or create district and return its ID."""
        if name in self.district_cache:
            return self.district_cache[name]

        # Check if exists
        result = await db.fetch_one(
            "SELECT id FROM districts WHERE name = ?", (name,)
        )

        if result:
            district_id = result['id']
        else:
            # Create new district
            cursor = await db.execute(
                "INSERT INTO districts (name, code) VALUES (?, ?)",
                (name, self._generate_code(name))
            )
            district_id = cursor.lastrowid

        self.district_cache[name] = district_id
        return district_id

    async def _get_or_create_constituency(self, district_id: int, name: str) -> int:
        """Get or create constituency and return its ID."""
        cache_key = (district_id, name)
        if cache_key in self.constituency_cache:
            return self.constituency_cache[cache_key]

        # Check if exists
        result = await db.fetch_one(
            "SELECT id FROM constituencies WHERE district_id = ? AND name = ?",
            (district_id, name)
        )

        if result:
            constituency_id = result['id']
        else:
            # Create new constituency
            cursor = await db.execute(
                "INSERT INTO constituencies (district_id, name, code) VALUES (?, ?, ?)",
                (district_id, name, self._generate_code(name))
            )
            constituency_id = cursor.lastrowid

        self.constituency_cache[cache_key] = constituency_id
        return constituency_id

    async def _get_or_create_polling_station(self, constituency_id: int,
                                            name: str, station_number: str = None) -> int:
        """Get or create polling station and return its ID."""
        cache_key = (constituency_id, station_number or name)
        if cache_key in self.polling_station_cache:
            return self.polling_station_cache[cache_key]

        # Check if exists
        query = "SELECT id FROM polling_stations WHERE constituency_id = ? AND "
        if station_number:
            query += "station_number = ?"
            params = (constituency_id, station_number)
        else:
            query += "name = ?"
            params = (constituency_id, name)

        result = await db.fetch_one(query, params)

        if result:
            polling_station_id = result['id']
        else:
            # Create new polling station
            cursor = await db.execute(
                "INSERT INTO polling_stations (constituency_id, name, station_number) VALUES (?, ?, ?)",
                (constituency_id, name, station_number)
            )
            polling_station_id = cursor.lastrowid

        self.polling_station_cache[cache_key] = polling_station_id
        return polling_station_id

    def _parse_voter_row(self, row: pd.Series, polling_station_id: int) -> Optional[tuple]:
        """Parse a CSV row into voter tuple for database insertion."""
        try:
            # Extract voter data based on CSV column names
            serial_number = str(row.get('Serial Number (வரிசை எண்)', '')).strip()
            division_no = str(row.get('Division No (பிரிவு எண்)', '')).strip()
            house_no = str(row.get('House No (வீட்டு எண்)', '')).strip()
            voter_name = str(row.get('Voter Name (வாக்காளரின் பெயர்)', '')).strip()
            relationship_code = str(row.get('Relationship Code (உறவு முறை)', '')).strip()
            relative_name = str(row.get('Relative Name (உறவினர் பெயர்)', '')).strip()
            age_str = str(row.get('Age (வயது)', '')).strip()
            gender_caste = str(row.get('Gender/Caste Code (இனம்)', '')).strip()
            voter_id = str(row.get('Voter ID No (வாக்காளர் அடையாள அட்டை எண்)', '')).strip()

            # Parse age
            try:
                age = int(age_str) if age_str and age_str.isdigit() else None
            except:
                age = None

            # Clean voter ID (remove if empty or just whitespace)
            voter_id = voter_id if voter_id and voter_id != 'nan' else None

            # Skip if no voter name
            if not voter_name or voter_name == 'nan':
                return None

            return (
                polling_station_id,
                serial_number,
                division_no or None,
                house_no or None,
                voter_name,
                voter_name,  # Store in both English and Tamil fields for now
                relationship_code or None,
                relative_name or None,
                relative_name,  # Store in both English and Tamil fields
                age,
                gender_caste or None,
                None,  # caste_code (separate if needed)
                voter_id
            )
        except Exception as e:
            logger.error(f"   ❌ Error parsing row: {e}")
            logger.error(f"      Row data: {row.to_dict() if hasattr(row, 'to_dict') else row}")
            return None

    async def _bulk_insert_voters(self, voters: List[tuple]):
        """Bulk insert voters for better performance."""
        async with self._insert_lock:  # Ensure only one insert at a time
            logger.info(f"   📝 Preparing to insert {len(voters)} voters...")
            
            query = """
                INSERT OR IGNORE INTO voters (
                    polling_station_id, serial_number, division_no, house_no,
                    voter_name, voter_name_tamil, relationship_code,
                    relative_name, relative_name_tamil, age, gender, caste_code, voter_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            try:
                # Insert voters into main table
                await db.execute_many(query, voters)
                logger.info(f"   ✅ Database INSERT completed for {len(voters)} voters")
                
                # Get the inserted row IDs for FTS sync
                if voters:
                    sample_ps_id = voters[0][0]  # polling_station_id
                    
                    # Sync newly inserted voters to FTS (contentless FTS5 manual sync)
                    try:
                        fts_sync_query = """
                            INSERT INTO voters_fts(rowid, voter_name, voter_name_tamil, relative_name,
                                                  relative_name_tamil, voter_id, serial_number, house_no)
                            SELECT id, voter_name, voter_name_tamil, relative_name,
                                   relative_name_tamil, voter_id, serial_number, house_no
                            FROM voters 
                            WHERE polling_station_id = ? 
                            AND id NOT IN (SELECT rowid FROM voters_fts WHERE rowid IS NOT NULL)
                        """
                        await db.execute(fts_sync_query, (sample_ps_id,))
                        logger.info(f"   🔍 FTS synced for polling_station_id={sample_ps_id}")
                    except Exception as fts_error:
                        logger.warning(f"   ⚠️ FTS sync failed (non-critical): {fts_error}")
                    
                    # Verify insertion
                    count_query = "SELECT COUNT(*) as count FROM voters WHERE polling_station_id = ?"
                    result = await db.fetch_one(count_query, (sample_ps_id,))
                    logger.info(f"   🔍 Verification: {result['count']} total voters in polling_station_id={sample_ps_id}")
            except Exception as e:
                logger.error(f"   ❌ Database INSERT failed: {e}")
                raise

    def _generate_code(self, name: str) -> str:
        """Generate a code from name (simple implementation)."""
        # Remove special characters and take first 10 chars
        code = re.sub(r'[^a-zA-Z0-9]', '', name).upper()[:10]
        return code


async def import_sample_data():
    """Import the sample CSV data."""
    importer = ElectoralDataImporter()

    # Import the sample file
    csv_path = "/Users/bala-2082/ZC/POC/pdf-OCR-search/output/248-tiruveumbur-page 25_gemini.csv"

    # Extract metadata from filename
    # Format: <constituency-code>-<constituency-name>-page <page-num>_<source>.csv
    filename = Path(csv_path).stem
    parts = filename.split('-')

    constituency_code = parts[0] if len(parts) > 0 else "248"
    constituency_name = parts[1] if len(parts) > 1 else "tiruveumbur"
    page_info = parts[2] if len(parts) > 2 else "page 25"

    stats = await importer.import_csv(
        csv_path=csv_path,
        district_name="Tiruchirappalli",  # Default district, update as needed
        constituency_name=constituency_name.title(),
        polling_station_name=f"Station {constituency_code}",
        station_number=constituency_code
    )

    print("\nImport completed!")
    print(f"Statistics: {stats}")

    # Rebuild FTS index
    print("\nRebuilding search index...")
    await db.rebuild_fts_index()
    print("✓ Search index ready")

    # Show database stats
    db_stats = await db.get_stats()
    print(f"\nDatabase Statistics:")
    print(f"  Districts: {db_stats['districts']}")
    print(f"  Constituencies: {db_stats['constituencies']}")
    print(f"  Polling Stations: {db_stats['polling_stations']}")
    print(f"  Voters: {db_stats['voters']}")
    print(f"  Database Size: {db_stats['db_size_mb']} MB")


if __name__ == "__main__":
    asyncio.run(import_sample_data())
