#!/usr/bin/env python3
"""
Test script to validate workflow retrieval and display
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from web_ui.web_server import WebUIServer

def test_workflow_retrieval():
    """Test workflow retrieval from Firestore"""
    print("Testing workflow retrieval...")
    
    # Create server instance
    server = WebUIServer()
    
    # Test Firestore client
    print(f"Firestore client initialized: {server.firestore_client is not None}")
    
    # Test workflow retrieval
    try:
        workflow_data = server.firestore_client.get_random_published_workflow("diligent4")
        print(f"Workflow data retrieved: {workflow_data is not None}")
        
        if workflow_data:
            print(f"Workflow structure: {list(workflow_data.keys())}")
            if 'workflow' in workflow_data:
                workflow = workflow_data['workflow']
                print(f"Workflow fields: {list(workflow.keys())}")
                print(f"Title: {workflow.get('title', 'N/A')}")
                print(f"ID: {workflow.get('id', 'N/A')}")
                print(f"Has guide_markdown: {'guide_markdown' in workflow}")
                if 'guide_markdown' in workflow:
                    guide_length = len(workflow['guide_markdown'])
                    print(f"Guide markdown length: {guide_length} characters")
                    print(f"Guide preview: {workflow['guide_markdown'][:200]}...")
            else:
                print("ERROR: No 'workflow' key in data")
        else:
            print("ERROR: No workflow data returned")
            
    except Exception as e:
        print(f"ERROR retrieving workflow: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_workflow_retrieval()
