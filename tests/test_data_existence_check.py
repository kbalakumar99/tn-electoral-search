#!/usr/bin/env python3
"""
Test script for the new data existence check functionality.
This ensures the UI properly alerts users when no data exists for selected locations.
"""
import asyncio
import requests
import json
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

async def test_data_existence_api():
    """Test the new /api/check-data endpoint."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Data Existence Check API")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Location with data (Tiruchirappalli → Tiruveumbur)",
            "params": {"district": "Tiruchirappalli", "constituency": "Tiruveumbur"},
            "expected_exists": True
        },
        {
            "name": "Location without data (Ariyalur → Ariyalur)", 
            "params": {"district": "Ariyalur", "constituency": "Ariyalur"},
            "expected_exists": False
        },
        {
            "name": "Specific polling station with data",
            "params": {"district": "Tiruchirappalli", "constituency": "Tiruveumbur", "polling_station": "Station 248"},
            "expected_exists": True
        },
        {
            "name": "Non-existent polling station",
            "params": {"district": "Tiruchirappalli", "constituency": "Tiruveumbur", "polling_station": "Non-Existent Station"},
            "expected_exists": False
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}")
        print("-" * 40)
        
        try:
            response = requests.get(f"{base_url}/api/check-data", params=test['params'], timeout=5)
            response.raise_for_status()
            data = response.json()
            
            print(f"   Request: {test['params']}")
            print(f"   Response: exists={data['exists']}, count={data['count']}")
            
            if data['exists'] == test['expected_exists']:
                print(f"   ✅ PASS - Expected exists={test['expected_exists']}")
            else:
                print(f"   ❌ FAIL - Expected exists={test['expected_exists']}, got {data['exists']}")
                
        except requests.RequestException as e:
            print(f"   ❌ ERROR - Request failed: {e}")
        except Exception as e:
            print(f"   ❌ ERROR - Unexpected error: {e}")

def main():
    """Main test function."""
    print("🚀 Starting Electoral Search Data Existence Tests")
    print("Make sure the server is running on http://localhost:8000")
    print()
    
    try:
        # Check if server is running
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        response.raise_for_status()
        print("✅ Server is running")
        
        # Run tests
        asyncio.run(test_data_existence_api())
        
        print("\n" + "=" * 50)
        print("🎉 Test completed!")
        print("\n📝 What this feature does:")
        print("- Before searching, checks if any data exists for selected location")
        print("- If no data exists, shows helpful alert with import guidance")
        print("- Distinguishes between 'no data exists' vs 'search returned no matches'")
        print("- Provides clear user guidance to import missing data")
        
    except requests.RequestException:
        print("❌ Server is not running. Start it with:")
        print("   cd electoral_search && python main.py")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()