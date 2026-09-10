from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Assignment:
    course_id: str
    coursework_id: str
    title: str
    course_name: str
    due_at: datetime | None
    classroom_url: str | None
    submission_state: str
    submitted: bool
    late: bool
    grade: float | None
    max_points: float | None

    @property
    def key(self) -> str:
        return f"{self.course_id}:{self.coursework_id}"
