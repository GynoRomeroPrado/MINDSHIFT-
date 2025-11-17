#!/bin/bash
#
# MindShift Database Backup Script
# Automated backup with rotation and S3 upload
#

set -e

# Configuration
BACKUP_DIR="/var/backups/mindshift"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="mindshift_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

# Database credentials (from environment)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-mindshift}"
DB_USER="${DB_USER:-mindshift}"
DB_PASSWORD="${DB_PASSWORD}"

# S3 configuration (optional)
S3_BUCKET="${S3_BUCKET:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

echo "==================================="
echo "MindShift Database Backup"
echo "==================================="
echo "Timestamp: ${TIMESTAMP}"
echo "Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
echo ""

# Perform backup
echo "Creating database backup..."
PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --format=custom \
    --compress=9 \
    --file="${BACKUP_DIR}/${BACKUP_FILE}"

echo "✓ Backup created: ${BACKUP_FILE}"

# Get backup size
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
echo "  Size: ${BACKUP_SIZE}"

# Upload to S3 (if configured)
if [ -n "${S3_BUCKET}" ]; then
    echo ""
    echo "Uploading to S3..."
    aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" \
        "s3://${S3_BUCKET}/backups/${BACKUP_FILE}" \
        --region "${AWS_REGION}"

    echo "✓ Uploaded to s3://${S3_BUCKET}/backups/${BACKUP_FILE}"
fi

# Remove old backups
echo ""
echo "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
find "${BACKUP_DIR}" -name "mindshift_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
OLD_COUNT=$(find "${BACKUP_DIR}" -name "mindshift_backup_*.sql.gz" -mtime +${RETENTION_DAYS} | wc -l)
echo "✓ Removed ${OLD_COUNT} old backups"

# List current backups
echo ""
echo "Current backups:"
ls -lh "${BACKUP_DIR}/mindshift_backup_"*.sql.gz | tail -5

echo ""
echo "==================================="
echo "Backup Complete!"
echo "==================================="
