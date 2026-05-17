#!/bin/bash
# Script: /root/Arsitektur/pull-and-restart-pm2.sh
# Auto-pull git dan restart PM2 bila ada perubahan

LOG_FILE="/var/log/pull-and-restart-pm2.log"
REPO_DIR="/root/Arsitektur"
BRANCH="main"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === AUTO-PULL PM2 START ===" >> "$LOG_FILE"

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
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] === AUTO-PULL PM2 GAGAL ===" >> "$LOG_FILE"
  exit 1
fi

# Cek apakah HEAD berubah (ada perubahan dari git pull)
HEAD_AFTER=$(git rev-parse HEAD)

if [ "$HEAD_BEFORE" != "$HEAD_AFTER" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Perubahan terdeteksi! HEAD: $HEAD_BEFORE -> $HEAD_AFTER" >> "$LOG_FILE"

  # Restart PM2 apps
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restart PM2 apps..." >> "$LOG_FILE"
  cd "$REPO_DIR"
  pm2 restart all >> "$LOG_FILE" 2>&1
  PM2_EXIT=$?

  # Tunggu sebentar dan cek status
  sleep 2
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Status PM2:" >> "$LOG_FILE"
  pm2 status >> "$LOG_FILE" 2>&1

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restart selesai. PM2 exit=$PM2_EXIT" >> "$LOG_FILE"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tidak ada perubahan. HEAD: $HEAD_AFTER" >> "$LOG_FILE"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === AUTO-PULL PM2 END ===" >> "$LOG_FILE"
