"""Tests for wherewasi CLI."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from wherewasi.cli import _build_table, _format_date, _parse_datetime, _scan_projects


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


def test_build_table_empty():
    table = _build_table([])
    assert table.title == "Where Was I?"
    assert len(table.columns) == 2
    assert table.row_count == 0


def test_scan_with_mock_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test-project"
        project_dir.mkdir()
        lines = [
            json.dumps({"type": "summary", "summary": "Test session"}),
            json.dumps({
                "type": "user",
                "message": {"role": "user", "content": "hello world"},
                "cwd": "/tmp/test-project",
                "timestamp": "2026-01-19T01:00:00Z",
            }),
            json.dumps({
                "type": "assistant",
                "timestamp": "2026-01-19T02:00:00Z",
            }),
        ]
        (project_dir / "abc123.jsonl").write_text("\n".join(lines))

        with patch("wherewasi.cli.CLAUDE_PROJECTS_DIR", Path(tmpdir)):
            projects = _scan_projects()

        assert len(projects) == 1
        assert projects[0].name == "test-project"
        assert len(projects[0].sessions) == 1
        assert projects[0].sessions[0].first_prompt == "hello world"
