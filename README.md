# chronicle

A small CLI for appending dated entries to one or more markdown files —
work journal, inbox, or anything else you want organized by month and day.

## Usage

```
chronicle [KEY]
```

`KEY` selects which configured target file to write to (see Setup below);
if omitted, the first target in the config file is used. A target keyed
`*`, if configured, additionally collects a copy of every entry.

`chronicle` opens `$EDITOR` (defaulting to `vi`) on a temporary file
prefilled with two lines: `# <target file path>`, so you can see where
you're about to write, followed by `- `. For `vim`/`nvim` specifically, it
also opens straight into insert mode positioned right after the `- `
prefill; other editors are left to their normal startup behavior. When the
editor exits:

- the first line is dropped if it's still exactly `# <target file path>`
  (any other first line, including an edited or deleted header, is kept
  as part of the entry);
- of what remains, trailing whitespace is stripped from every line and
  leading/trailing newlines are removed to form today's entry (internal
  newlines are preserved verbatim);
- an empty result, or one unchanged from the `- ` prefill, means nothing
  is logged.

The entry is appended under today's date heading in the target file,
creating the month heading and/or day heading as needed.

Example:

```
$ chronicle
# ($EDITOR opens prefilled with "# /home/you/notes/chronicle/2026-q3.md\n- ";
#  you add text after the dash and save)
- cephs is broken again
```

This produces (and extends) a file structured like:

```markdown
## August

### 2026-08-12, Wednesday
- cephs is broken again
```

## Setup

Symlink the script onto your `PATH`, e.g.:

```
ln -s "$(pwd)/chronicle" ~/.local/bin/chronicle
```

Target files are configured under a `[targets]` section of a config file
(`~/.config/chronicle/chronicle.conf` by default, or the path given with
`--config`), mapping an arbitrary key to a full file path:

```ini
[targets]
0 = ~/proj/notes/notes/chronicles/2026-q3.md
1 = ~/proj/notes/notes/__inbox/_inbox.md
```

Keys are case-sensitive. `chronicle` with no key writes to the first entry
in this section (`0` above); `chronicle 1` writes to the inbox. Since the
key is just a config lookup, there's no automatic date-based file
rollover — update a target's path by hand (e.g. each new quarter) when
you want entries to start landing in a different file.

### Catch-all target: `*`

A target with the key `*` also receives a verbatim copy of every entry
written to any other target, giving you one combined log across all of
them:

```ini
[targets]
0 = ~/proj/notes/notes/chronicles/2026-q3.md
1 = ~/proj/notes/notes/__inbox/_inbox.md
* = ~/proj/notes/notes/everything.md
```

Here `chronicle 1` appends to both the inbox and `everything.md`, each
file getting its own month/day headings as needed. Otherwise `*` is an
ordinary target: `chronicle '*'` writes to it alone, and if it's listed
first it's the default. Quote it on the command line (`'*'` or `\*`) —
an unquoted `*` may be expanded by your shell into the current
directory's file names before `chronicle` ever sees it. If `*` points at the same file as the target
being written, the entry is written only once.

A target file doesn't need to have been written by `chronicle` before —
if it has no heading for today, one is appended at the end, leaving any
pre-existing content above untouched (and, if it used a different heading
style, unconverted).

If a key isn't configured (or the config file/section is missing
entirely), `chronicle` prints an error along with a copy-pasteable
`[targets]` template to add.
