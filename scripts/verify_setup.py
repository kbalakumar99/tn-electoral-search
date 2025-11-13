#!/usr/bin/env python3
"""
Verify that the application setup is correct.
"""
import sys
import importlib
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

def check_imports():
    """Check that all required modules can be imported."""
    modules = [
        'main',
        'database', 
        'search_service',
        'pdf_service'
    ]
    
    print("🔍 Checking module imports...")
    
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            return False
    
    return True

def check_database():
    """Check database configuration."""
    print("\n🗄️  Checking database configuration...")
    
    try:
        from database import DB_PATH, SCHEMA_PATH
        
        print(f"  Database path: {DB_PATH}")
        print(f"  Schema path: {SCHEMA_PATH}")
        
        if SCHEMA_PATH.exists():
            print("  ✅ Schema file exists")
        else:
            print("  ❌ Schema file missing")
            return False
            
        # Check if database directory exists
        DB_PATH.parent.mkdir(exist_ok=True)
        print("  ✅ Database directory ready")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database check failed: {e}")
        return False

def check_dependencies():
    """Check required dependencies."""
    print("\n📦 Checking dependencies...")
    
    required = [
        'fastapi',
        'uvicorn', 
        'aiosqlite',
        'cachetools',
        'pydantic'
    ]
    
    missing = []
    
    for dep in required:
        try:
            importlib.import_module(dep)
            print(f"  ✅ {dep}")
        except ImportError:
            print(f"  ❌ {dep}")
            missing.append(dep)
    
    if missing:
        print(f"\n💡 Install missing dependencies:")
        print(f"   pip install {' '.join(missing)}")
        return False
        
    return True

def main():
    """Run all verification checks."""
    print("🚀 TN Electoral Search - Setup Verification")
    print("=" * 50)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Module Imports", check_imports), 
        ("Database Config", check_database)
    ]
    
    all_passed = True
    
    for name, check_func in checks:
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 All checks passed! Ready to run:")
        print("   python scripts/init_db.py")
        print("   python scripts/dev_server.py")
    else:
        print("❌ Some checks failed. Please fix issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()