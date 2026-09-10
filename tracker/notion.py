from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import Assignment

NOTION_VERSION = "2025-09-03"


class NotionClient:
    def __init__(self, token: str, data_source_id: str) -> None:
        self.data_source_id = data_source_id
        self.session = requests.Session()
        # Retry reads and rate limits. Never replay an ambiguous page creation.
        self.session.mount(
            "https://",
            HTTPAdapter(
                max_retries=Retry(
                    total=3,
                    backoff_factor=0.5,
                    allowed_methods={"GET", "PATCH"},
                    status_forcelist=[429, 502, 503, 504],
                    respect_retry_after_header=True,
                )
            ),
        )
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(
            method, f"https://api.notion.com/v1{path}", timeout=30, **kwargs
        )
        if not response.ok:
            try:
                detail = response.json().get("message", "Request rejected")
            except ValueError:
                detail = "The service returned a non-JSON error response."
            raise RuntimeError(f"Notion API error ({response.status_code}): {detail}")
        return response.json()

    def pages(self) -> Iterator[dict[str, Any]]:
        cursor = None
        while True:
            body: dict[str, Any] = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            result = self._request(
                "POST", f"/data_sources/{self.data_source_id}/query", json=body
            )
            yield from result.get("results", [])
            if not result.get("has_more"):
                return
            next_cursor = result.get("next_cursor")
            if not next_cursor or next_cursor == cursor:
                raise RuntimeError("Notion returned an invalid pagination cursor.")
            cursor = next_cursor

    @staticmethod
    def _plain_text(page: dict[str, Any], name: str) -> str:
        prop = page.get("properties", {}).get(name, {})
        values = prop.get("rich_text", [])
        return "".join(value.get("plain_text", "") for value in values)

    def existing_assignments(self) -> dict[str, str]:
        existing: dict[str, str] = {}
        for page in self.pages():
            course_id = self._plain_text(page, "Course ID")
            coursework_id = self._plain_text(page, "Coursework ID")
            if course_id and coursework_id:
                key = f"{course_id}:{coursework_id}"
                if key in existing:
                    raise RuntimeError(
                        f"Duplicate assignment key in Notion: {key}. Merge the duplicate rows before syncing."
                    )
                existing[key] = page["id"]
        return existing

    @staticmethod
    def properties(
        assignment: Assignment, status: str, synced_at: datetime
    ) -> dict[str, Any]:
        due = {"date": None}
        if assignment.due_at:
            due = {"date": {"start": assignment.due_at.isoformat()}}
        return {
            "Assignment": {"title": [{"text": {"content": assignment.title[:2000]}}]},
            "Course": {
                "rich_text": [{"text": {"content": assignment.course_name[:2000]}}]
            },
            "Due": due,
            "Status": {"select": {"name": status}},
            "Submitted": {"checkbox": assignment.submitted},
            "Grade": {"number": assignment.grade},
            "Max Points": {"number": assignment.max_points},
            "Classroom Link": {"url": assignment.classroom_url},
            "Course ID": {"rich_text": [{"text": {"content": assignment.course_id}}]},
            "Coursework ID": {
                "rich_text": [{"text": {"content": assignment.coursework_id}}]
            },
            "Submission State": {
                "rich_text": [{"text": {"content": assignment.submission_state}}]
            },
            "Last Synced": {"date": {"start": synced_at.isoformat()}},
        }

    def create(self, properties: dict[str, Any]) -> str:
        result = self._request(
            "POST",
            "/pages",
            json={
                "parent": {
                    "type": "data_source_id",
                    "data_source_id": self.data_source_id,
                },
                "properties": properties,
            },
        )
        return result["id"]

    def update(self, page_id: str, properties: dict[str, Any]) -> None:
        self._request("PATCH", f"/pages/{page_id}", json={"properties": properties})
