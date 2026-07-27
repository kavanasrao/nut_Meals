"""add otp codes, password reset tokens, social accounts, addresses,
user preferences and user audit logs

Revision ID: 0002_profile_features
Revises: 0001_initial
Create Date: 2026-07-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0002_profile_features"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # --- enums -----------------------------------------------------------------
    otp_channel_enum = pg.ENUM("sms", "email", name="otp_channel_enum", create_type=True)
    otp_channel_enum.create(bind, checkfirst=True)

    otp_purpose_enum = pg.ENUM(
        "login", "verify_phone", "verify_email", name="otp_purpose_enum", create_type=True
    )
    otp_purpose_enum.create(bind, checkfirst=True)

    social_provider_enum = pg.ENUM("google", name="social_provider_enum", create_type=True)
    social_provider_enum.create(bind, checkfirst=True)

    address_type_enum = pg.ENUM("home", "work", "other", name="address_type_enum", create_type=True)
    address_type_enum.create(bind, checkfirst=True)

    audit_action_enum = pg.ENUM(
        "login",
        "login_failed",
        "otp_login",
        "social_login",
        "logout",
        "profile_update",
        "password_change",
        "password_reset_requested",
        "password_reset_completed",
        "address_create",
        "address_update",
        "address_delete",
        "address_set_default",
        "preference_update",
        "account_blocked",
        "account_unblocked",
        "role_changed",
        name="user_audit_action_enum",
        create_type=True,
    )
    audit_action_enum.create(bind, checkfirst=True)

    # --- otp_codes ---------------------------------------------------------------
    op.create_table(
        "otp_codes",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("identifier", sa.String(320), nullable=False),
        sa.Column("channel", pg.ENUM("sms", "email", name="otp_channel_enum", create_type=False), nullable=False),
        sa.Column(
            "purpose",
            pg.ENUM("login", "verify_phone", "verify_email", name="otp_purpose_enum", create_type=False),
            nullable=False,
            server_default="login",
        ),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_otp_codes_identifier", "otp_codes", ["identifier"])

    # --- password_reset_tokens ---------------------------------------------------
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_ip", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"])

    # --- social_accounts -----------------------------------------------------------
    op.create_table(
        "social_accounts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", pg.ENUM("google", name="social_provider_enum", create_type=False), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_social_provider_user"),
    )
    op.create_index("ix_social_accounts_user_id", "social_accounts", ["user_id"])
    op.create_index("ix_social_accounts_provider_user_id", "social_accounts", ["provider_user_id"])

    # --- addresses ------------------------------------------------------------------
    op.create_table(
        "addresses",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(50), nullable=False, server_default="Home"),
        sa.Column(
            "address_type",
            pg.ENUM("home", "work", "other", name="address_type_enum", create_type=False),
            nullable=False,
            server_default="other",
        ),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("line1", sa.String(255), nullable=False),
        sa.Column("line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("postal_code", sa.String(20), nullable=False),
        sa.Column("landmark", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_addresses_user_id", "addresses", ["user_id"])
    op.create_index("ix_addresses_is_default", "addresses", ["is_default"])

    # --- user_preferences -------------------------------------------------------------
    op.create_table(
        "user_preferences",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("dark_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marketing_opt_in", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email_notifications", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sms_notifications", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("push_notifications", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"])

    # --- user_audit_logs -----------------------------------------------------------------
    op.create_table(
        "user_audit_logs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "action",
            pg.ENUM(
                "login",
                "login_failed",
                "otp_login",
                "social_login",
                "logout",
                "profile_update",
                "password_change",
                "password_reset_requested",
                "password_reset_completed",
                "address_create",
                "address_update",
                "address_delete",
                "address_set_default",
                "preference_update",
                "account_blocked",
                "account_unblocked",
                "role_changed",
                name="user_audit_action_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("extra_data", pg.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_audit_logs_user_id", "user_audit_logs", ["user_id"])
    op.create_index("ix_user_audit_logs_action", "user_audit_logs", ["action"])
    op.create_index("ix_user_audit_logs_created_at", "user_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_user_audit_logs_created_at", table_name="user_audit_logs")
    op.drop_index("ix_user_audit_logs_action", table_name="user_audit_logs")
    op.drop_index("ix_user_audit_logs_user_id", table_name="user_audit_logs")
    op.drop_table("user_audit_logs")

    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")
    op.drop_table("user_preferences")

    op.drop_index("ix_addresses_is_default", table_name="addresses")
    op.drop_index("ix_addresses_user_id", table_name="addresses")
    op.drop_table("addresses")

    op.drop_index("ix_social_accounts_provider_user_id", table_name="social_accounts")
    op.drop_index("ix_social_accounts_user_id", table_name="social_accounts")
    op.drop_table("social_accounts")

    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_index("ix_otp_codes_identifier", table_name="otp_codes")
    op.drop_table("otp_codes")

    bind = op.get_bind()
    pg.ENUM(name="user_audit_action_enum").drop(bind, checkfirst=True)
    pg.ENUM(name="address_type_enum").drop(bind, checkfirst=True)
    pg.ENUM(name="social_provider_enum").drop(bind, checkfirst=True)
    pg.ENUM(name="otp_purpose_enum").drop(bind, checkfirst=True)
    pg.ENUM(name="otp_channel_enum").drop(bind, checkfirst=True)
