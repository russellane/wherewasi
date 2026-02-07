"""Where Was I - Claude Code session reporter."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from libcli import BaseCLI
from rich import box
from rich.console import Console
from rich.table import Table

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


def _read_jsonl_session(path: Path) -> tuple[str, Session] | None:
    """Read session metadata from a .jsonl file. Returns (cwd, Session) or None."""

    summary = ""
    first_prompt = ""
    cwd = ""
    first_ts: str | None = None

    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)

        # Read head for summary, first prompt, cwd, and first timestamp.
        with path.open(errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if first_ts is None:
                    ts = rec.get("timestamp")
                    if ts:
                        first_ts = ts
                if rec.get("type") == "summary":
                    summary = rec.get("summary", "")
                if rec.get("type") == "user" and not first_prompt:
                    content = rec.get("message", {}).get("content", "")
                    if isinstance(content, str):
                        first_prompt = content
                    if not cwd:
                        cwd = rec.get("cwd", "")
                if first_ts and first_prompt and summary:
                    break
    except OSError:
        return None

    if first_ts is None:
        return None

    return cwd, Session(
        summary=summary,
        first_prompt=first_prompt,
        modified=mtime,
        created=_parse_datetime(first_ts),
    )


def _scan_projects() -> list[Project]:
    """Scan ~/.claude/projects for session data."""

    projects: dict[str, Project] = {}

    if not CLAUDE_PROJECTS_DIR.exists():
        return []

    for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        for jsonl_file in project_dir.glob("*.jsonl"):
            result = _read_jsonl_session(jsonl_file)
            if not result:
                continue
            cwd, session = result

            if cwd not in projects:
                projects[cwd] = Project(
                    name=Path(cwd).name or cwd,
                    path=cwd,
                    description=_read_project_description(cwd),
                    sessions=[],
                )
            projects[cwd].sessions.append(session)

    for project in projects.values():
        project.sessions.sort(key=lambda s: s.modified, reverse=True)

    result = list(projects.values())
    result.sort(key=lambda p: p.last_active, reverse=True)
    return result


def _build_table(projects: list[Project]) -> Table:
    """Format projects as a rich Table."""

    table = Table(title="Where Was I?", expand=True)
    table.add_column("Directory", style="dim", no_wrap=True)
    table.add_column("Sessions", ratio=1)

    for i, project in enumerate(projects):
        short = _short_path(project.path)

        sub = Table(show_header=False, show_edge=False, box=box.HORIZONTALS, show_lines=True, pad_edge=False, expand=True)
        sub.add_column(ratio=1)
        for session in project.sessions:
            sdate = _format_date(session.modified)
            summary = session.summary or "(no summary)"
            cell = f"{sdate}  {summary}"
            if session.first_prompt:
                prompt = session.first_prompt
                if len(prompt) > 70:
                    prompt = prompt[:67] + "..."
                cell += f'\n  "{prompt}"'
            sub.add_row(cell)

        table.add_row(short, sub)
        if i < len(projects) - 1:
            table.add_section()

    return table


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
            print(_format_markdown(projects))
        else:
            Console().print(_build_table(projects))


def main(args: list[str] | None = None) -> None:
    """Command line interface entry point (function)."""
    WhereWasICLI(args).main()
