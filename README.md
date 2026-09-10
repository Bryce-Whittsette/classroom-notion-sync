# Classroom → Notion

Copy your Google Classroom assignments into a Notion database. A course/work ID pair identifies each assignment, so later runs update its row. Your notes and priorities stay yours.

Google Classroom access is read-only. The sync **does write to Notion** unless `--dry-run` is supplied.

## Setup

Requires Python 3.11 or newer, a Google account with Classroom access, a Google desktop OAuth client, and a Notion internal integration.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

On Windows, activate with `.venv\Scripts\activate` instead.

1. Enable the Classroom API in your Google Cloud project. Create an OAuth client of type **Desktop app** and save its download as `credentials.json`. Add your account as a test user if your consent screen requires it.
2. Create a Notion internal integration and connect it to your destination database. Give it read, insert, and update content capabilities. Set `NOTION_TOKEN` and `NOTION_DATA_SOURCE_ID` in `.env`. Use the **data source ID**, not a page URL or database container ID.
3. Add the properties below to the database, preserving their names and types.
4. Run `classroom-sync --dry-run`. The first run opens Google sign-in. Review the planned changes, then run `classroom-sync`.

School administrators may restrict OAuth applications. A permission failure is reported for the affected course; it is not silently counted as a successful import.

## Database properties

| Property | Notion type |
| --- | --- |
| Assignment | Title |
| Course | Text |
| Due | Date |
| Status | Select |
| Submitted | Checkbox |
| Grade, Max Points | Number |
| Classroom Link | URL |
| Course ID, Coursework ID, Submission State | Text |
| Last Synced | Date |
| Priority, My Notes | Any suitable type; never written by this tool |

Status options: `Completed`, `Late`, `No Due Date`, `Missing`, `Due Soon`, `Upcoming`.

## Behavior

- Classroom deadlines are UTC timestamps, converted into `TRACKER_TIMEZONE` for display. Daylight saving and dates crossing midnight are covered by regression tests.
- Submitted work is completed. Otherwise Google's late flag takes priority, followed by missing and upcoming deadline rules.
- `DUE_SOON_DAYS` defaults to 3 and must be nonnegative.
- Duplicate IDs already in Notion stop the sync before writing. Resolve them explicitly rather than allowing an arbitrary row to win.
- Pages absent from the current Classroom result are left in Notion. The tool does not delete or archive historical work.
- A failed run may have updated some rows. Rerunning is supported, but do not run concurrent sync processes against the same data source.
- `--dry-run` still reads both services and can create or refresh the local OAuth token; it makes no Notion writes.

Run from the directory containing `.env`, `credentials.json`, and `token.json`, or set `TRACKER_CONFIG_DIR` to that directory. Credentials are excluded from Git. The token file is written with owner-only filesystem permissions on systems that support them.

## Development

```sh
python -m unittest discover -s tests -v
```

`tracker/classroom.py` handles Google authorization, pagination, and normalized assignments. `tracker/status.py` is the deadline policy. `tracker/notion.py` maps assignments to Notion properties. `tracker/sync.py` coordinates the run. Tests use mocks, never your accounts.

Automated checks cover status precedence, UTC conversion, invalid pagination, duplicate detection, non-JSON errors, protected fields, and dry-run writes. Live Google/Notion integration has not been exercised for this release.

## References

- [Classroom coursework fields](https://developers.google.com/workspace/classroom/reference/rest/v1/courses.courseWork)
- [Notion data source queries](https://developers.notion.com/reference/query-a-data-source)

MIT licensed. Google and Notion names identify the supported services; this is an independent project.
