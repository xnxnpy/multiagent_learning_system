from sqlalchemy import Column, BigInteger, String, DateTime, Text, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Assignment(Base):
    """作业模型"""
    __tablename__ = "assignments"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    teacher_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    due_date = Column(DateTime(timezone=True))
    target_students = Column(JSON)  # 学生ID列表
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_at = Column(DateTime(timezone=True))
    status = Column(String(20), default="draft")  # draft, published, closed

    # 关联关系
    teacher = relationship("User", back_populates="assignments")
    submissions = relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")


class AssignmentSubmission(Base):
    """作业提交模型"""
    __tablename__ = "assignment_submissions"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    assignment_id = Column(BigInteger, ForeignKey("assignments.id"), nullable=False, index=True)
    student_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    score = Column(BigInteger)
    feedback = Column(Text)
    status = Column(String(20), default="submitted")  # submitted, graded, returned

    # 关联关系
    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", back_populates="submissions")
