# Quick Start Guide - Running Rocket

## ✅ Prerequisites Completed
- ✅ `.env` file created with POLLINATIONS_API_KEY
- ✅ Virtual environment exists at `.venv`
- ✅ Startup scripts created

## 🚀 Running Both Backend and Frontend

### Option 1: Run Everything at Once (Easiest)
Double-click on: **`START_ALL.bat`**

This will open two command windows:
- **Rocket Backend** - Python WebSocket server on ws://0.0.0.0:8765
- **Rocket Frontend** - Flutter mobile app

### Option 2: Run Separately

#### Backend Only:
Double-click on: **`start_backend.bat`**
- Starts the Python backend server
- Runs on ws://0.0.0.0:8765
- Keep this window open while using the app

#### Frontend Only:
Double-click on: **`start_frontend.bat`**
- Installs Flutter dependencies
- Launches the mobile app
- Choose your target device (iOS simulator, Android emulator, or physical device)

## 📋 First Time Setup

If this is your first time running, you may need to:

1. **Install Python dependencies** (if not done):
   ```bash
   .venv\Scripts\activate.bat
   pip install -r requirements.txt
   ```

2. **Install Flutter dependencies**:
   ```bash
   cd mobile_app
   flutter pub get
   ```

## 🔍 Troubleshooting

### Backend Issues
- **"Virtual environment not found"**: Run `python -m venv .venv`
- **"No module named 'agent'"**: Make sure PYTHONPATH is set (the script does this automatically)
- **"POLLINATIONS_API_KEY is required"**: Check that `.env` file exists with the key

### Frontend Issues
- **"Flutter not found"**: Install Flutter from https://flutter.dev
- **"No devices found"**: Connect a device or start an emulator
- **Dependencies fail**: Run `flutter doctor` to check your setup

## 📱 Connecting Mobile App to Backend

1. Start the backend first (it will show a QR code)
2. Start the Flutter app
3. Scan the QR code shown by the backend
4. The app will connect to your PC via WebSocket

## 🛑 Stopping the Servers

Press **Ctrl+C** in each command window to stop the respective server.

## 📝 Manual Commands

If you prefer to run manually in your own terminal:

**Backend:**
```bash
cd "c:\Users\Prahan\Myoffice\Patent Project\TheRocketProject\rocket"
set PYTHONPATH=%CD%
.venv\Scripts\activate.bat
python agent\main.py --host 0.0.0.0 --port 8765
```

**Frontend:**
```bash
cd "c:\Users\Prahan\Myoffice\Patent Project\TheRocketProject\rocket\mobile_app"
flutter pub get
flutter run
```

## 📞 Need Help?

- Check the main README.md for full documentation
- See logs in the backend window for error messages
- Ensure your firewall allows WebSocket connections on port 8765
