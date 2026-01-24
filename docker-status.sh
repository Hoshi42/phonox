#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       PHONOX DOCKER SETUP - COMPLETE & RUNNING ✅           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo

echo "🚀 SERVICES RUNNING:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker-compose ps
echo

echo "📊 BACKEND API:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🏥 Health:    http://localhost:8000/health"
echo "  📚 Docs:      http://localhost:8000/docs"
echo "  🔄 API:       http://localhost:8000/api/v1/identify"
echo

echo "🎨 FRONTEND:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🌐 App:       http://localhost:5173"
echo

echo "📋 COMMON COMMANDS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  View logs:               docker-compose logs -f"
echo "  Backend logs:            docker-compose logs -f backend"
echo "  Frontend logs:           docker-compose logs -f frontend"
echo "  Backend tests:           docker-compose exec backend python -m pytest tests/ -v"
echo "  Backend shell:           docker-compose exec backend bash"
echo "  Frontend shell:          docker-compose exec frontend sh"
echo "  Stop all:                docker-compose down"
echo "  Rebuild & start:         docker-compose up -d --build"
echo

echo "⚙️ ENVIRONMENT:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Docker version:          $(docker --version)"
echo "  Docker Compose version:  $(docker-compose --version)"
echo "  Network:                 phonox_phonox_network (bridge)"
echo

echo "📁 MOUNTED VOLUMES:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Backend:"
echo "    • ./backend → /app/backend (hot reload)"
echo "    • ./phonox.db → /app/phonox.db (persistent)"
echo "    • ./tests → /app/tests"
echo "  Frontend:"
echo "    • ./frontend → /app (hot reload)"
echo "    • /app/node_modules (shared in container)"
echo

echo "✨ NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. Open http://localhost:5173 in your browser"
echo "  2. Upload vinyl record images for identification"
echo "  3. Check backend logs: docker-compose logs -f backend"
echo "  4. Run tests: docker-compose exec backend python -m pytest tests/ -v"
echo "  5. View API docs: http://localhost:8000/docs"
echo

echo "💡 HOT RELOAD:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  • Edit backend code in ./backend → automatic reload"
echo "  • Edit frontend code in ./frontend → automatic hot reload"
echo "  • No container restart needed!"
echo

echo "📖 DOCUMENTATION:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  See DOCKER_SETUP.md for comprehensive documentation"
echo
