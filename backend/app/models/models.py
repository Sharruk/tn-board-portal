from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.database import Base


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), nullable=False)
    slug = Column(String(10), unique=True, nullable=False, index=True)

    subjects = relationship("Subject", back_populates="class_", order_by="Subject.display_order")

    def __repr__(self):
        return f"<Class {self.name}>"


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), nullable=False)
    is_practical = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)

    class_ = relationship("Class", back_populates="subjects")
    papers = relationship("Paper", back_populates="subject", order_by="Paper.year.desc()")

    def __repr__(self):
        return f"<Subject {self.name}>"


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    exam_type = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    paper_type = Column(String(20), nullable=False)    # "question" | "answer_key"
    file_path = Column(String(500), nullable=True)
    public_url = Column(Text, nullable=True)
    youtube_url = Column(Text, nullable=True)
    is_visible = Column(Boolean, default=True)
    download_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="papers")

    def __repr__(self):
        return f"<Paper {self.title}>"


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    audit_logs = relationship("AuditLog", back_populates="admin", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Admin {self.username}>"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    admin_email = Column(String(255), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    target_paper_id = Column(Integer, nullable=True)
    target_details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    admin = relationship("Admin", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.admin_email}>"
