"""Where Was I - Claude Code session reporter."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from libcli import BaseCLI

__all__ = ["WhereWasICLI"]

CLAUDE_PROJECTS_DIR = Path("~/.claude/projects").expanduser()


@dataclass
class Session:
    """A single Claude Code session entry."""

    summary: str
    first_prompt: str
    modified: datetime
    created: datetime


@dataclass
class Project:
    """A Claude Code project with its sessions."""

    name: str
    path: str
    description: str
    sessions: list[Session] = field(default_factory=list)

    @property
    def last_active(self) -> datetime:
        """Return the most recent session modification time."""
        return max(s.modified for s in self.sessions)


def _parse_datetime(s: str) -> datetime:
    """Parse an ISO format datetime string."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _short_path(path: str) -> str:
    """Shorten a path by replacing the home directory with ~."""
    home = str(Path.home())
    if path.startswith(home):
        return "~" + path[len(home) :]
    return path


def _format_date(dt: datetime) -> str:
    """Format a datetime as 'Mon DD'."""
    return dt.strftime("%b %d").replace(" 0", "  ")


def _read_project_description(project_path: str) -> str:
    """Read the first meaningful line from a project's CLAUDE.md."""

    claude_md = Path(project_path) / "CLAUDE.md"
    if not claude_md.exists():
        return ""
    for line in claude_md.read_text(errors="replace").splitlines():
        line = line.strip()
        # Skip empty lines, the heading, and the boilerplate
        if not line:
            continue
        if line.startswith("# "):
            continue
        if line.startswith("This file provides guidance"):
            continue
        if line.startswith("## "):
            # Return section name content as description
            return line[3:].strip()
        return line
    return ""


def _scan_projects() -> list[Project]:
    """Scan ~/.claude/projects for session data."""

    projects: list[Project] = []

    if not CLAUDE_PROJECTS_DIR.exists():
        return projects

    for index_file in CLAUDE_PROJECTS_DIR.glob("*/sessions-index.json"):
        try:
            data = json.loads(index_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        entries = data.get("entries", [])
        if not entries:
            continue

        # Derive original path and project name
        original_path = data.get("originalPath", "")
        if not original_path:
            # Fall back to projectPath from first entry
            original_path = entries[0].get("projectPath", index_file.parent.name)
        name = Path(original_path).name

        description = _read_project_description(original_path)

        sessions: list[Session] = []
        for entry in entries:
            sessions.append(
                Session(
                    summary=entry.get("summary", ""),
                    first_prompt=entry.get("firstPrompt", ""),
                    modified=_parse_datetime(entry.get("modified", "1970-01-01T00:00:00Z")),
                    created=_parse_datetime(entry.get("created", "1970-01-01T00:00:00Z")),
                )
            )

        project = Project(
            name=name,
            path=original_path,
            description=description,
            sessions=sorted(sessions, key=lambda s: s.modified, reverse=True),
        )
        projects.append(project)

    # Sort projects by most recent session
    projects.sort(key=lambda p: p.last_active, reverse=True)
    return projects


def _format_plain(projects: list[Project]) -> str:
    """Format projects as plain text."""

    lines: list[str] = []

    # Header
    header = f"{'Project':<17}{'Last Active':<13}Directory"
    separator = f"{'───────':<17}{'───────────':<13}─────────"
    lines.append(header)
    lines.append(separator)

    for project in projects:
        short = _short_path(project.path)
        date = _format_date(project.last_active)
        lines.append(f"{project.name:<17}{date:<13}{short}")

        if project.description:
            lines.append(f"  {project.description}")

        lines.append("  Sessions:")
        for session in project.sessions:
            sdate = _format_date(session.modified)
            summary = session.summary or "(no summary)"
            lines.append(f"    {sdate}  {summary}")
            if session.first_prompt:
                prompt = session.first_prompt
                if len(prompt) > 70:
                    prompt = prompt[:67] + "..."
                lines.append(f'            "{prompt}"')

        lines.append("")

    return "\n".join(lines)


def _format_markdown(projects: list[Project]) -> str:
    """Format projects as Markdown."""

    lines: list[str] = []
    lines.append("# Where Was I?")
    lines.append("")

    for project in projects:
        short = _short_path(project.path)
        date = _format_date(project.last_active)
        lines.append(f"## {project.name}")
        lines.append("")
        lines.append(f"**Last Active:** {date} | **Directory:** `{short}`")
        lines.append("")

        if project.description:
            lines.append(f"*{project.description}*")
            lines.append("")

        lines.append("### Sessions")
        lines.append("")
        for session in project.sessions:
            sdate = _format_date(session.modified)
            summary = session.summary or "(no summary)"
            lines.append(f"- **{sdate}** — {summary}")
            if session.first_prompt:
                prompt = session.first_prompt
                if len(prompt) > 70:
                    prompt = prompt[:67] + "..."
                lines.append(f'  > "{prompt}"')

        lines.append("")

    return "\n".join(lines)


class WhereWasICLI(BaseCLI):
    """Where Was I - Claude Code session reporter."""

    config = {
        "dist-name": "rlane-wherewasi",
    }

    def init_parser(self) -> None:
        """Initialize argument parser."""

        self.ArgumentParser(
            prog=__package__,
            description="Report recent Claude Code sessions and projects.",
        )

    def add_arguments(self) -> None:
        """Add arguments to parser."""

        self.parser.add_argument(
            "--markdown",
            "-m",
            action="store_true",
            default=False,
            help="output in Markdown format",
        )

        self.parser.add_argument(
            "-n",
            type=int,
            default=0,
            metavar="NUM",
            help="limit to NUM most recent projects (default: all)",
        )

    def main(self) -> None:
        """Command line interface entry point (method)."""

        projects = _scan_projects()

        if self.options.n > 0:
            projects = projects[: self.options.n]

        if self.options.markdown:
            output = _format_markdown(projects)
        else:
            output = _format_plain(projects)

        print(output)


def main(args: list[str] | None = None) -> None:
    """Command line interface entry point (function)."""
    WhereWasICLI(args).main()
