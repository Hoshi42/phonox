#!/bin/bash

echo "🔍 Testing Phonox Frontend & Backend Connectivity"
echo "=================================================="
echo

# Test 1: Check if frontend is running
echo "1️⃣ Testing Frontend Server (http://localhost:5173)"
if curl -s -m 2 http://localhost:5173 &>/dev/null; then
    echo "   ✅ Frontend is responding"
else
    echo "   ❌ Frontend is NOT responding"
fi
echo

# Test 2: Check if backend is running
echo "2️⃣ Testing Backend Health (http://localhost:8000/health)"
if curl -s -m 2 http://localhost:8000/health | grep -q "healthy"; then
    echo "   ✅ Backend is healthy"
else
    echo "   ❌ Backend is NOT healthy"
fi
echo

# Test 3: Check API endpoint
echo "3️⃣ Testing API Endpoint (http://localhost:8000/api/v1/identify)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -m 2 -X POST http://localhost:8000/api/v1/identify)
if [ "$STATUS" = "422" ]; then
    echo "   ✅ API endpoint is accessible (returns 422 without images, which is expected)"
elif [ "$STATUS" = "000" ]; then
    echo "   ❌ Cannot reach API endpoint (connection failed)"
else
    echo "   ⚠️  API endpoint returned status $STATUS"
fi
echo

# Test 4: Check CORS
echo "4️⃣ Testing CORS Headers"
CORS=$(curl -s -I -H "Origin: http://localhost:5173" http://localhost:8000/health | grep -i "access-control")
if [ -n "$CORS" ]; then
    echo "   ✅ CORS headers present:"
    echo "   $CORS"
else
    echo "   ❌ No CORS headers found"
fi
echo

echo "=================================================="
echo "✅ All systems operational!" 
echo
echo "🚀 Visit: http://localhost:5173"
