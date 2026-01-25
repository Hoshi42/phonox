#!/bin/bash
set -euo pipefail

echo "🛑 Stopping local dev servers (if any)..."
pkill -f "uvicorn|vite|npm run dev" 2>/dev/null || true

echo "🐳 Starting Docker containers..."
cd /home/hoshhie/phonox

docker-compose up -d --build

echo "✅ Docker containers started."
echo "📊 Backend:  http://localhost:8000"
echo "🎨 Frontend: http://localhost:5173"
