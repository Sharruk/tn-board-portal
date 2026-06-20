"""
Phase 4.1 Database Migration
=============================
Adds new columns to the 'admins' table and creates 'audit_logs'.
Run this ONCE before restarting the FastAPI backend.

Usage (from project root):
    cd backend
    python migrate_41.py

Or from project root:
    python backend/migrate_41.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

from sqlalchemy import text
from app.database.database import engine, Base
from app.models import models  # noqa — registers all models including AuditLog


def run():
    print("Phase 4.1 — Database Migration")
    print("=" * 50)

    # ── Step 1: Add new columns to admins ─────────────────────────────────────
    alter_statements = [
        (
            "admins.email",
            "ALTER TABLE admins ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
        ),
        (
            "admins.failed_login_count",
            "ALTER TABLE admins ADD COLUMN IF NOT EXISTS failed_login_count INTEGER NOT NULL DEFAULT 0",
        ),
        (
            "admins.locked_until",
            "ALTER TABLE admins ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP",
        ),
        (
            "admins.last_login_at",
            "ALTER TABLE admins ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP",
        ),
    ]

    with engine.connect() as conn:
        for label, stmt in alter_statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
                print(f"  ✓ Added column: {label}")
            except Exception as e:
                conn.rollback()
                print(f"  ~ Skipped {label}: {e}")

        # Add unique index on email (if not exists — PostgreSQL syntax)
        try:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_admins_email ON admins (email) WHERE email IS NOT NULL"
            ))
            conn.commit()
            print("  ✓ Added unique index: admins.email")
        except Exception as e:
            conn.rollback()
            print(f"  ~ Skipped email index: {e}")

    # ── Step 2: Create audit_logs table ───────────────────────────────────────
    print("\nCreating new tables (audit_logs)...")
    Base.metadata.create_all(bind=engine)
    print("  ✓ audit_logs table ready")

    # ── Step 3: Set email on existing admin account ────────────────────────────
    print("\nUpdating admin account...")
    target_email = "hungrylearner786@gmail.com"

    from app.database.database import SessionLocal
    from app.models.models import Admin

    db = SessionLocal()
    try:
        admin = db.query(Admin).filter(Admin.username == "admin").first()
        if admin:
            if not admin.email:
                admin.email = target_email
                db.commit()
                print(f"  ✓ Set email: {admin.username} → {target_email}")
            else:
                print(f"  ~ Admin already has email: {admin.email}")
        else:
            print("  ! No admin with username='admin' found")
            all_admins = db.query(Admin).all()
            if all_admins:
                print(f"    Existing admins: {[a.username for a in all_admins]}")
                print("    Update admin.email manually using change_admin_password.py")
    finally:
        db.close()

    print("\nMigration complete.")
    print("\nNext steps:")
    print("  1. Restart the FastAPI backend workflow")
    print("  2. Run change_admin_password.py to set a production password")


if __name__ == "__main__":
    run()
