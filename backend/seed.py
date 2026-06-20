"""
Run once to populate the database with initial data.
Usage: cd backend && python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database.database import SessionLocal, engine, Base
from app.models.models import Class, Subject, Admin
from app.services.auth import hash_password

Base.metadata.create_all(bind=engine)

CLASSES = [
    {"id": 9,  "name": "Class 9",  "slug": "9"},
    {"id": 10, "name": "Class 10", "slug": "10"},
    {"id": 11, "name": "Class 11", "slug": "11"},
    {"id": 12, "name": "Class 12", "slug": "12"},
]

SUBJECTS = {
    9: [
        ("Tamil",          "tamil",   False, 1),
        ("English",        "english", False, 2),
        ("Mathematics",    "maths",   False, 3),
        ("Science",        "science", True,  4),
        ("Social Science", "social",  False, 5),
    ],
    10: [
        ("Tamil",          "tamil",   False, 1),
        ("English",        "english", False, 2),
        ("Mathematics",    "maths",   False, 3),
        ("Science",        "science", True,  4),
        ("Social Science", "social",  False, 5),
    ],
    11: [
        ("Tamil",                  "tamil",   False, 1),
        ("English",                "english", False, 2),
        ("Mathematics",            "maths",   False, 3),
        ("Physics",                "physics", True,  4),
        ("Chemistry",              "chemistry", True, 5),
        ("Biology",                "biology", True,  6),
        ("Computer Science",       "cs",      True,  7),
        ("Computer Applications",  "ca",      True,  8),
        ("Accountancy",            "acc",     False, 9),
        ("Commerce",               "comm",    False, 10),
        ("Economics",              "eco",     False, 11),
    ],
    12: [
        ("Tamil",                  "tamil",   False, 1),
        ("English",                "english", False, 2),
        ("Mathematics",            "maths",   False, 3),
        ("Physics",                "physics", True,  4),
        ("Chemistry",              "chemistry", True, 5),
        ("Biology",                "biology", True,  6),
        ("Computer Science",       "cs",      True,  7),
        ("Computer Applications",  "ca",      True,  8),
        ("Accountancy",            "acc",     False, 9),
        ("Commerce",               "comm",    False, 10),
        ("Economics",              "eco",     False, 11),
    ],
}

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def seed():
    db = SessionLocal()
    try:
        # Seed classes
        for c in CLASSES:
            existing = db.query(Class).filter(Class.id == c["id"]).first()
            if not existing:
                db.add(Class(id=c["id"], name=c["name"], slug=c["slug"]))
                print(f"  + Class: {c['name']}")
            else:
                print(f"  ~ Class already exists: {c['name']}")
        db.commit()

        # Seed subjects
        for class_id, subjects in SUBJECTS.items():
            cls = db.query(Class).filter(Class.id == class_id).first()
            if not cls:
                continue
            for name, slug, is_practical, order in subjects:
                existing = db.query(Subject).filter(
                    Subject.class_id == class_id,
                    Subject.slug == slug,
                ).first()
                if not existing:
                    db.add(Subject(
                        class_id=class_id,
                        name=name,
                        slug=slug,
                        is_practical=is_practical,
                        display_order=order,
                    ))
                    print(f"  + Subject: Class {class_id} — {name}")
                else:
                    print(f"  ~ Subject already exists: Class {class_id} — {name}")
        db.commit()

        # Seed admin
        existing_admin = db.query(Admin).filter(Admin.username == ADMIN_USERNAME).first()
        if not existing_admin:
            db.add(Admin(
                username=ADMIN_USERNAME,
                password_hash=hash_password(ADMIN_PASSWORD),
            ))
            db.commit()
            print(f"  + Admin created: username={ADMIN_USERNAME} / password={ADMIN_PASSWORD}")
        else:
            print(f"  ~ Admin already exists: {ADMIN_USERNAME}")

        print("\nSeed complete.")

    except Exception as e:
        db.rollback()
        print(f"Error during seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding database...")
    seed()
