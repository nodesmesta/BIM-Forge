#!/bin/bash
# BIM Quality Guardian - Comprehensive Health Check
# Part of bim-quality-guardian skill

cd /root/Arsitektur/service
source venv/bin/activate

LOG_FILE="/root/Arsitektur/service/log/guardian.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================"
log "BIM Quality Guardian - Starting Check"
log "========================================"

# 1. SERVICE HEALTH CHECK
log "Step 1: Checking service health..."

FRONTEND=$(curl -s -o /dev/null -w "%{http_code}" https://bim.nodesemesta.com)
BACKEND=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)

log "  Frontend: $FRONTEND"
log "  Backend: $BACKEND"

# 2. API FUNCTIONAL TEST
log "Step 2: Running API functional tests..."
python3 /root/Arsitektur/service/scripts/test_api.py --json 2>/dev/null | tail -1

# 3. CHECK RECENT GENERATIONS
log "Step 3: Checking recent task generations..."
TASKS=$(curl -s http://localhost:8000/api/tasks 2>/dev/null)
echo "$TASKS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tasks = data.get('tasks', [])
    if tasks:
        for t in tasks[-3:]:
            print(f\"  - {t['id'][:8]}... | {t['status']} | {t['progress']}%\")
    else:
        print('  No active tasks')
except: print('  Could not parse tasks')
"

# 4. CHECK LOGS FOR ERRORS
log "Step 4: Checking logs for errors..."
ERROR_COUNT=$(grep -c "ERROR\|Exception\|Failed" /root/Arsitektur/service/log/error.log 2>/dev/null || echo 0)
log "  Error count in error.log: $ERROR_COUNT"

if [ "$ERROR_COUNT" -gt 0 ]; then
    log "  Recent errors:"
    tail -5 /root/Arsitektur/service/log/error.log | while read line; do
        log "    $line"
    done
fi

# 5. GENERATE REPORT
log "Step 5: Generating status report..."

if [ "$FRONTEND" = "200" ] && [ "$BACKEND" = "200" ]; then
    log "✓ ALL SERVICES HEALTHY"
    exit 0
else
    log "⚠️ SERVICE ISSUES DETECTED"
    log "  Frontend: $([ "$FRONTEND" = "200" ] && echo 'OK' || echo 'FAIL ($FRONTEND)')"
    log "  Backend: $([ "$BACKEND" = "200" ] && echo 'OK' || echo 'FAIL ($BACKEND)')"
    exit 1
fi