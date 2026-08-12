# chronicle

A small CLI for appending dated entries to a markdown work journal, organized
by year, quarter, month, and day.

## Usage

```
chronicle <entry text>
```

Appends `- <entry text>` under today's date heading in the current
quarter's journal file, creating the quarter file, month heading, and/or
day heading as needed.

Example:

```
$ chronicle cephs is broken again
- cephs is broken again
```

This produces (and extends) a file structured like:

```markdown
# 2026 Q3
## August
### 2026-08-12, Wednesday
- cephs is broken again
```

## Setup

Journal files live in `~/proj/notes/notes/chronicles/`, named
`<year>-q<quarter>.md` (e.g. `2026-q3.md`), currently hardcoded in
`chronicle` (`CHRONICLE_DIR`). Symlink the script onto your `PATH`, e.g.:

```
ln -s "$(pwd)/chronicle" ~/.local/bin/chronicle
```
