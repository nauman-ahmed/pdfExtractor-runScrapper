@echo off
setlocal

echo ⚙️  Creating virtual environment...
python -m venv env

echo 📦 Activating virtual environment...
call env\Scripts\activate.bat

echo 📚 Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo 🚀 Starting FastAPI server in a new terminal window...
start "FastAPI Server" cmd /k "uvicorn main:app --host 127.0.0.1 --port 8000"

echo ⏳ Waiting for FastAPI server to start...
timeout /t 5 /nobreak > NUL

echo 🔍 Running scraper...
python run_scraper.py

echo ✅ All done!
pause
