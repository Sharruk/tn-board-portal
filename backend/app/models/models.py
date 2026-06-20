from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.database import Base


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), nullable=False)        # "Class 10"
    slug = Column(String(10), unique=True, nullable=False, index=True)  # "10"

    subjects = relationship("Subject", back_populates="class_", order_by="Subject.display_order")

    def __repr__(self):
        return f"<Class {self.name}>"


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)       # "Mathematics"
    slug = Column(String(50), nullable=False)        # "maths"
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
    exam_type = Column(String(100), nullable=False)  # "Unit Test 1", "Annual Exam"
    year = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    paper_type = Column(String(20), nullable=False)  # "question" | "answer_key"
    file_path = Column(String(500), nullable=True)   # stored filename in /uploads/
    public_url = Column(Text, nullable=True)         # URL for downloading
    youtube_url = Column(Text, nullable=True)        # YouTube embed URL
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
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Admin {self.username}>"
