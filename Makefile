# Building Generator - Makefile
# Simplified for a clean and robust development workflow

.PHONY: dev backend frontend setup clean help stop

# Default target: Show help
help:
	@echo "Building Generator - Makefile Commands"
	@echo ""
	@echo "  make dev      - Run frontend and backend for development (RECOMMENDED)"
	@echo "  make backend  - Run only backend (FastAPI)"
	@echo "  make frontend - Run only frontend (Next.js)"
	@echo "  make stop     - Stop all processes and clear dev cache for a clean restart"
	@echo "  make setup    - Install all dependencies for frontend and backend"
	@echo "  make clean    - Remove ALL temporary files, logs, and dependencies"

# Run both frontend and backend concurrently
dev:
	@echo "Starting development servers..."
	@echo "Backend logs will be written to service/log/info.log and service/log/error.log"
	@echo "Combined output will be shown below."
	@npx concurrently \
		-n "BACKEND,FRONTEND" \
		-c "blue,green" \
		"cd service && bash -c 'source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'" \
		"npm run dev"

# Stop all development processes and clear the Next.js cache/lock
stop:
	@echo "Stopping development servers..."

	# Ensure Uvicorn backend is stopped
	@pkill -f "uvicorn.*app.main:app.*8000"

	# Ensure Next.js frontend is stopped
	@pkill -f "next.*dev"

	@echo "[OK] Development servers stopped."
	@echo "Cleaning up Next.js build cache..."
	@rm -rf .next
	@echo "[OK] Cleanup complete. Ready for a fresh start."

# Run only backend
backend:
	@echo "Starting backend on http://localhost:8000..."
	@cd service && bash -c "source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"

# Run only frontend
frontend:
	@echo "Starting frontend on http://localhost:3000..."
	@npm run dev

# Setup all dependencies
setup:
	@echo "Checking for system dependencies..."
	@if ! dpkg -s libldap2-dev >/dev/null 2>&1 || ! dpkg -s libsasl2-dev >/dev/null 2>&1; then \
		echo "ERROR: Missing system dependencies required for build."; \
		echo "Please run the following command to install them:"; \
		echo "sudo apt-get update && sudo apt-get install -y libldap2-dev libsasl2-dev"; \
		exit 1; \
	fi
	@echo "[OK] System dependencies found."
	@echo "Setting up backend dependencies..."
	@cd service && python3 -m venv venv && bash -c 'source venv/bin/activate && pip install -r requirements.txt'
	@echo "Setting up frontend dependencies..."
	@npm install
	@echo "Setup complete!"

# Clean temporary files, logs, and dependencies
clean:
	@echo "Cleaning project..."
	@make stop 2>/dev/null || true
	@echo "Removing backend and frontend dependencies..."
	@rm -rf service/venv
	@rm -rf node_modules
	@echo "Removing logs and outputs..."
	@rm -rf service/outputs/*
	@rm -rf service/log
	@echo "[OK] Clean complete!"
