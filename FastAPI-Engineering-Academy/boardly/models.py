# boardly/models.py
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

@dataclass
class User:
    id: UUID
    name: str
    email: str

@dataclass
class Project:
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime

@dataclass
class Ticket:
    id: UUID
    project_id: UUID
    title: str
    assignee_id: UUID | None
    status: str   # "open" | "in_progress" | "blocked" | "done"
    priority: int # 1 (low) .. 5 (urgent)
