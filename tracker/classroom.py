from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import Assignment

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
]


def _paged(request_factory, result_key: str) -> Iterator[dict[str, Any]]:
    page_token = None
    while True:
        response = request_factory(page_token).execute()
        yield from response.get(result_key, [])
        page_token = response.get("nextPageToken")
        if not page_token:
            return


def _due_datetime(coursework: dict[str, Any], timezone_name: str) -> datetime | None:
    due_date = coursework.get("dueDate")
    if not due_date:
        return None
    due_time = coursework.get("dueTime", {})
    return datetime(
        due_date["year"],
        due_date["month"],
        due_date["day"],
        due_time.get("hours", 0),
        due_time.get("minutes", 0),
        due_time.get("seconds", 0),
        tzinfo=timezone.utc,
    ).astimezone(ZoneInfo(timezone_name))


def authorize(credentials_path: Path, token_path: Path) -> Credentials:
    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    elif not credentials or not credentials.valid:
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Missing {credentials_path}. Download the Google desktop OAuth file "
                "and save it there as credentials.json."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        credentials = flow.run_local_server(port=0)
    # Restrict access before writing, including when replacing an older token.
    descriptor = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as token_file:
        os.chmod(token_path, 0o600)
        token_file.write(credentials.to_json())
    return credentials


def fetch_assignments(
    credentials: Credentials, timezone_name: str
) -> tuple[list[Assignment], list[str]]:
    service = build("classroom", "v1", credentials=credentials, cache_discovery=False)
    courses = list(
        _paged(
            lambda token: service.courses().list(
                courseStates=["ACTIVE"], pageSize=100, pageToken=token
            ),
            "courses",
        )
    )
    assignments: list[Assignment] = []
    warnings: list[str] = []

    for course in courses:
        course_id = course["id"]
        try:
            coursework_items = list(
                _paged(
                    lambda token, course_id=course_id: (
                        service.courses()
                        .courseWork()
                        .list(
                            courseId=course_id,
                            courseWorkStates=["PUBLISHED"],
                            pageSize=100,
                            pageToken=token,
                        )
                    ),
                    "courseWork",
                )
            )
            submissions = list(
                _paged(
                    lambda token, course_id=course_id: (
                        service.courses()
                        .courseWork()
                        .studentSubmissions()
                        .list(
                            courseId=course_id,
                            courseWorkId="-",
                            userId="me",
                            pageSize=100,
                            pageToken=token,
                        )
                    ),
                    "studentSubmissions",
                )
            )
        except HttpError as error:
            warnings.append(f"Skipped {course.get('name', course_id)}: {error.reason}")
            continue

        submission_by_work = {item["courseWorkId"]: item for item in submissions}
        for item in coursework_items:
            submission = submission_by_work.get(item["id"], {})
            state = submission.get("state", "NEW")
            assignments.append(
                Assignment(
                    course_id=course_id,
                    coursework_id=item["id"],
                    title=item.get("title", "Untitled assignment"),
                    course_name=course.get("name", "Unknown course"),
                    due_at=_due_datetime(item, timezone_name),
                    classroom_url=item.get("alternateLink"),
                    submission_state=state,
                    submitted=state in {"TURNED_IN", "RETURNED"},
                    late=bool(submission.get("late", False)),
                    grade=submission.get("assignedGrade"),
                    max_points=item.get("maxPoints"),
                )
            )
    return assignments, warnings
