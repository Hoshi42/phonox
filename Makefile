.PHONY: help docker-up docker-down docker-logs docker-test docker-shell-backend docker-shell-frontend docker-rebuild docker-clean docker-status

help:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║           Phonox Docker - Available Commands              ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 Getting Started:"
	@echo "  make docker-up              Start all services"
	@echo "  make docker-down            Stop all services"
	@echo "  make docker-rebuild         Rebuild and start services"
	@echo "  make docker-status          Show service status"
	@echo ""
	@echo "📋 Logs & Monitoring:"
	@echo "  make docker-logs            View all logs"
	@echo "  make docker-logs-backend    View backend logs"
	@echo "  make docker-logs-frontend   View frontend logs"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make docker-test            Run all backend tests"
	@echo "  make docker-test-type       Run mypy type checking"
	@echo "  make docker-test-e2e        Run frontend E2E tests"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make docker-shell-backend   Access backend shell"
	@echo "  make docker-shell-frontend  Access frontend shell"
	@echo "  make docker-clean           Remove all containers & volumes"
	@echo ""

# Docker Compose shortcuts
docker-up:
	docker-compose up -d
	@echo "✅ Services started!"
	@echo "   Backend:  http://localhost:8000"
	@echo "   Frontend: http://localhost:5173"

docker-down:
	docker-compose down
	@echo "✅ Services stopped"

docker-rebuild:
	docker-compose down
	docker-compose up -d --build
	@echo "✅ Services rebuilt and started"
	@echo "   Backend:  http://localhost:8000"
	@echo "   Frontend: http://localhost:5173"

docker-status:
	@echo "🐳 Docker Containers Status:"
	@docker-compose ps
	@echo ""
	@echo "🌐 Service URLs:"
	@echo "   Backend:  http://localhost:8000"
	@echo "   Frontend: http://localhost:5173"
	@echo "   API Docs: http://localhost:8000/docs"
	@echo "   Health:   http://localhost:8000/health"

docker-logs:
	docker-compose logs -f

docker-logs-backend:
	docker-compose logs -f backend

docker-logs-frontend:
	docker-compose logs -f frontend

# Testing
docker-test:
	docker-compose exec backend python -m pytest tests/ -v

docker-test-type:
	docker-compose exec backend mypy backend/

docker-test-e2e:
	docker-compose exec frontend npm run test:e2e

# Shell Access
docker-shell-backend:
	docker-compose exec backend bash

docker-shell-frontend:
	docker-compose exec frontend sh

# Cleanup
docker-clean:
	docker-compose down -v
	docker system prune -a --volumes -f
	@echo "✅ All containers and volumes removed"

# Useful combinations
docker-quick-test:
	@echo "Running backend tests..."
	docker-compose exec backend python -m pytest tests/ -v
	@echo ""
	@echo "Running type check..."
	docker-compose exec backend mypy backend/

docker-dev-shell:
	@echo "Select shell to open:"
	@echo "1) Backend (bash)"
	@echo "2) Frontend (sh)"
	@read choice; \
	if [ "$$choice" = "1" ]; then \
		docker-compose exec backend bash; \
	elif [ "$$choice" = "2" ]; then \
		docker-compose exec frontend sh; \
	fi
