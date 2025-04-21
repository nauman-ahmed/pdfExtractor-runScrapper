#!/bin/bash

echo "⚙️  Creating virtual environment..."
python3 -m venv env

echo "📦 Activating virtual environment..."
source env/bin/activate

echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🚀 Starting FastAPI server in the background..."
uvicorn main:app --host 127.0.0.1 --port 8000 &

# Save the PID so we can kill the server later
SERVER_PID=$!

echo "⏳ Waiting for FastAPI server to start..."
sleep 5

echo "🔍 Running scraper..."
python run_scraper.py

echo "🧹 Shutting down FastAPI server..."
kill $SERVER_PID

echo "✅ Done."
