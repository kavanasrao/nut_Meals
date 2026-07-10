#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# pg_restore.sh — Download, decrypt, and restore a nut_Meals backup
#
# Usage:
#   pg_restore.sh --s3-key <key> --target-dsn <postgresql://...>
#   pg_restore.sh --list-backups [--db-alias <alias>]
#
# Same env vars as pg_backup.sh.
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()   { error "$*"; exit 1; }

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

S3_KEY=""
TARGET_DSN=""
LIST_MODE=false
FILTER_ALIAS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --s3-key)        S3_KEY="$2";       shift 2 ;;
        --target-dsn)    TARGET_DSN="$2";   shift 2 ;;
        --list-backups)  LIST_MODE=true;    shift ;;
        --db-alias)      FILTER_ALIAS="$2"; shift 2 ;;
        --help|-h) echo "Usage: $0 --s3-key <key> --target-dsn <dsn>"; exit 0 ;;
        *) die "Unknown argument: $1" ;;
    esac
done

: "${S3_BUCKET_NAME:?S3_BUCKET_NAME must be set}"
: "${S3_ACCESS_KEY_ID:?S3_ACCESS_KEY_ID must be set}"
: "${S3_SECRET_ACCESS_KEY:?S3_SECRET_ACCESS_KEY must be set}"
: "${BACKUP_ENCRYPTION_KEY:?BACKUP_ENCRYPTION_KEY must be set}"

export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY"
AWS_ARGS=(--region "${S3_REGION:-us-east-1}")
[[ -n "${S3_ENDPOINT_URL:-}" ]] && AWS_ARGS+=(--endpoint-url "$S3_ENDPOINT_URL")

decrypt_file() {
    local src="$1" dst="$2"
    python3 - "$src" "$dst" "$BACKUP_ENCRYPTION_KEY" <<'PYEOF'
import sys, base64
from cryptography.fernet import Fernet

src, dst, raw_key = sys.argv[1], sys.argv[2], sys.argv[3]
key = base64.urlsafe_b64encode(raw_key.encode()[:32].ljust(32, b'\0'))
f = Fernet(key)
with open(src, 'rb') as fin, open(dst, 'wb') as fout:
    fout.write(f.decrypt(fin.read()))
PYEOF
}

# ── List mode ─────────────────────────────────────────────────────────────────
if $LIST_MODE; then
    prefix="backups/"
    [[ -n "$FILTER_ALIAS" ]] && prefix="backups/${FILTER_ALIAS}/"
    info "Listing backups at s3://${S3_BUCKET_NAME}/${prefix}"
    aws s3 ls "s3://${S3_BUCKET_NAME}/${prefix}" "${AWS_ARGS[@]}" --recursive \
        | sort -k1,2 \
        | awk '{printf "%-45s %s\n", $4, $3}'
    exit 0
fi

# ── Restore mode ──────────────────────────────────────────────────────────────
[[ -z "$S3_KEY" ]]     && die "Specify --s3-key"
[[ -z "$TARGET_DSN" ]] && die "Specify --target-dsn"

warn "⚠️  This will OVERWRITE the target database. Ctrl-C within 5s to abort."
sleep 5

enc_file="$TMP_DIR/backup.dump.enc"
dump_file="$TMP_DIR/backup.dump"

# 1. Download
info "Downloading s3://${S3_BUCKET_NAME}/${S3_KEY}"
aws s3 cp "s3://${S3_BUCKET_NAME}/${S3_KEY}" "$enc_file" "${AWS_ARGS[@]}"
info "Downloaded: $(stat -c%s "$enc_file" 2>/dev/null || stat -f%z "$enc_file") bytes"

# 2. Verify checksum if stored in metadata
stored_sha=$(aws s3api head-object \
    --bucket "$S3_BUCKET_NAME" \
    --key "$S3_KEY" \
    "${AWS_ARGS[@]}" \
    --query 'Metadata.sha256' \
    --output text 2>/dev/null || echo "")

if [[ -n "$stored_sha" && "$stored_sha" != "None" ]]; then
    actual_sha=$(sha256sum "$enc_file" | awk '{print $1}')
    if [[ "$stored_sha" != "$actual_sha" ]]; then
        die "Checksum mismatch! stored=$stored_sha actual=$actual_sha — aborting"
    fi
    info "Checksum verified: $actual_sha"
fi

# 3. Decrypt
info "Decrypting backup..."
decrypt_file "$enc_file" "$dump_file"
rm -f "$enc_file"
info "Decrypted: $(stat -c%s "$dump_file" 2>/dev/null || stat -f%z "$dump_file") bytes"

# 4. Restore
info "Running pg_restore into target database..."
PGPASSWORD="" pg_restore \
    --no-password \
    --clean \
    --if-exists \
    --exit-on-error \
    --dbname="$TARGET_DSN" \
    "$dump_file"

info "✅ Restore complete"
