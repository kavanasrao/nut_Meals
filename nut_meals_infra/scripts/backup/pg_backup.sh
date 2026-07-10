#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# pg_backup.sh — Direct PostgreSQL backup script (standalone, no FastAPI)
#
# Usage:
#   pg_backup.sh [--db-alias <alias>] [--all]
#
# Environment variables (can be loaded from .env):
#   BACKUP_DB_TARGETS   — "alias1=dsn1,alias2=dsn2"
#   S3_BUCKET_NAME      — target bucket
#   S3_ENDPOINT_URL     — optional, for OCI / MinIO
#   S3_ACCESS_KEY_ID
#   S3_SECRET_ACCESS_KEY
#   S3_REGION
#   BACKUP_ENCRYPTION_KEY — 32-char Fernet key material
#   BACKUP_RETENTION_DAYS — default 30
#   SLACK_WEBHOOK_URL   — optional notifications
#
# Dependencies: pg_dump, aws-cli v2, openssl, python3 (for Fernet encrypt)
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail
IFS=$'\n\t'

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()     { error "$*"; exit 1; }

# ── Defaults ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DATE_PATH="$(date -u +%Y/%m/%d)"
TMP_DIR="$(mktemp -d)"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_ALL=false
TARGET_ALIAS=""

trap 'rm -rf "$TMP_DIR"; info "Cleaned up temp files"' EXIT

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --db-alias)   TARGET_ALIAS="$2"; shift 2 ;;
        --all)        BACKUP_ALL=true; shift ;;
        --help|-h)
            echo "Usage: $0 [--db-alias <alias>] [--all]"; exit 0 ;;
        *) die "Unknown argument: $1" ;;
    esac
done

# ── Validate environment ──────────────────────────────────────────────────────
: "${BACKUP_DB_TARGETS:?BACKUP_DB_TARGETS must be set}"
: "${S3_BUCKET_NAME:?S3_BUCKET_NAME must be set}"
: "${S3_ACCESS_KEY_ID:?S3_ACCESS_KEY_ID must be set}"
: "${S3_SECRET_ACCESS_KEY:?S3_SECRET_ACCESS_KEY must be set}"
: "${BACKUP_ENCRYPTION_KEY:?BACKUP_ENCRYPTION_KEY must be set}"

command -v pg_dump    >/dev/null 2>&1 || die "pg_dump not found"
command -v aws        >/dev/null 2>&1 || die "aws-cli not found"
command -v python3    >/dev/null 2>&1 || die "python3 not found"

# ── S3 CLI args ───────────────────────────────────────────────────────────────
AWS_ARGS=(--region "${S3_REGION:-us-east-1}")
[[ -n "${S3_ENDPOINT_URL:-}" ]] && AWS_ARGS+=(--endpoint-url "$S3_ENDPOINT_URL")

export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY"

# ── Fernet encryption via python3 ─────────────────────────────────────────────
encrypt_file() {
    local src="$1" dst="$2"
    python3 - "$src" "$dst" "$BACKUP_ENCRYPTION_KEY" <<'PYEOF'
import sys, base64
from cryptography.fernet import Fernet

src, dst, raw_key = sys.argv[1], sys.argv[2], sys.argv[3]
key = base64.urlsafe_b64encode(raw_key.encode()[:32].ljust(32, b'\0'))
f = Fernet(key)
with open(src, 'rb') as fin, open(dst, 'wb') as fout:
    fout.write(f.encrypt(fin.read()))
PYEOF
}

# ── Slack notification ────────────────────────────────────────────────────────
notify_slack() {
    [[ -z "${SLACK_WEBHOOK_URL:-}" ]] && return 0
    local msg="$1"
    curl -s -X POST "$SLACK_WEBHOOK_URL" \
         -H 'Content-type: application/json' \
         --data "{\"text\": \"$msg\"}" >/dev/null
}

# ── Core backup function ──────────────────────────────────────────────────────
do_backup() {
    local alias="$1" dsn="$2"
    local dump_file="$TMP_DIR/${alias}_${TIMESTAMP}.dump"
    local enc_file="${dump_file}.enc"
    local s3_key="backups/${alias}/${DATE_PATH}/${alias}_${TIMESTAMP}.dump.enc"

    info "Starting backup: alias=$alias"

    # 1. pg_dump
    if ! PGPASSWORD="" pg_dump \
            --no-password \
            --format=custom \
            --compress=6 \
            --lock-wait-timeout=30s \
            "$dsn" > "$dump_file"; then
        error "pg_dump failed for $alias"
        notify_slack "❌ *pg_dump FAILED* for \`$alias\` on $(hostname)"
        return 1
    fi

    local raw_size
    raw_size=$(stat -c%s "$dump_file" 2>/dev/null || stat -f%z "$dump_file")
    info "Dump complete: ${raw_size} bytes"

    # 2. Fernet encrypt
    encrypt_file "$dump_file" "$enc_file"
    rm -f "$dump_file"
    info "Encrypted dump → $enc_file"

    # 3. Checksum
    local sha256
    sha256=$(sha256sum "$enc_file" | awk '{print $1}')

    # 4. Upload to S3
    aws s3 cp "$enc_file" "s3://${S3_BUCKET_NAME}/${s3_key}" \
        "${AWS_ARGS[@]}" \
        --sse AES256 \
        --metadata "alias=$alias,sha256=$sha256,encrypted=fernet,timestamp=$TIMESTAMP" \
        --storage-class STANDARD_IA

    local enc_size
    enc_size=$(stat -c%s "$enc_file" 2>/dev/null || stat -f%z "$enc_file")
    info "Uploaded s3://${S3_BUCKET_NAME}/${s3_key} (${enc_size} bytes, sha256=${sha256})"
    rm -f "$enc_file"

    notify_slack "✅ *Backup succeeded* \`$alias\` — ${enc_size} bytes → \`$s3_key\`"
    return 0
}

# ── Parse BACKUP_DB_TARGETS ───────────────────────────────────────────────────
declare -A DB_TARGETS
while IFS='=' read -r alias dsn; do
    alias="${alias// /}"
    dsn="${dsn// /}"
    [[ -n "$alias" && -n "$dsn" ]] && DB_TARGETS["$alias"]="$dsn"
done < <(echo "$BACKUP_DB_TARGETS" | tr ',' '\n' | sed 's/=/ /')

[[ ${#DB_TARGETS[@]} -eq 0 ]] && die "No DB targets parsed from BACKUP_DB_TARGETS"

# ── Dispatch ──────────────────────────────────────────────────────────────────
failed=0

if $BACKUP_ALL; then
    for alias in "${!DB_TARGETS[@]}"; do
        do_backup "$alias" "${DB_TARGETS[$alias]}" || ((failed++))
    done
elif [[ -n "$TARGET_ALIAS" ]]; then
    [[ -v DB_TARGETS["$TARGET_ALIAS"] ]] || die "Unknown alias: $TARGET_ALIAS"
    do_backup "$TARGET_ALIAS" "${DB_TARGETS[$TARGET_ALIAS]}" || ((failed++))
else
    die "Specify --db-alias <alias> or --all"
fi

# ── Retention cleanup ─────────────────────────────────────────────────────────
info "Running S3 retention cleanup (${RETENTION_DAYS} days)"
aws s3 ls "s3://${S3_BUCKET_NAME}/backups/" "${AWS_ARGS[@]}" --recursive \
    | awk '{print $4}' \
    | while read -r key; do
        obj_date=$(echo "$key" | grep -oP '\d{4}/\d{2}/\d{2}' | head -1 | tr '/' '-')
        if [[ -n "$obj_date" ]]; then
            age_days=$(( ( $(date -u +%s) - $(date -u -d "$obj_date" +%s 2>/dev/null || date -u -j -f "%Y-%m-%d" "$obj_date" +%s) ) / 86400 ))
            if (( age_days > RETENTION_DAYS )); then
                warn "Deleting expired backup: $key (${age_days}d old)"
                aws s3 rm "s3://${S3_BUCKET_NAME}/${key}" "${AWS_ARGS[@]}"
            fi
        fi
    done

if (( failed > 0 )); then
    die "$failed backup(s) failed"
fi
info "All backups completed successfully"
