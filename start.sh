#!/bin/bash

echo "Starting Narrator AI..."

# Start Python FastAPI backend in background
echo "Starting Python backend on port 8000..."
cd backend
python main.py &
PYTHON_PID=$!

# Wait for Python backend to be ready
echo "Waiting for backend to start..."
sleep 2

# Go back to root and start Node.js frontend
cd ..
echo "Starting Node.js frontend on port 5000..."
npm run dev &
NODE_PID=$!

# Handle cleanup on exit
cleanup() {
    echo "Shutting down..."
    kill $PYTHON_PID 2>/dev/null
    kill $NODE_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
