#!/usr/bin/env python3
"""
Production server runner script.
"""
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

if __name__ == "__main__":
    import uvicorn
    from main import app
    
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=8000,
        reload=False,
        log_level="info"
    )