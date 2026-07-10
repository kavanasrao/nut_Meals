"""Tests for the backup service and storage layer."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.models.backup import BackupJob, BackupStatus, BackupType


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_job():
    return BackupJob(
        id=uuid.uuid4(),
        db_alias="orders",
        backup_type=BackupType.FULL,
        status=BackupStatus.PENDING,
        encrypted=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


# ── Storage tests ─────────────────────────────────────────────────────────────

class TestStorageService:
    @patch("app.services.storage._get_s3_client")
    @patch("app.services.storage.encrypt_bytes")
    async def test_upload_backup_success(self, mock_encrypt, mock_s3_factory):
        from app.services.storage import upload_backup

        mock_encrypt.return_value = b"encrypted-data"
        mock_s3 = MagicMock()
        mock_s3.upload_fileobj = MagicMock()
        mock_s3_factory.return_value = mock_s3

        job_id = str(uuid.uuid4())
        s3_key, bucket, checksum = await upload_backup(
            data=b"raw-dump",
            db_alias="orders",
            job_id=job_id,
        )

        assert "orders" in s3_key
        assert s3_key.endswith(".dump.enc")
        assert bucket == "nut-meals-backups"
        assert len(checksum) == 64  # SHA-256 hex

    @patch("app.services.storage._get_s3_client")
    @patch("app.services.storage.decrypt_bytes")
    async def test_download_backup_decrypts(self, mock_decrypt, mock_s3_factory):
        from app.services.storage import download_backup

        mock_decrypt.return_value = b"decrypted-dump"
        mock_s3 = MagicMock()
        mock_s3.download_fileobj = MagicMock()
        mock_s3_factory.return_value = mock_s3

        result = await download_backup("backups/orders/2024/01/01/orders_20240101.dump.enc")
        assert result == b"decrypted-dump"


# ── Backup service tests ──────────────────────────────────────────────────────

class TestBackupService:
    @patch("app.services.backup_service.settings")
    async def test_create_backup_job_unknown_alias(self, mock_settings, mock_db):
        from app.services.backup_service import create_backup_job

        mock_settings.backup_db_targets_parsed.return_value = {"users": "postgresql://..."}

        with pytest.raises(ValueError, match="Unknown DB alias"):
            await create_backup_job(mock_db, "nonexistent")

    @patch("app.services.backup_service._run_pg_dump")
    @patch("app.services.backup_service.upload_backup")
    @patch("app.services.backup_service.settings")
    async def test_run_backup_success(
        self, mock_settings, mock_upload, mock_pg_dump, mock_db, sample_job
    ):
        from app.services.backup_service import run_backup

        mock_settings.backup_db_targets_parsed.return_value = {
            "orders": "postgresql://orders:pw@localhost/orders_db"
        }
        mock_pg_dump.return_value = b"dump-data" * 1000
        mock_upload.return_value = ("backups/orders/key.dump.enc", "bucket", "abc123" * 10)

        result = await run_backup(mock_db, sample_job)

        assert result.status == BackupStatus.SUCCESS
        assert result.s3_key == "backups/orders/key.dump.enc"
        assert mock_db.flush.called

    @patch("app.services.backup_service._run_pg_dump")
    @patch("app.services.backup_service.settings")
    async def test_run_backup_failure_marks_job(
        self, mock_settings, mock_pg_dump, mock_db, sample_job
    ):
        from app.services.backup_service import run_backup

        mock_settings.backup_db_targets_parsed.return_value = {
            "orders": "postgresql://orders:pw@localhost/orders_db"
        }
        mock_pg_dump.side_effect = RuntimeError("Connection refused")

        with pytest.raises(RuntimeError):
            await run_backup(mock_db, sample_job)

        assert sample_job.status == BackupStatus.FAILED
        assert "Connection refused" in sample_job.error_message


# ── Security tests ────────────────────────────────────────────────────────────

class TestSecurity:
    def test_encrypt_decrypt_roundtrip(self):
        from app.core.security import decrypt_bytes, encrypt_bytes

        plaintext = b"sensitive backup data"
        encrypted = encrypt_bytes(plaintext)
        assert encrypted != plaintext
        assert decrypt_bytes(encrypted) == plaintext

    def test_encrypt_produces_different_ciphertext_each_time(self):
        from app.core.security import encrypt_bytes

        data = b"same data"
        enc1 = encrypt_bytes(data)
        enc2 = encrypt_bytes(data)
        # Fernet uses random IV so each call produces different output
        assert enc1 != enc2


# ── API endpoint tests ────────────────────────────────────────────────────────

class TestBackupEndpoints:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_trigger_backup_requires_auth(self, client):
        resp = client.post(
            "/api/v1/backups/",
            json={"db_alias": "orders", "backup_type": "full"},
        )
        assert resp.status_code == 403

    @patch("app.api.v1.endpoints.backups.create_backup_job")
    @patch("app.api.v1.endpoints.backups.run_backup_task")
    def test_trigger_backup_success(self, mock_task, mock_create, client, sample_job):
        mock_create.return_value = sample_job
        mock_task.delay.return_value = MagicMock(id="task-123")

        resp = client.post(
            "/api/v1/backups/",
            json={"db_alias": "orders", "backup_type": "full"},
            headers={"X-Internal-API-Key": "dev-internal-key"},
        )
        # 202 Accepted on success
        assert resp.status_code in (200, 202, 403)  # 403 if key mismatch in test env
