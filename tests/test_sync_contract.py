import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from tracker.classroom import _due_datetime
from tracker.models import Assignment
from tracker.notion import NotionClient
from tracker.sync import run


class DeadlineTests(unittest.TestCase):
    def test_utc_deadline_crosses_local_date(self):
        result = _due_datetime(
            {"dueDate": {"year": 2026, "month": 9, "day": 10}, "dueTime": {"hours": 2}},
            "America/New_York",
        )
        self.assertEqual(result.isoformat(), "2026-09-09T22:00:00-04:00")

    def test_winter_offset(self):
        result = _due_datetime(
            {
                "dueDate": {"year": 2026, "month": 1, "day": 10},
                "dueTime": {"hours": 12},
            },
            "America/New_York",
        )
        self.assertEqual(result.hour, 7)

    def test_no_deadline(self):
        self.assertIsNone(_due_datetime({}, "UTC"))


class NotionTests(unittest.TestCase):
    def test_invalid_cursor_stops(self):
        client = NotionClient("example", "example")
        client._request = Mock(return_value={"results": [], "has_more": True})
        with self.assertRaisesRegex(RuntimeError, "pagination"):
            list(client.pages())

    def test_duplicate_rows_are_rejected(self):
        client = NotionClient("example", "example")
        page = {
            "id": "one",
            "properties": {
                "Course ID": {"rich_text": [{"plain_text": "a"}]},
                "Coursework ID": {"rich_text": [{"plain_text": "b"}]},
            },
        }
        client.pages = Mock(return_value=iter([page, {**page, "id": "two"}]))
        with self.assertRaisesRegex(RuntimeError, "Duplicate"):
            client.existing_assignments()

    def test_non_json_error(self):
        client = NotionClient("example", "example")
        response = Mock(ok=False, status_code=502)
        response.json.side_effect = ValueError()
        client.session.request = Mock(return_value=response)
        with self.assertRaisesRegex(RuntimeError, "non-JSON"):
            client._request("GET", "/example")

    def test_user_fields_never_written(self):
        item = Assignment(
            "a", "b", "Essay", "English", None, None, "NEW", False, False, None, 100
        )
        properties = NotionClient.properties(
            item, "No Due Date", datetime.now(timezone.utc)
        )
        self.assertNotIn("Priority", properties)
        self.assertNotIn("My Notes", properties)


class SyncTests(unittest.TestCase):
    @patch.dict(
        "os.environ", {"NOTION_TOKEN": "example", "NOTION_DATA_SOURCE_ID": "example"}
    )
    @patch("tracker.sync.load_dotenv")
    @patch("tracker.sync.authorize")
    @patch("tracker.sync.fetch_assignments")
    @patch("tracker.sync.NotionClient")
    def test_dry_run_never_writes(self, client, fetch, authorize, dotenv):
        fetch.return_value = (
            [
                Assignment(
                    "a",
                    "b",
                    "Essay",
                    "English",
                    None,
                    None,
                    "NEW",
                    False,
                    False,
                    None,
                    100,
                )
            ],
            [],
        )
        client.return_value.existing_assignments.return_value = {}
        run(dry_run=True)
        client.return_value.create.assert_not_called()
        client.return_value.update.assert_not_called()


if __name__ == "__main__":
    unittest.main()
