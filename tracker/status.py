from __future__ import annotations

from datetime import datetime, timedelta

from .models import Assignment


def calculate_status(assignment: Assignment, now: datetime, due_soon_days: int) -> str:
    if assignment.submitted:
        return "Completed"
    if assignment.late:
        return "Late"
    if assignment.due_at is None:
        return "No Due Date"
    if assignment.due_at < now:
        return "Missing"
    if assignment.due_at <= now + timedelta(days=due_soon_days):
        return "Due Soon"
    return "Upcoming"
