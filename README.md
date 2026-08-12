# chronicle

A small CLI for appending dated log entries to a running work journal in markdown.

## Usage

```
chronicle <entry text>
```

Appends `- <entry text>` under today's `### YYYY-MM-DD` section of the
target file, creating the day and/or month (`## Month`) headers if they
don't exist yet.

Example:

```
$ chronicle cephs is broken again
- cephs is broken again
```

## Setup

The target file is currently hardcoded in `chronicle` (`CHRONICLE_FILE`).
Symlink the script onto your `PATH`, e.g.:

```
ln -s "$(pwd)/chronicle" ~/.local/bin/chronicle
```
