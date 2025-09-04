# Flingoos Web UI

**Pure Web Interface - No Business Logic**

A clean, modern web interface that provides the user-facing layer for Flingoos session management.

## 🎯 **Purpose**

This component is **ONLY** responsible for:
- ✅ Serving HTML/CSS/JS to browsers
- ✅ Handling user interactions (buttons, forms)
- ✅ Real-time UI updates via Socket.IO
- ✅ Communicating with Session Manager API

This component is **NOT** responsible for:
- ❌ Session business logic
- ❌ Bridge communication
- ❌ Forge integration
- ❌ Data processing

## 🏗️ **Architecture**

```
Browser ←→ Web UI Server ←→ Session Manager API
                           ↓
                      Bridge Service
```

## 🚀 **Quick Start**

### Prerequisites
- Python 3.8+
- Session Manager running on port 8845

### Installation
```bash
cd flingoos-web-ui
pip install -r requirements.txt
```

### Run
```bash
python run_web_ui.py
```

Access at: http://127.0.0.1:8844

### Options
```bash
python run_web_ui.py --port 8844 --session-manager-url http://localhost:8845
```

## 📡 **API Communication**

The Web UI communicates with the Session Manager via HTTP:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/session/start` | POST | Start new session |
| `/api/session/{id}/stop` | POST | Stop session |
| `/api/session/status` | GET | Get status |
| `/api/session/{id}/workflow` | GET | Get workflow result |

## 🔄 **Real-time Updates**

Uses Socket.IO for real-time updates:
- Session status changes
- Upload progress
- Workflow completion
- Connection status

## 🎨 **Features**

- **Modern UI**: Clean, responsive design
- **Real-time Timer**: Session duration tracking
- **Upload Progress**: Visual upload status
- **Workflow Display**: Markdown-rendered guides
- **Connection Status**: Live connection indicator
- **Error Handling**: User-friendly error messages

## 🔧 **Configuration**

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PORT` | 8844 | Web UI port |
| `SESSION_MANAGER_URL` | http://localhost:8845 | Session Manager API URL |

## 📝 **Future**

This Web UI will eventually be integrated into the existing Diligent4 dashboard website, replacing this standalone component.
