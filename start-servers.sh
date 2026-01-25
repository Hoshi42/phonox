#!/bin/bash

echo "🚀 Starting Phonox Servers"
echo "=========================="

# Kill any existing processes
pkill -f "uvicorn|vite|npm run dev" 2>/dev/null

echo "⏳ Waiting for previous processes to terminate..."
sleep 2

# Start backend
echo "📚 Starting Backend (uvicorn)..."
cd /home/hoshhie/phonox
python -m uvicorn backend.main:app --reload --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Start frontend
echo "🎨 Starting Frontend (Vite)..."
cd /home/hoshhie/phonox/frontend
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

sleep 3

echo
echo "✅ Servers started!"
echo "📊 Backend:  http://localhost:8000"
echo "🎨 Frontend: http://localhost:5173"
echo
echo "📋 Logs:"
echo "   Backend:  tail -f /tmp/backend.log"
echo "   Frontend: tail -f /tmp/frontend.log"
