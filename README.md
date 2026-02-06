# wherewasi

Report recent Claude Code sessions and projects.

Scans `~/.claude/projects/` for session data and displays a summary of your
recent activity across all projects.

## Installation

```bash
pip install rlane-wherewasi
```

## Usage

```bash
wherewasi          # show all projects
wherewasi -n 5     # show 5 most recent projects
wherewasi -m       # output in Markdown format
```

## Options

| Option | Description |
|--------|-------------|
| `-n NUM` | Limit to NUM most recent projects (default: all) |
| `-m`, `--markdown` | Output in Markdown format |

## License

MIT
