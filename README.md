# TU Delft — Sabbatical Research

A lightweight research management system for tracking research notes and memos
during a sabbatical at TU Delft.

---

## Directory Structure

```
TUDelft/
├── research/        # Research notes (Markdown)
├── memos/           # Memos (Markdown)
├── templates/       # Templates for notes and memos
│   ├── research_note.md
│   └── memo.md
├── research.py      # CLI management tool
└── README.md
```

---

## Requirements

- Python 3.7+

No external dependencies are needed.

---

## Usage

All commands are run via `python research.py` (or `./research.py` after making it executable).

### Create a research note

```bash
python research.py note "My Research Topic"
python research.py note "Deep Learning for CFD" --tags deep-learning CFD simulation
```

Creates a new Markdown file in `research/` pre-filled from the research note template.

### Create a memo

```bash
python research.py memo "Project kickoff meeting summary"
python research.py memo "Budget request Q2" --to "Prof. Janssen"
```

Creates a new Markdown file in `memos/` pre-filled from the memo template.

### List notes and memos

```bash
python research.py list           # list everything
python research.py list notes     # list only research notes
python research.py list memos     # list only memos
```

### Search

```bash
python research.py search "turbulence"
```

Searches all notes and memos for the keyword (case-insensitive) and prints
each matching file and line.

---

## Templates

Templates live in `templates/`. Edit them to suit your workflow.

| Template | Used for |
|----------|----------|
| `research_note.md` | Research literature notes, ideas, experiments |
| `memo.md` | Internal memos, meeting notes, action items |

---

## File Naming

Files are named automatically as `YYYY-MM-DD-<slug>.md`, e.g.

```
research/2026-04-15-deep-learning-for-cfd.md
memos/2026-04-15-budget-request-q2.md
```
