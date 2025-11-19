"""
Database Schemas for College Digital Application Management System

Each Pydantic model corresponds to a MongoDB collection.
Collection name = lowercase of class name

Key Collections:
- User: all types of users (student, coordinator, hod, registrar, admin)
- Department: academic and administrative departments
- Application: student applications with routing info
- StatusUpdate: timeline of actions on an application
- Notification: system/user notifications
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

# ---------- Core ----------
class Department(BaseModel):
    name: str = Field(..., description="Department name (e.g., Computer Science)")
    code: str = Field(..., description="Short code (e.g., CSE)")
    type: Literal["academic", "administrative"] = Field("academic", description="Department type")
    is_active: bool = Field(True)

class User(BaseModel):
    full_name: str = Field(...)
    email: EmailStr
    role: Literal["student", "coordinator", "hod", "registrar", "admin", "superadmin"]
    department_code: Optional[str] = Field(None, description="Code of department if applicable")
    is_active: bool = Field(True)

# ---------- Applications ----------
class Application(BaseModel):
    student_id: str = Field(..., description="College student ID / roll number")
    student_name: str = Field(...)
    student_email: EmailStr
    department_code: str = Field(..., description="Home department of student")
    category: Literal[
        "bonafide_certificate",
        "leave_request",
        "lab_access",
        "project_approval",
        "general"
    ] = Field("general")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed description")
    attachments: List[str] = Field(default_factory=list, description="Attachment URLs (optional)")

    status: Literal["submitted", "under_review", "approved", "rejected", "forwarded"] = Field("submitted")
    current_stage: Literal["coordinator", "hod", "registrar", "admin"] = Field("coordinator")
    route_history: List[str] = Field(default_factory=list, description="List of department codes or roles traversed")

class StatusUpdate(BaseModel):
    application_id: str
    actor_role: Literal["student", "coordinator", "hod", "registrar", "admin", "superadmin"]
    actor_name: str
    action: Literal["submit", "review", "forward", "approve", "reject", "comment"]
    comments: Optional[str] = None
    to_department: Optional[str] = None
    created_at: Optional[datetime] = None

class Notification(BaseModel):
    user_email: EmailStr
    title: str
    message: str
    read: bool = False

# Convenience small model for simple filters (not a collection)
class AppFilter(BaseModel):
    student_id: Optional[str] = None
    department_code: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
