#!/bin/bash

# Debug Script for Phonox Loading Issues

echo "🔍 Phonox Debug Script"
echo "====================="
echo ""

# Check if containers are running
echo "📋 Container Status:"
docker-compose ps

echo ""
echo "🌐 Network Connectivity:"
echo "Frontend: http://localhost:5173"
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:5173

echo "Backend: http://localhost:8000"  
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8000

echo ""
echo "🧭 Manual Debugging Steps:"
echo "1. Open http://localhost:5173 in browser"
echo "2. Press F12 to open DevTools"
echo "3. Check Console tab for JavaScript errors"
echo "4. Check Network tab for failed requests"
echo "5. If page is blank, check if UserManager modal is blocking"
echo ""

echo "📱 Mobile Access (if configured):"
IP=$(hostname -I | awk '{print $1}')
echo "Try: http://$IP:5173"
echo ""

echo "🔧 Quick Fixes:"
echo "• Hard refresh: Ctrl+Shift+R"
echo "• Clear service worker in DevTools > Application"
echo "• Try incognito mode"
echo "• Check browser console for errors"