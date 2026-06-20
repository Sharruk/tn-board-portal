"""
Change Admin Password
=====================
Safely update the admin account credentials (email and/or password).
Run this interactively — the password is never stored in source code.

Usage (from project root):
    python change_admin_password.py

Requirements:
    DATABASE_URL must be set in .env or environment secrets.
"""

import os
import sys
import getpass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from dotenv import load_dotenv
load_dotenv()

from app.database.database import SessionLocal
from app.models.models import Admin
from app.services.auth import hash_password, verify_password


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{label}{suffix}: ").strip()
    return val or default


def main():
    print()
    print("=" * 50)
    print("  Admin Account Manager")
    print("  TN State Board Learning Platform")
    print("=" * 50)

    db = SessionLocal()
    try:
        admins = db.query(Admin).all()
        if not admins:
            print("\nNo admin accounts found in database.")
            return

        print(f"\nFound {len(admins)} admin account(s):\n")
        for i, a in enumerate(admins):
            lock_status = " 🔒 LOCKED" if a.locked_until else ""
            print(f"  [{i + 1}] {a.username:<20} Email: {a.email or '(none)'}{lock_status}")

        print()
        choice = prompt("Select account number", "1")
        try:
            admin = admins[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid selection.")
            return

        print(f"\nEditing: {admin.username} ({admin.email or 'no email'})")
        print()

        # Update email
        new_email = prompt("New email (leave blank to keep current)", admin.email or "")
        if new_email and new_email != admin.email:
            # Check uniqueness
            existing = db.query(Admin).filter(Admin.email == new_email, Admin.id != admin.id).first()
            if existing:
                print(f"  ✗ Email '{new_email}' is already used by another admin.")
                return
            admin.email = new_email
            print(f"  ✓ Email will be updated to: {new_email}")

        # Update password
        print()
        change_pw = input("Change password? [y/N]: ").strip().lower()
        if change_pw == "y":
            new_pw = getpass.getpass("  New password: ")
            if len(new_pw) < 8:
                print("  ✗ Password must be at least 8 characters.")
                return
            confirm_pw = getpass.getpass("  Confirm password: ")
            if new_pw != confirm_pw:
                print("  ✗ Passwords do not match.")
                return
            admin.password_hash = hash_password(new_pw)
            print("  ✓ Password will be updated.")

        # Unlock account if locked
        if admin.locked_until:
            unlock = input("\nAccount is locked. Unlock it? [Y/n]: ").strip().lower()
            if unlock != "n":
                admin.locked_until = None
                admin.failed_login_count = 0
                print("  ✓ Account will be unlocked.")

        print()
        confirm = input("Save changes? [Y/n]: ").strip().lower()
        if confirm == "n":
            print("Cancelled — no changes saved.")
            return

        db.commit()
        print("\n✅ Changes saved successfully.")
        print(f"   Username: {admin.username}")
        print(f"   Email:    {admin.email or '(none)'}")
        print(f"   Locked:   {'No' if not admin.locked_until else 'Yes'}")

    except KeyboardInterrupt:
        print("\n\nCancelled.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
