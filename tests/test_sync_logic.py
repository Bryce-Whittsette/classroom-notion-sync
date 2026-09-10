import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tracker.models import Assignment
from tracker.status import calculate_status


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 27, 12, tzinfo=ZoneInfo("America/New_York"))

    def assignment(self, **overrides):
        values = {
            "course_id": "course",
            "coursework_id": "work",
            "title": "Essay",
            "course_name": "English",
            "due_at": self.now + timedelta(days=7),
            "classroom_url": None,
            "submission_state": "CREATED",
            "submitted": False,
            "late": False,
            "grade": None,
            "max_points": 100,
        }
        values.update(overrides)
        return Assignment(**values)

    def test_completed_wins(self):
        item = self.assignment(
            submitted=True, late=True, due_at=self.now - timedelta(days=1)
        )
        self.assertEqual(calculate_status(item, self.now, 3), "Completed")

    def test_google_late_flag(self):
        self.assertEqual(
            calculate_status(self.assignment(late=True), self.now, 3), "Late"
        )

    def test_missing_when_past_due(self):
        item = self.assignment(due_at=self.now - timedelta(minutes=1))
        self.assertEqual(calculate_status(item, self.now, 3), "Missing")

    def test_due_soon(self):
        item = self.assignment(due_at=self.now + timedelta(days=2))
        self.assertEqual(calculate_status(item, self.now, 3), "Due Soon")

    def test_upcoming(self):
        self.assertEqual(calculate_status(self.assignment(), self.now, 3), "Upcoming")

    def test_no_due_date(self):
        self.assertEqual(
            calculate_status(self.assignment(due_at=None), self.now, 3), "No Due Date"
        )


if __name__ == "__main__":
    unittest.main()
