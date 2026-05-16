#!/bin/bash
# BIM Quality Guardian - Health Check Script
# Run via cron: */5 * * * * /root/.hermes/scripts/guardian.sh >> /var/log/bim-guardian.log 2>&1

cd /root/Arsitektur/service
source venv/bin/activate

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$SCRIPT_DIR:$PATH"

echo "=== BIM Guardian Check - $(date) ==="

# Check Frontend
FRONTEND=$(curl -s -o /dev/null -w "%{http_code}" https://bim.nodesemesta.com)
echo "Frontend: $FRONTEND"

# Check Backend
BACKEND=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
echo "Backend: $BACKEND"

# Run API tests
python3 /root/Arsitektur/service/scripts/test_api.py --json 2>/dev/null | tail -1

# Report if issues found
if [ "$FRONTEND" != "200" ] || [ "$BACKEND" != "200" ]; then
    echo "⚠️ Service issue detected!"
    exit 1
fi

echo "✓ All services healthy"
exit 0