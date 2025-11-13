#!/usr/bin/env python3
"""
Populate database with electoral location data from JSON.
Use this script to reset/populate just the location data without affecting voter data.
"""
import asyncio
import sys
import json
import sqlite3
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from database import db

async def populate_electoral_data():
    """Load electoral_rolls_complete.json and populate database with location data."""
    
    # Load JSON data
    json_path = Path(__file__).parent.parent / 'config' / 'electoral_rolls_complete.json'
    
    if not json_path.exists():
        print(f"❌ Error: {json_path} not found")
        print("Make sure the electoral_rolls_complete.json file exists in the config/ directory")
        return False
    
    print("📊 Loading electoral data from JSON...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✓ Loaded data: {len(data)} districts")
    
    # Use the database connection
    db_path = Path(__file__).parent.parent / "database" / "electoral_data.db"
    
    if not db_path.exists():
        print("❌ Database not found. Please run 'python scripts/init_db.py' first")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get current voter count before clearing location data
    cursor.execute("SELECT COUNT(*) FROM voters")
    voter_count = cursor.fetchone()[0]
    
    if voter_count > 0:
        print(f"⚠️  Found {voter_count} voters in database")
        response = input("This will clear location data but keep voters. Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Operation cancelled")
            conn.close()
            return False
    
    # Clear existing location data (keep voters)
    print("🧹 Clearing existing location data...")
    cursor.execute("DELETE FROM polling_stations")
    cursor.execute("DELETE FROM constituencies")  
    cursor.execute("DELETE FROM districts")
    conn.commit()
    
    # Populate districts, constituencies, and polling stations
    print("📍 Populating database with electoral locations...")
    
    total_districts = 0
    total_constituencies = 0
    total_parts = 0
    duplicates_skipped = 0
    
    for district_data in data:
        district_name = district_data['district']
        
        # Insert district
        cursor.execute(
            "INSERT INTO districts (name) VALUES (?)",
            (district_name,)
        )
        district_id = cursor.lastrowid
        total_districts += 1
        
        for constituency_data in district_data['constituencies']:
            constituency_name = constituency_data['constituency']
            
            # Insert constituency
            cursor.execute(
                "INSERT INTO constituencies (district_id, name) VALUES (?, ?)",
                (district_id, constituency_name)
            )
            constituency_id = cursor.lastrowid
            total_constituencies += 1
            
            # Track unique part numbers per constituency
            seen_parts = set()
            
            # Insert parts/polling stations
            for part in constituency_data['parts']:
                part_number = part['part_number']
                part_name = part['part_name']
                
                # Skip duplicate part numbers in same constituency
                if part_number in seen_parts:
                    duplicates_skipped += 1
                    continue
                
                seen_parts.add(part_number)
                
                try:
                    # Insert into polling_stations
                    cursor.execute(
                        """INSERT INTO polling_stations 
                           (constituency_id, name, station_number) 
                           VALUES (?, ?, ?)""",
                        (constituency_id, part_name, part_number)
                    )
                    total_parts += 1
                except sqlite3.IntegrityError:
                    duplicates_skipped += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Electoral data populated successfully!")
    print(f"   - Districts: {total_districts}")
    print(f"   - Constituencies: {total_constituencies}")
    print(f"   - Polling Stations: {total_parts}")
    if duplicates_skipped > 0:
        print(f"   - Duplicates skipped: {duplicates_skipped}")
    
    return True

async def main():
    """Main function to populate electoral data."""
    print("🚀 TN Electoral Search - Data Population")
    print("=" * 50)
    
    success = await populate_electoral_data()
    
    if success:
        # Show final statistics
        stats = await db.get_stats()
        print(f"\n📊 Final database statistics:")
        print(f"   - {stats['districts']} districts")
        print(f"   - {stats['constituencies']} constituencies") 
        print(f"   - {stats['polling_stations']} polling stations")
        print(f"   - {stats['voters']} voters")
        print(f"   - Database size: {stats['db_size_mb']} MB")
        
        print(f"\n🎉 Data population complete!")
    else:
        print(f"\n❌ Data population failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))