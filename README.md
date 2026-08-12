# chronicle

A small CLI for appending dated entries to a markdown work journal, organized
by year, quarter, month, and day.

## Usage

```
chronicle <entry text>
```

Appends `- <entry text>` under today's date heading in the current
quarter's journal file, creating the quarter file, month heading, and/or
day heading as needed. Run `chronicle -h` for full usage.

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

Symlink the script onto your `PATH`, e.g.:

```
ln -s "$(pwd)/chronicle" ~/.local/bin/chronicle
```

Journal files are named `<year>-q<quarter>.md` (e.g. `2026-q3.md`) inside a
root directory, resolved in this order:

1. the `CHRONICLE_ROOT_DIR` environment variable
2. the `root_dir` setting in a config file, `~/.config/chronicle/chronicle.conf`
   by default, or the path given with `--config`:
   ```ini
   [chronicle]
   root_dir = ~/proj/notes/notes/chronicles
   ```

If neither is set, `chronicle` interactively prompts for a root directory
and saves it to the default config file location.
