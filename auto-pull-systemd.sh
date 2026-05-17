#!/bin/bash
# Script: /root/Arsitektur/auto-pull-systemd.sh
# Auto-pull git dan restart service systemd (arsitektur-backend & arsitektur-frontend)

LOG_FILE="/var/log/arsitektur-auto-pull.log"
REPO_DIR="/root/Arsitektur"
BRANCH="main"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === AUTO-PULL SYSTEMD START ===" >> "$LOG_FILE"

cd "$REPO_DIR" || {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Gagal cd ke $REPO_DIR" >> "$LOG_FILE"
  exit 1
}

# Simpan HEAD sebelum pull
HEAD_BEFORE=$(git rev-parse HEAD)

# Git pull
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Menjalankan git pull origin $BRANCH..." >> "$LOG_FILE"
git pull origin "$BRANCH" >> "$LOG_FILE" 2>&1
PULL_EXIT=$?

if [ $PULL_EXIT -ne 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: git pull gagal (exit code $PULL_EXIT)" >> "$LOG_FILE"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] === AUTO-PULL SYSTEMD GAGAL ===" >> "$LOG_FILE"
  exit 1
fi

# Cek apakah HEAD berubah (ada perubahan dari git pull)
HEAD_AFTER=$(git rev-parse HEAD)

if [ "$HEAD_BEFORE" != "$HEAD_AFTER" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Perubahan terdeteksi! HEAD: $HEAD_BEFORE -> $HEAD_AFTER" >> "$LOG_FILE"

  # Restart backend service
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restart arsitektur-backend.service..." >> "$LOG_FILE"
  systemctl restart arsitektur-backend.service >> "$LOG_FILE" 2>&1
  BACKEND_EXIT=$?

  # Restart frontend service
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restart arsitektur-frontend.service..." >> "$LOG_FILE"
  systemctl restart arsitektur-frontend.service >> "$LOG_FILE" 2>&1
  FRONTEND_EXIT=$?

  # Verifikasi status
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Status service:" >> "$LOG_FILE"
  systemctl is-active arsitektur-backend.service >> "$LOG_FILE" 2>&1
  systemctl is-active arsitektur-frontend.service >> "$LOG_FILE" 2>&1

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restart selesai. Backend exit=$BACKEND_EXIT, Frontend exit=$FRONTEND_EXIT" >> "$LOG_FILE"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tidak ada perubahan. HEAD: $HEAD_AFTER" >> "$LOG_FILE"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === AUTO-PULL SYSTEMD END ===" >> "$LOG_FILE"
