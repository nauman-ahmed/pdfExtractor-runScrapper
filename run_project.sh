echo "📦 Activating virtual environment..."
source env/bin/activate

echo "🚀 Starting FastAPI server in the background..."
uvicorn main:app --host 127.0.0.1 --port 8000 &

echo "⏳ Waiting for FastAPI server to start..."
sleep 5

echo "🔍 Running scraper..."
python run_scraper.py

echo "✅ Done."
