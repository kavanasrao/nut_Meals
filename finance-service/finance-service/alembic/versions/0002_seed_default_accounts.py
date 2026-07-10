"""seed default chart of accounts

Revision ID: 0002_seed_default_accounts
Revises: 0001_initial_schema
Create Date: 2026-07-10
"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_seed_default_accounts"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ACCOUNTS = [
    ("1000", "Cash", "asset"),
    ("1100", "Bank - Kotak Current Account", "asset"),
    ("1200", "Payment Gateway Clearing - Juspay", "asset"),
    ("1300", "Accounts Receivable", "asset"),
    ("2000", "Accounts Payable", "liability"),
    ("2100", "Customer Refunds Payable", "liability"),
    ("2200", "GST Payable", "liability"),
    ("3000", "Owner's Equity", "equity"),
    ("4000", "Sales Revenue", "income"),
    ("4100", "Delivery Fee Income", "income"),
    ("4900", "Reconciliation Gain (Misc Income)", "income"),
    ("5000", "Cost of Goods Sold", "expense"),
    ("5100", "Payment Gateway Fees", "expense"),
    ("5200", "Delivery & Logistics Expense", "expense"),
    ("5900", "Reconciliation Loss (Misc Expense)", "expense"),
]

ledger_accounts_table = sa.table(
    "ledger_accounts",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("account_type", sa.String),
    sa.column("is_system_account", sa.Boolean),
    sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    now = sa.func.now()
    rows = [
        {
            "id": uuid.uuid4(),
            "code": code,
            "name": name,
            "account_type": acc_type,
            "is_system_account": True,
            "is_active": True,
        }
        for code, name, acc_type in DEFAULT_ACCOUNTS
    ]
    conn = op.get_bind()
    for row in rows:
        conn.execute(
            ledger_accounts_table.insert().values(
                id=row["id"],
                code=row["code"],
                name=row["name"],
                account_type=row["account_type"],
                is_system_account=row["is_system_account"],
                is_active=row["is_active"],
                created_at=sa.func.now(),
                updated_at=sa.func.now(),
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    codes = tuple(code for code, _, _ in DEFAULT_ACCOUNTS)
    conn.execute(ledger_accounts_table.delete().where(ledger_accounts_table.c.code.in_(codes)))
