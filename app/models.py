from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    institution = Column(String)
    hashed_password = Column(String)

    courses = relationship("Course", back_populates="user")
    semesters = relationship("Semester", back_populates="user", cascade="all, delete")

class Semester(Base):
    __tablename__ = "semesters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="semesters")
    courses = relationship("Course", back_populates="semester", cascade="all, delete-orphan")

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    grade = Column(String, nullable=False)  # e.g. "A", "B", etc.
    unit = Column(Integer, nullable=False)
    difficulty = Column(String, nullable=True)
    instructor = Column(String, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="courses")
    semester_id = Column(Integer, ForeignKey("semesters.id"))
    semester = relationship("Semester", back_populates="courses")