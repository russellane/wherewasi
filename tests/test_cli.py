"""Tests for wherewasi CLI."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from wherewasi.cli import _format_date, _format_plain, _parse_datetime, _scan_projects


def test_parse_datetime():
    dt = _parse_datetime("2026-01-19T01:51:54.536Z")
    assert dt.year == 2026
    assert dt.month == 1
    assert dt.day == 19


def test_format_date():
    dt = _parse_datetime("2026-01-19T01:51:54.536Z")
    result = _format_date(dt)
    assert "Jan" in result
    assert "19" in result


def test_scan_projects_with_real_data():
    projects = _scan_projects()
    # Should find at least one project if claude data exists
    assert isinstance(projects, list)


def test_format_plain_empty():
    output = _format_plain([])
    assert "Project" in output
    assert "Last Active" in output


def test_scan_with_mock_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test-project"
        project_dir.mkdir()
        index = {
            "version": 1,
            "entries": [
                {
                    "sessionId": "abc123",
                    "firstPrompt": "hello world",
                    "summary": "Test session",
                    "created": "2026-01-19T01:00:00Z",
                    "modified": "2026-01-19T02:00:00Z",
                }
            ],
            "originalPath": "/tmp/test-project",
        }
        (project_dir / "sessions-index.json").write_text(json.dumps(index))

        with patch("wherewasi.cli.CLAUDE_PROJECTS_DIR", Path(tmpdir)):
            projects = _scan_projects()

        assert len(projects) == 1
        assert projects[0].name == "test-project"
        assert len(projects[0].sessions) == 1
        assert projects[0].sessions[0].first_prompt == "hello world"
