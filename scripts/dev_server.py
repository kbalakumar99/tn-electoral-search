#!/usr/bin/env python3
"""
Development server with auto-reload.
"""
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000, 
        reload=True,
        log_level="info",
        reload_dirs=[str(Path(__file__).parent.parent / 'app')]
    )