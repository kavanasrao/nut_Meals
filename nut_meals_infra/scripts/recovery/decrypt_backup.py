#!/usr/bin/env python3
"""
decrypt_backup.py — Decrypt a Fernet-encrypted nut_Meals backup file.

Usage:
    python decrypt_backup.py <encrypted_file> <output_file> [--key <key>]

If --key is omitted, reads BACKUP_ENCRYPTION_KEY from environment.
"""

import argparse
import base64
import os
import sys
from pathlib import Path

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    sys.exit("Install cryptography: pip install cryptography")


def main() -> None:
    parser = argparse.ArgumentParser(description="Decrypt a nut_Meals backup")
    parser.add_argument("input", type=Path, help="Encrypted .enc file")
    parser.add_argument("output", type=Path, help="Output dump file")
    parser.add_argument("--key", help="Encryption key (overrides env var)")
    args = parser.parse_args()

    raw_key = args.key or os.environ.get("BACKUP_ENCRYPTION_KEY")
    if not raw_key:
        sys.exit("Provide --key or set BACKUP_ENCRYPTION_KEY")

    # Derive Fernet-compatible key from raw material
    key_bytes = raw_key.encode()[:32].ljust(32, b"\0")
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    f = Fernet(fernet_key)

    print(f"Reading {args.input} ({args.input.stat().st_size:,} bytes)")
    try:
        plaintext = f.decrypt(args.input.read_bytes())
    except InvalidToken:
        sys.exit("❌ Decryption failed — wrong key or corrupted file")

    args.output.write_bytes(plaintext)
    print(f"✅ Decrypted → {args.output} ({len(plaintext):,} bytes)")
    print(f"\nTo restore manually:\n  pg_restore --clean --if-exists --dbname=<DSN> {args.output}")


if __name__ == "__main__":
    main()
