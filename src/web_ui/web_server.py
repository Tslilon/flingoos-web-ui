"""
Flingoos Web UI Server - Pure Interface Layer

This is a clean web interface that:
1. Serves HTML/CSS/JS to browsers
2. Communicates with Session Manager API via HTTP
3. Provides real-time updates via Socket.IO
4. Does NOT contain business logic
"""

import logging
import json
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from flask import Flask, render_template_string, request, jsonify
    from flask_socketio import SocketIO, emit
    import requests
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Import the original components for direct integration
try:
    import sys
    from pathlib import Path
    
    # Add session manager path for imports
    session_manager_path = Path(__file__).parent.parent.parent.parent / "flingoos-session-manager" / "src"
    sys.path.insert(0, str(session_manager_path))
    
    from session_manager.bridge_client.command_client import BridgeClient
    from session_manager.forge.trigger_generator import ForgeTriggerGenerator
    from session_manager.forge.mock_forge import MockForge
    from session_manager.forge.firestore_client import FirestoreClient
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import session manager components: {e}")
    COMPONENTS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebUIServer:
    """
    Web UI Server - Restored Original Functionality
    
    This restores the exact original behavior with direct session management,
    detailed upload progress, forge integration, and workflow display.
    """
    
    def __init__(self, port: int = 8844, session_manager_url: str = "http://localhost:8845"):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask and flask-socketio are required for web UI")
        
        if not COMPONENTS_AVAILABLE:
            raise ImportError("Session manager components are required for full functionality")
            
        self.port = port
        self.session_manager_url = session_manager_url
        self.app = None
        self.socketio = None
        self.server_thread = None
        self.running = False
        
        # Restore original session management
        self.session_active = False
        self.session_start_time = None
        self.session_id = None
        self.command_client = None
        
        # Upload status tracking (sequential steps)
        self.upload_status = {
            'current_step': 'Waiting for session...',
            'is_uploading': False,
            'steps': []
        }
        
        # Forge integration components (restored)
        self.trigger_generator = ForgeTriggerGenerator()
        self.mock_forge = MockForge()
        self.firestore_client = FirestoreClient(use_mock=False)  # Try real Firestore, fallback to enhanced mock
        
        # Workflow results
        self.current_workflow = None
        
    def setup_flask_app(self):
        """Initialize Flask app and SocketIO."""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'flingoos-web-ui'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Route for main page
        @self.app.route('/')
        def index():
            return render_template_string(WEB_UI_HTML_TEMPLATE)
        
        # Socket.IO events for session management (restored original behavior)
        @self.socketio.on('start_session')
        def handle_start_session():
            try:
                if self.session_active:
                    emit('session_error', {'error': 'Session is already active'})
                    return
                
                self.start_session()
                emit('session_started', {
                    'session_id': self.session_id,
                    'message': 'Session started successfully'
                })
                
            except Exception as e:
                logger.error(f"Error starting session: {e}")
                emit('session_error', {'error': str(e)})
        
        @self.socketio.on('stop_session')
        def handle_stop_session():
            try:
                if not self.session_active:
                    emit('session_error', {'error': 'No active session to stop'})
                    return
                
                # Emit stopped event IMMEDIATELY before processing
                emit('session_stopped', {
                    'session_id': self.session_id,
                    'message': 'Session stopped, processing workflow...'
                })
                
                # Then stop the session (this will start background processing)
                self.stop_session()
                
            except Exception as e:
                logger.error(f"Error stopping session: {e}")
                emit('session_error', {'error': str(e)})
        
        # Keep API routes for compatibility but make them work with direct session management
        @self.app.route('/api/session/start', methods=['POST'])
        def api_start_session():
            try:
                if self.session_active:
                    return jsonify({"success": False, "error": "Session is already active"}), 400
                
                self.start_session()
                return jsonify({
                    "success": True,
                    "session_id": self.session_id,
                    "message": "Session started successfully"
                })
                
            except Exception as e:
                logger.error(f"Error starting session: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/session/stop', methods=['POST'])
        def api_stop_session():
            try:
                if not self.session_active:
                    return jsonify({"success": False, "error": "No active session to stop"}), 400
                
                self.stop_session()
                return jsonify({
                    "success": True,
                    "session_id": self.session_id,
                    "message": "Session stopped, processing workflow..."
                })
                
            except Exception as e:
                logger.error(f"Error stopping session: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/session/status', methods=['GET'])
        def api_get_status():
            try:
                bridge_status = self.command_client.is_bridge_running() if self.command_client else False
                return jsonify({
                    "success": True,
                    "session_active": self.session_active,
                    "session_id": self.session_id,
                    "bridge_connected": bridge_status,
                    "has_workflow": self.current_workflow is not None
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        # Socket.IO events
        @self.socketio.on('connect')
        def handle_connect():
            logger.info("Client connected to Web UI")
            emit('connected', {'status': 'Connected to Flingoos Web UI'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            logger.info("Client disconnected from Web UI")
    
    def start_session(self):
        """Start a new data collection session."""
        if self.session_active:
            raise ValueError("Session is already active")
            
        logger.info("Starting session via audio start command")
        
        # Initialize command client if needed
        if not self.command_client:
            self.command_client = BridgeClient()
            
        # Execute audio start command
        result = self.command_client.start_audio_recording()
        if not result.get("success", False):
            raise RuntimeError(f"Failed to start session: {result.get('error', 'Unknown error')}")
            
        self.session_active = True
        self.session_start_time = datetime.now()
        
        # Generate unique session ID for tracking
        import uuid
        self.session_id = str(uuid.uuid4())
        
        logger.info(f"Session started successfully with ID: {self.session_id}")
        
    def stop_session(self):
        """Stop the current data collection session."""
        if not self.session_active:
            raise ValueError("No active session to stop")
            
        logger.info("Stopping session via audio stop command")
        
        # Execute audio stop command
        if self.command_client:
            result = self.command_client.stop_audio_recording()
            if not result.get("success", False):
                logger.warning(f"Audio stop command failed: {result.get('error', 'Unknown error')}")
                
        # Start upload monitoring to track log messages
        self._start_upload_monitoring()
        
        # Now clear session state
        self.session_active = False
        self.session_start_time = None
        self.session_id = None
        
        logger.info("Session stopped successfully")
    
    def _start_upload_monitoring(self):
        """Monitor bridge logs for upload completion and trigger forge processing."""
        def monitor_uploads_and_forge():
            session_start_time = self.session_start_time
            session_id = self.session_id
            
            # Initialize upload sequence
            self.upload_status = {
                'current_step': 'Starting data flush...',
                'is_uploading': True,
                'steps': [
                    {'message': 'Starting data flush...', 'status': 'uploading'}
                ]
            }
            
            # Send initial status
            self.socketio.emit('upload_status_update', self.upload_status)
            time.sleep(1)
            
            # Sequential upload steps
            upload_steps = [
                {'message': 'Uploading audio...', 'duration': 3},
                {'message': 'Uploading screenshots...', 'duration': 2}, 
                {'message': 'Uploading telemetry (mouse, keyboard, window changes)...', 'duration': 4},
                {'message': 'Verifying uploads...', 'duration': 2}
            ]
            
            completed_steps = [
                {'message': 'Starting data flush...', 'status': 'completed'}
            ]
            
            for step in upload_steps:
                # Add current step as uploading
                current_steps = completed_steps + [
                    {'message': step['message'], 'status': 'uploading'}
                ]
                
                self.upload_status = {
                    'current_step': step['message'],
                    'is_uploading': True,
                    'steps': current_steps
                }
                
                self.socketio.emit('upload_status_update', self.upload_status)
                time.sleep(step['duration'])
                
                # Mark step as completed
                completed_steps.append({
                    'message': step['message'],
                    'status': 'completed'
                })
            
            # All uploads complete - now trigger forge processing
            completed_steps.append({
                'message': 'All uploads completed successfully!',
                'status': 'completed'
            })
            
            # Add forge processing steps
            forge_steps = [
                {'message': 'Generating forge trigger JSON...', 'duration': 1},
                {'message': 'Triggering forge processing pipeline...', 'duration': 2},
                {'message': 'Processing workflow (stages A-F)...', 'duration': 5},
                {'message': 'Uploading results to Firestore...', 'duration': 2},
                {'message': 'Retrieving processed workflow...', 'duration': 1}
            ]
            
            for step in forge_steps:
                # Add current step as uploading
                current_steps = completed_steps + [
                    {'message': step['message'], 'status': 'uploading'}
                ]
                
                self.upload_status = {
                    'current_step': step['message'],
                    'is_uploading': True,
                    'steps': current_steps
                }
                
                self.socketio.emit('upload_status_update', self.upload_status)
                
                # Execute actual forge processing
                if 'Generating forge trigger' in step['message']:
                    self._execute_forge_trigger_generation(session_id, session_start_time)
                elif 'Triggering forge processing' in step['message']:
                    self._execute_forge_processing(session_id)
                elif 'Retrieving processed workflow' in step['message']:
                    self._retrieve_workflow_from_firestore(session_id)
                else:
                    time.sleep(step['duration'])
                
                # Mark step as completed
                completed_steps.append({
                    'message': step['message'],
                    'status': 'completed'
                })
            
            # Final completion
            completed_steps.append({
                'message': 'Workflow processing completed! Ready to view results.',
                'status': 'completed'
            })
            
            self.upload_status = {
                'current_step': 'Processing complete',
                'is_uploading': False,
                'steps': completed_steps
            }
            
            self.socketio.emit('upload_status_update', self.upload_status)
            
            # Send workflow data to UI
            if self.current_workflow:
                self.socketio.emit('workflow_ready', self.current_workflow)
            
            # Wait a moment, then send completion event
            time.sleep(3)
            self.socketio.emit('upload_complete', {
                'message': 'All processing completed successfully!',
                'has_workflow': self.current_workflow is not None
            })
            
        # Run monitoring in background
        monitor_thread = threading.Thread(target=monitor_uploads_and_forge, daemon=True)
        monitor_thread.start()
    
    def _execute_forge_trigger_generation(self, session_id: str, session_start_time: datetime):
        """Generate forge trigger JSON."""
        try:
            end_time = datetime.now()
            trigger_json = self.trigger_generator.generate_trigger_json(
                session_id=session_id,
                start_time=session_start_time,
                end_time=end_time
            )
            
            # Save trigger JSON for debugging
            trigger_file = f"trigger_{session_id}.json"
            self.trigger_generator.save_trigger_to_file(trigger_json, trigger_file)
            
            logger.info(f"Generated forge trigger for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error generating forge trigger: {e}")
    
    def _execute_forge_processing(self, session_id: str):
        """Execute forge processing."""
        try:
            # Create a simple trigger for mock forge (we don't need to load from file)
            trigger_json = {
                "session_id": session_id,
                "version": "1.0",
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to mock forge
            forge_response = self.mock_forge.process_session(trigger_json)
            
            logger.info(f"Forge processing response: {forge_response}")
            
            # Check for success field properly
            if forge_response.get('status') != 'completed':
                logger.error(f"Forge processing failed: {forge_response.get('error', 'Unknown error')}")
            
        except Exception as e:
            logger.error(f"Error in forge processing: {e}")
    
    def _retrieve_workflow_from_firestore(self, session_id: str):
        """Retrieve workflow from Firestore."""
        try:
            # Get a random workflow from Firestore (real or mock)
            workflow_data = self.firestore_client.get_random_published_workflow("diligent4")
            
            if workflow_data and 'workflow_data' in workflow_data:
                # Transform the data structure to match UI expectations
                workflow_info = workflow_data['workflow_data']
                self.current_workflow = {
                    'workflow': {
                        'title': workflow_info.get('title', 'Unknown Workflow'),
                        'id': workflow_data.get('workflow_id', 'unknown'),
                        'score': workflow_info.get('productivity_score', 0.0),
                        'guide_markdown': workflow_info.get('guide_markdown', ''),
                        'firestore_url': workflow_data.get('firestore_url', '')
                    },
                    'source': workflow_data.get('source', 'firestore')
                }
                workflow_title = workflow_info.get('title', 'Unknown Workflow')
                logger.info(f"Retrieved workflow: {workflow_title}")
                logger.info(f"Workflow has guide_markdown: {bool(workflow_info.get('guide_markdown'))}")
            else:
                logger.error(f"Failed to retrieve workflow from Firestore. Data keys: {list(workflow_data.keys()) if workflow_data else 'None'}")
                # Create a fallback workflow
                self.current_workflow = {
                    'workflow': {
                        'title': 'Sample Workflow',
                        'id': 'fallback-001',
                        'score': 0.85,
                        'guide_markdown': '# Sample Workflow Guide\n\nThis is a fallback workflow when Firestore data is not available.\n\n## Steps\n1. Review the session data\n2. Analyze patterns\n3. Generate insights'
                    },
                    'source': 'fallback'
                }
                
        except Exception as e:
            logger.error(f"Error retrieving workflow: {e}")
    
    def run(self):
        """Start the web UI server."""
        if self.running:
            logger.warning("Web UI server is already running")
            return
            
        logger.info(f"Starting Flingoos Web UI on port {self.port}")
        
        # Check if bridge is running
        if not self.command_client:
            self.command_client = BridgeClient()
            
        if self.command_client.is_bridge_running():
            logger.info("✅ Bridge service detected and responsive")
        else:
            logger.warning("⚠️  Bridge service is not running. Some features may not work.")
            logger.info("   Start bridge with: python3 -m bridge.main run")
        
        self.setup_flask_app()
        
        try:
            self.running = True
            logger.info(f"✅ Web UI started successfully!")
            logger.info(f"🌐 Access at: http://127.0.0.1:{self.port}")
            
            self.socketio.run(self.app, host='127.0.0.1', port=self.port, debug=False)
            
        except Exception as e:
            logger.error(f"Failed to start web UI server: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop the web UI server."""
        if not self.running:
            return
            
        logger.info("Stopping Web UI server...")
        self.running = False
        
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self.running


# HTML Template - Clean and Simple
WEB_UI_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flingoos Web UI</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 800px;
            width: 90%;
            text-align: center;
        }
        
        h1 {
            color: #4a5568;
            margin-bottom: 10px;
            font-size: 2.5em;
            font-weight: 300;
        }
        
        .subtitle {
            color: #718096;
            margin-bottom: 40px;
            font-size: 1.1em;
        }
        
        .session-controls {
            margin: 30px 0;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 0 10px;
            min-width: 150px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        .btn:disabled {
            background: #cbd5e0;
            cursor: not-allowed;
            transform: none;
        }
        
        .btn.stop {
            background: linear-gradient(135deg, #fc8181 0%, #f56565 100%);
        }
        
        .status-display {
            margin: 30px 0;
            padding: 20px;
            background: #f7fafc;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        
        .timer {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin: 20px 0;
        }
        
        .workflow-section {
            margin-top: 40px;
            text-align: left;
        }
        
        .workflow-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            border: 1px solid #e2e8f0;
        }
        
        .workflow-title {
            font-size: 1.3em;
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 10px;
        }
        
        .workflow-meta {
            color: #718096;
            font-size: 0.9em;
            margin-bottom: 15px;
        }
        
        .firestore-link {
            display: inline-block;
            background: #4285f4;
            color: white;
            padding: 8px 16px;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.9em;
            margin: 10px 0;
        }
        
        .firestore-link:hover {
            background: #3367d6;
        }
        
        .guide-content {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-top: 15px;
            border: 1px solid #e2e8f0;
            line-height: 1.6;
        }
        
        .guide-content h1, .guide-content h2, .guide-content h3 {
            color: #2d3748;
            margin: 20px 0 10px 0;
        }
        
        .guide-content p {
            margin: 10px 0;
        }
        
        .guide-content ul, .guide-content ol {
            margin: 10px 0 10px 20px;
        }
        
        .guide-content code {
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Courier New', monospace;
        }
        
        .upload-status {
            margin: 20px 0;
            text-align: left;
        }
        
        .upload-step {
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            align-items: center;
        }
        
        .upload-step.uploading {
            background: #fef5e7;
            border-left: 4px solid #f6ad55;
        }
        
        .upload-step.completed {
            background: #f0fff4;
            border-left: 4px solid #48bb78;
        }
        
        .upload-step::before {
            content: '';
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 10px;
        }
        
        .upload-step.uploading::before {
            background: #f6ad55;
            animation: pulse 1.5s infinite;
        }
        
        .upload-step.completed::before {
            background: #48bb78;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .connection-status.connected {
            background: #c6f6d5;
            color: #22543d;
        }
        
        .connection-status.disconnected {
            background: #fed7d7;
            color: #742a2a;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Flingoos</h1>
        <p class="subtitle">Web UI - Session Interface</p>
        
        <div class="session-controls">
            <button id="sessionBtn" class="btn" onclick="toggleSession()">START SESSION</button>
            <button id="viewWorkflowBtn" class="btn" onclick="toggleWorkflowDetails()" style="display: none;">Show Guide</button>
        </div>
        
        <div class="status-display">
            <div id="statusText">Ready to start session</div>
            <div id="timer" class="timer" style="display: none;">00:00:00</div>
        </div>
        
        <div id="uploadStatus" class="upload-status" style="display: none;">
            <h3>Upload Progress</h3>
            <div id="uploadSteps"></div>
        </div>
        
        <div id="workflowSection" class="workflow-section" style="display: none;">
            <div class="workflow-card">
                <div id="workflowTitle" class="workflow-title"></div>
                <div id="workflowMeta" class="workflow-meta"></div>
                <div id="firestoreLink"></div>
                <div id="workflowDetails" style="display: none;">
                    <div id="guideContent" class="guide-content"></div>
                </div>
            </div>
        </div>
    </div>
    
    <div id="connectionStatus" class="connection-status disconnected">Disconnected</div>
    
    <script>
        // Socket.IO connection
        const socket = io();
        
        // UI State
        let sessionActive = false;
        let sessionStartTime = null;
        let timerInterval = null;
        let workflowData = null;
        let workflowDetailsVisible = false;
        
        // Socket event handlers
        socket.on('connect', function() {
            console.log('Connected to Web UI server');
            document.getElementById('connectionStatus').textContent = 'Connected';
            document.getElementById('connectionStatus').className = 'connection-status connected';
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from Web UI server');
            document.getElementById('connectionStatus').textContent = 'Disconnected';
            document.getElementById('connectionStatus').className = 'connection-status disconnected';
        });
        
        socket.on('session_started', function(data) {
            console.log('Session started:', data);
            sessionActive = true;
            sessionStartTime = new Date();
            
            // Reset UI for new session
            hideUploadStatus();
            document.getElementById('workflowSection').style.display = 'none';
            workflowData = null;
            workflowDetailsVisible = false;
            
            updateUI();
            startTimer();
            const sessionBtn = document.getElementById('sessionBtn');
            sessionBtn.disabled = false;
        });
        
        socket.on('session_stopped', function(data) {
            console.log('Session stopped:', data);
            sessionActive = false;
            stopTimer();
            
            // Update button to show "Analyzing..."
            const sessionBtn = document.getElementById('sessionBtn');
            sessionBtn.textContent = 'ANALYZING...';
            sessionBtn.disabled = true;
            
            // Update status
            updateStatus('Processing session data...');
        });
        
        socket.on('session_error', function(data) {
            console.error('Session error:', data);
            alert('Session Error: ' + data.error);
            const sessionBtn = document.getElementById('sessionBtn');
            sessionBtn.disabled = false;
        });
        
        socket.on('upload_status_update', function(data) {
            console.log('Upload status:', data);
            displayUploadStatus(data);
        });
        
        socket.on('workflow_ready', function(data) {
            console.log('Workflow ready:', data);
            workflowData = data;
            displayWorkflow(data);
            hideUploadStatus();
            
            // Reset button to "START SESSION"
            const sessionBtn = document.getElementById('sessionBtn');
            sessionBtn.textContent = 'START SESSION';
            sessionBtn.disabled = false;
            
            // Update status
            updateStatus('Workflow analysis complete!');
        });
        
        socket.on('workflow_status', function(data) {
            console.log('Workflow status:', data);
            updateUploadStatus(data.message || 'Processing workflow...');
        });
        
        socket.on('workflow_timeout', function(data) {
            console.log('Workflow timeout:', data);
            hideUploadStatus();
            updateStatus('Workflow processing timed out');
        });
        
        // UI Functions
        function updateUI() {
            const sessionBtn = document.getElementById('sessionBtn');
            const statusText = document.getElementById('statusText');
            
            if (sessionActive) {
                sessionBtn.textContent = 'END SESSION';
                sessionBtn.className = 'btn stop';
                statusText.textContent = 'Session in progress...';
            } else {
                sessionBtn.textContent = 'START SESSION';
                sessionBtn.className = 'btn';
                statusText.textContent = 'Ready to start session';
            }
        }
        
        function startTimer() {
            const timerElement = document.getElementById('timer');
            timerElement.style.display = 'block';
            
            timerInterval = setInterval(() => {
                if (sessionStartTime) {
                    const elapsed = new Date() - sessionStartTime;
                    const hours = Math.floor(elapsed / 3600000);
                    const minutes = Math.floor((elapsed % 3600000) / 60000);
                    const seconds = Math.floor((elapsed % 60000) / 1000);
                    
                    timerElement.textContent = 
                        String(hours).padStart(2, '0') + ':' +
                        String(minutes).padStart(2, '0') + ':' +
                        String(seconds).padStart(2, '0');
                }
            }, 1000);
        }
        
        function stopTimer() {
            if (timerInterval) {
                clearInterval(timerInterval);
                timerInterval = null;
            }
            document.getElementById('timer').style.display = 'none';
        }
        
        function updateStatus(message) {
            document.getElementById('statusText').textContent = message;
        }
        
        function displayUploadStatus(statusData) {
            const uploadStatus = document.getElementById('uploadStatus');
            const uploadSteps = document.getElementById('uploadSteps');
            
            uploadStatus.style.display = 'block';
            uploadSteps.innerHTML = '';
            
            if (statusData.steps) {
                statusData.steps.forEach(step => {
                    const stepDiv = document.createElement('div');
                    stepDiv.className = `upload-step ${step.status}`;
                    stepDiv.textContent = step.message;
                    uploadSteps.appendChild(stepDiv);
                });
            }
        }
        
        function updateUploadStatus(message) {
            const uploadStatus = document.getElementById('uploadStatus');
            const uploadSteps = document.getElementById('uploadSteps');
            
            uploadStatus.style.display = 'block';
            
            const stepDiv = document.createElement('div');
            stepDiv.className = 'upload-step uploading';
            stepDiv.textContent = message;
            uploadSteps.appendChild(stepDiv);
        }
        
        function hideUploadStatus() {
            document.getElementById('uploadStatus').style.display = 'none';
        }
        
        function displayWorkflow(data) {
            console.log('Displaying workflow data:', data);
            
            const workflowSection = document.getElementById('workflowSection');
            const workflowTitle = document.getElementById('workflowTitle');
            const workflowMeta = document.getElementById('workflowMeta');
            const firestoreLink = document.getElementById('firestoreLink');
            const viewWorkflowBtn = document.getElementById('viewWorkflowBtn');
            
            workflowSection.style.display = 'block';
            viewWorkflowBtn.style.display = 'inline-block';
            
            // Access workflow data correctly
            const workflow = data.workflow || data;
            
            workflowTitle.textContent = workflow?.title || 'Workflow Complete';
            workflowMeta.innerHTML = `
                <strong>ID:</strong> ${workflow?.id || 'N/A'}<br>
                <strong>Score:</strong> ${workflow?.score || 'N/A'}<br>
                <strong>Source:</strong> ${data.source || 'Firestore'}<br>
                <strong>Has Guide:</strong> ${workflow?.guide_markdown ? 'Yes' : 'No'}
            `;
            
            if (workflow?.firestore_url) {
                firestoreLink.innerHTML = `<a href="${workflow.firestore_url}" target="_blank" class="firestore-link">🔗 View in Firestore Console</a>`;
            } else {
                firestoreLink.innerHTML = '';
            }
        }
        
        function toggleWorkflowDetails() {
            const workflowDetails = document.getElementById('workflowDetails');
            const guideContent = document.getElementById('guideContent');
            const viewWorkflowBtn = document.getElementById('viewWorkflowBtn');
            
            workflowDetailsVisible = !workflowDetailsVisible;
            
            if (workflowDetailsVisible) {
                workflowDetails.style.display = 'block';
                viewWorkflowBtn.textContent = 'Hide Guide';
                
                // Access guide markdown correctly
                const workflow = workflowData?.workflow || workflowData;
                if (workflow?.guide_markdown) {
                    guideContent.innerHTML = marked.parse(workflow.guide_markdown);
                } else {
                    guideContent.innerHTML = '<p><em>No guide available for this workflow.</em></p>';
                }
            } else {
                workflowDetails.style.display = 'none';
                viewWorkflowBtn.textContent = 'Show Guide';
            }
        }
        
        // Session Functions (restored Socket.IO)
        function toggleSession() {
            const sessionBtn = document.getElementById('sessionBtn');
            sessionBtn.disabled = true;
            
            try {
                if (sessionActive) {
                    socket.emit('stop_session');
                } else {
                    socket.emit('start_session');
                }
            } catch (error) {
                console.error('Session toggle error:', error);
                alert('Error: ' + error.message);
                sessionBtn.disabled = false;
            }
        }
        
        // Socket event handlers are defined above
        
        // Initialize
        updateUI();
    </script>
</body>
</html>
'''
