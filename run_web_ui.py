#!/usr/bin/env python3
"""
Flingoos Web UI Runner

Simple runner for the web interface that communicates with Session Manager API.
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from web_ui.web_server import WebUIServer

def main():
    parser = argparse.ArgumentParser(description="Flingoos Web UI")
    parser.add_argument("--port", type=int, default=8844, help="Port to run on")
    parser.add_argument("--session-manager-url", default="http://localhost:8845", 
                       help="Session Manager API URL")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        server = WebUIServer(port=args.port, session_manager_url=args.session_manager_url)
        server.run()
    except KeyboardInterrupt:
        print("\n🛑 Web UI stopped by user")
    except Exception as e:
        print(f"❌ Error starting Web UI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
