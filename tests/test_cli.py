"""Tests for chronicle's CLI argument parsing and main() integration."""

from pathlib import Path

import chronicle
import pytest


def _configure_target(target_path, key="0"):
    """Point the (test-isolated) default config file's target `key` at `target_path`."""
    chronicle.DEFAULT_CONFIG_PATH.write_text(f"[targets]\n{key} = {target_path}\n")


def test_parse_args_no_positional(monkeypatch):
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle"])
    args = chronicle.parse_args()
    assert args.target is None
    assert args.config is None


def test_parse_args_explicit_target(monkeypatch):
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", "1"])
    args = chronicle.parse_args()
    assert args.target == "1"


def test_parse_args_explicit_config(monkeypatch):
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", "--config", "/tmp/x.conf"])
    args = chronicle.parse_args()
    assert args.config == Path("/tmp/x.conf")


def test_parse_args_help(monkeypatch, capsys):
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", "-h"])
    with pytest.raises(SystemExit) as exc_info:
        chronicle.parse_args()
    assert exc_info.value.code == 0
    assert "usage" in capsys.readouterr().out


def _run_main(monkeypatch, argv, editor_content="my entry"):
    """Run main() with a mocked editor returning `editor_content`."""
    monkeypatch.setattr(chronicle, "edit_entry", lambda path: editor_content)
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", *argv])
    return chronicle.main()


def test_main_creates_new_file(monkeypatch, tmp_path, freeze_date, capsys):
    freeze_date(2026, 8, 12)  # a Wednesday
    target_file = tmp_path / "journal" / "target.md"
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="my entry")

    assert rc == 0
    assert target_file.read_text() == (
        "## August\n\n### 2026-08-12, Wednesday\nmy entry\n"
    )
    assert capsys.readouterr().out == "my entry\n"


def test_main_appends_to_existing_today_section(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    target_file.write_text("## August\n\n### 2026-08-12, Wednesday\nfirst entry\n")
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="second entry")

    assert rc == 0
    assert target_file.read_text() == (
        "## August\n\n### 2026-08-12, Wednesday\nfirst entry\nsecond entry\n"
    )


def test_main_existing_month_new_day(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    target_file.write_text("## August\n\n### 2026-08-11, Tuesday\nyesterday\n")
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="today's entry")

    assert rc == 0
    assert target_file.read_text() == (
        "## August\n"
        "\n"
        "### 2026-08-11, Tuesday\n"
        "yesterday\n"
        "\n"
        "### 2026-08-12, Wednesday\n"
        "today's entry\n"
    )
    # Month heading is not duplicated.
    assert target_file.read_text().count("## August") == 1


def test_main_trims_trailing_blank_lines(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    target_file.write_text("## August\n\n### 2026-08-11, Tuesday\nyesterday\n\n\n\n")
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="today's entry")

    assert rc == 0
    content = target_file.read_text()
    assert "\n\n\n" not in content


def test_main_empty_editor_content_no_op(monkeypatch, tmp_path, freeze_date, capsys):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="")

    assert rc == 0
    assert not target_file.exists()
    assert capsys.readouterr().out == ""


def test_main_whitespace_only_editor_content_no_op(
    monkeypatch, tmp_path, freeze_date, capsys
):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="   \n  \n")

    assert rc == 0
    assert not target_file.exists()


def test_main_dash_prefill_with_added_text(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="- cephs is broken again")

    assert rc == 0
    assert target_file.read_text() == (
        "## August\n\n### 2026-08-12, Wednesday\n- cephs is broken again\n"
    )


def test_main_dash_prefill_with_trailing_newline_from_real_editor(
    monkeypatch, tmp_path, freeze_date
):
    # A real editor writes a trailing newline on save, unlike the bare
    # strings used elsewhere in this suite.
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="- typed\n")

    assert rc == 0
    assert target_file.read_text() == (
        "## August\n\n### 2026-08-12, Wednesday\n- typed\n"
    )


def test_main_unmodified_dash_prefill_no_op(monkeypatch, tmp_path, freeze_date, capsys):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="- ")

    assert rc == 0
    assert not target_file.exists()
    assert capsys.readouterr().out == ""


def test_main_unmodified_header_and_dash_prefill_no_op(
    monkeypatch, tmp_path, freeze_date, capsys
):
    # The actual raw shape produced by a quit-without-editing: the
    # sanity-check header line still intact, followed by the "- " prefill.
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content=f"# {target_file.resolve()}\n- ")

    assert rc == 0
    assert not target_file.exists()
    assert capsys.readouterr().out == ""


def test_main_strips_leading_and_trailing_newlines(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="\n\nhello world\n\n")

    assert rc == 0
    assert "hello world\n" in target_file.read_text()


def test_main_multiline_content_preserved_verbatim(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="first line\nsecond line\nthird")

    assert rc == 0
    content = target_file.read_text()
    assert "first line\nsecond line\nthird\n" in content


def test_main_explicit_config_missing_file_raises(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    missing_config = tmp_path / "does-not-exist.conf"

    with pytest.raises(SystemExit):
        _run_main(monkeypatch, ["--config", str(missing_config)], editor_content="x")


def test_main_explicit_config_flag(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text(f"[targets]\n0 = {target_file}\n")

    rc = _run_main(monkeypatch, ["--config", str(config_path)], editor_content="entry")

    assert rc == 0
    assert target_file.exists()


def test_main_explicit_config_and_target_together(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    target0 = tmp_path / "target0.md"
    target1 = tmp_path / "target1.md"
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text(f"[targets]\n0 = {target0}\n1 = {target1}\n")

    rc = _run_main(
        monkeypatch, ["--config", str(config_path), "1"], editor_content="entry"
    )

    assert rc == 0
    assert not target0.exists()
    assert target1.exists()


def test_main_selects_target_by_key(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    target0 = tmp_path / "target0.md"
    target1 = tmp_path / "target1.md"
    chronicle.DEFAULT_CONFIG_PATH.write_text(
        f"[targets]\n0 = {target0}\n1 = {target1}\n"
    )

    rc = _run_main(monkeypatch, ["1"], editor_content="entry for one")

    assert rc == 0
    assert not target0.exists()
    assert target1.read_text() == (
        "## August\n\n### 2026-08-12, Wednesday\nentry for one\n"
    )


def test_main_default_uses_first_configured_target(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    # Deliberately out-of-numeric-order keys: "first entry" means file order.
    chronicle.DEFAULT_CONFIG_PATH.write_text(f"[targets]\n1 = {first}\n0 = {second}\n")

    rc = _run_main(monkeypatch, [], editor_content="entry")

    assert rc == 0
    assert first.exists()
    assert not second.exists()


def test_main_repeated_month_name_across_years_gets_own_heading(
    monkeypatch, tmp_path, freeze_date
):
    # A long-lived target file (no per-quarter rollover) can revisit a
    # month name. Today's month heading must not be skipped just because
    # the same name appears earlier in the file for a different year.
    freeze_date(2027, 9, 4)  # a Saturday
    target_file = tmp_path / "target.md"
    target_file.write_text("## September\n\n### 2026-09-04, Friday\nlast year\n")
    _configure_target(target_file)

    rc = _run_main(monkeypatch, [], editor_content="this year")

    assert rc == 0
    # A newly-appended month heading directly follows prior content (no
    # blank line); only the day heading gets one, per existing convention.
    assert target_file.read_text() == (
        "## September\n"
        "\n"
        "### 2026-09-04, Friday\n"
        "last year\n"
        "## September\n"
        "\n"
        "### 2027-09-04, Saturday\n"
        "this year\n"
    )


def test_main_unknown_target_key_exits(monkeypatch, tmp_path, capsys):
    _configure_target(tmp_path / "target.md", key="0")
    monkeypatch.setattr(chronicle, "edit_entry", lambda path: "should not be reached")
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", "9"])

    with pytest.raises(SystemExit) as exc_info:
        chronicle.main()

    assert exc_info.value.code == 1
    assert '"9"' in capsys.readouterr().err


def _configure_targets(targets):
    """Write a [targets] section mapping each key in `targets` to its path, in order."""
    body = "".join(f"{key} = {path}\n" for key, path in targets.items())
    chronicle.DEFAULT_CONFIG_PATH.write_text(f"[targets]\n{body}")


def test_main_mirrors_entry_into_all_target(monkeypatch, tmp_path, freeze_date, capsys):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    all_file = tmp_path / "all.md"
    _configure_targets({"0": target_file, "*": all_file})

    rc = _run_main(monkeypatch, ["0"], editor_content="- my entry")

    assert rc == 0
    expected = "## August\n\n### 2026-08-12, Wednesday\n- my entry\n"
    assert target_file.read_text() == expected
    assert all_file.read_text() == expected
    # Echoed once, not once per file written.
    assert capsys.readouterr().out == "- my entry\n"


def test_main_mirrors_entry_for_default_key(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    all_file = tmp_path / "all.md"
    _configure_targets({"0": target_file, "*": all_file})

    rc = _run_main(monkeypatch, [], editor_content="my entry")

    assert rc == 0
    assert target_file.read_text().endswith("my entry\n")
    assert all_file.read_text().endswith("my entry\n")


def test_main_all_target_gets_its_own_headings(monkeypatch, tmp_path, freeze_date):
    # The mirror's month/day headings depend on its own content, not the
    # primary target's: here the primary already has today's section while
    # "*" was last written in an earlier month.
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    target_file.write_text("## August\n\n### 2026-08-12, Wednesday\nearlier\n")
    all_file = tmp_path / "all.md"
    all_file.write_text("## July\n\n### 2026-07-31, Friday\nold\n")
    _configure_targets({"1": target_file, "*": all_file})

    rc = _run_main(monkeypatch, ["1"], editor_content="new")

    assert rc == 0
    assert target_file.read_text() == (
        "## August\n\n### 2026-08-12, Wednesday\nearlier\nnew\n"
    )
    assert all_file.read_text() == (
        "## July\n"
        "\n"
        "### 2026-07-31, Friday\n"
        "old\n"
        "## August\n"
        "\n"
        "### 2026-08-12, Wednesday\n"
        "new\n"
    )


def test_main_accumulates_entries_from_several_targets_in_all_target(
    monkeypatch, tmp_path, freeze_date
):
    freeze_date(2026, 8, 12)
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    all_file = tmp_path / "all.md"
    _configure_targets({"0": first, "1": second, "*": all_file})

    _run_main(monkeypatch, ["0"], editor_content="- from zero")
    _run_main(monkeypatch, ["1"], editor_content="- from one")

    assert first.read_text().endswith("### 2026-08-12, Wednesday\n- from zero\n")
    assert second.read_text().endswith("### 2026-08-12, Wednesday\n- from one\n")
    assert all_file.read_text() == (
        "## August\n\n### 2026-08-12, Wednesday\n- from zero\n- from one\n"
    )


def test_main_all_target_written_directly_only_once(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    all_file = tmp_path / "all.md"
    _configure_targets({"0": target_file, "*": all_file})

    rc = _run_main(monkeypatch, ["*"], editor_content="direct")

    assert rc == 0
    assert all_file.read_text() == "## August\n\n### 2026-08-12, Wednesday\ndirect\n"
    assert not target_file.exists()


def test_main_all_target_same_file_as_key_written_once(
    monkeypatch, tmp_path, freeze_date
):
    freeze_date(2026, 8, 12)
    shared = tmp_path / "shared.md"
    _configure_targets({"0": shared, "*": shared})

    rc = _run_main(monkeypatch, ["0"], editor_content="once")

    assert rc == 0
    assert shared.read_text() == "## August\n\n### 2026-08-12, Wednesday\nonce\n"


def test_main_blank_entry_writes_neither_target_nor_all_target(
    monkeypatch, tmp_path, freeze_date
):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    all_file = tmp_path / "all.md"
    _configure_targets({"0": target_file, "*": all_file})

    rc = _run_main(monkeypatch, ["0"], editor_content="- ")

    assert rc == 0
    assert not target_file.exists()
    assert not all_file.exists()


def test_main_all_target_creates_missing_parent_dirs(
    monkeypatch, tmp_path, freeze_date
):
    freeze_date(2026, 8, 12)
    all_file = tmp_path / "nested" / "dir" / "all.md"
    _configure_targets({"0": tmp_path / "target.md", "*": all_file})

    rc = _run_main(monkeypatch, ["0"], editor_content="entry")

    assert rc == 0
    assert all_file.read_text().endswith("entry\n")


def test_main_editor_header_names_primary_target_only(
    monkeypatch, tmp_path, freeze_date
):
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    _configure_targets({"0": target_file, "*": tmp_path / "all.md"})
    seen = []

    def fake_edit_entry(path):
        seen.append(path)
        return "entry"

    monkeypatch.setattr(chronicle, "edit_entry", fake_edit_entry)
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", "0"])
    chronicle.main()

    assert seen == [target_file.resolve()]


def test_main_strips_injected_header_line_end_to_end(
    monkeypatch, tmp_path, freeze_date
):
    # Exercises the real edit_entry -> strip_target_header_line -> main
    # pipeline (no mocked editor), confirming the sanity-check header line
    # never ends up in the written file.
    freeze_date(2026, 8, 12)
    target_file = tmp_path / "target.md"
    _configure_target(target_file)

    editor = tmp_path / "editor.sh"
    editor.write_text(
        "#!/bin/sh\n"
        'head -n 1 "$1" > "$1.tmp"\n'
        'echo "- integration entry" >> "$1.tmp"\n'
        'mv "$1.tmp" "$1"\n'
    )
    editor.chmod(0o755)
    monkeypatch.setenv("EDITOR", str(editor))
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle"])

    rc = chronicle.main()

    assert rc == 0
    content = target_file.read_text()
    assert str(target_file.resolve()) not in content
    assert content == "## August\n\n### 2026-08-12, Wednesday\n- integration entry\n"


def test_edit_entry_uses_env_editor(monkeypatch, tmp_path):
    captured = {}
    editor = tmp_path / "myeditor.sh"
    editor.write_text("#!/bin/sh\necho 'editor ran' > \"$1\"\n")
    editor.chmod(0o755)
    monkeypatch.setenv("EDITOR", str(editor))

    def fake_run(cmd, check):
        captured["cmd"] = cmd
        # Simulate editor writing content to the temp file path (last arg).
        with open(cmd[-1], "w") as f:
            f.write("from editor\n")

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    result = chronicle.edit_entry(tmp_path / "target.md")

    assert result == "from editor\n"
    assert captured["cmd"][0] == str(editor)


def test_edit_entry_falls_back_to_vi_when_editor_unset(monkeypatch, tmp_path):
    monkeypatch.delenv("EDITOR", raising=False)
    captured = {}

    def fake_run(cmd, check):
        captured["cmd"] = cmd
        with open(cmd[-1], "w") as f:
            f.write("vi content")

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    result = chronicle.edit_entry(tmp_path / "target.md")

    assert captured["cmd"][0] == "vi"
    assert result == "vi content"


def test_edit_editor_with_args(monkeypatch, tmp_path):
    editor = tmp_path / "editor.sh"
    editor.write_text('#!/bin/sh\necho x > "$1"\n')
    editor.chmod(0o755)
    monkeypatch.setenv("EDITOR", f"{editor} --flag --wait")

    captured = {}

    def fake_run(cmd, check):
        captured["cmd"] = cmd
        with open(cmd[-1], "w") as f:
            f.write("ok")

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    chronicle.edit_entry(tmp_path / "target.md")

    assert captured["cmd"] == [str(editor), "--flag", "--wait", captured["cmd"][-1]]


def test_edit_entry_prefills_temp_file_with_target_header_and_dash(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("EDITOR", raising=False)
    target = tmp_path / "target.md"
    captured = {}

    def fake_run(cmd, check):
        with open(cmd[-1], encoding="utf-8") as f:
            captured["initial"] = f.read()
        with open(cmd[-1], "w") as f:
            f.write("ok")

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    chronicle.edit_entry(target)

    assert captured["initial"] == f"# {target}\n- "


def test_edit_entry_adds_cursor_flags_for_vim(monkeypatch, tmp_path):
    monkeypatch.setenv("EDITOR", "vim")
    captured = {}

    def fake_run(cmd, check):
        captured["cmd"] = cmd
        with open(cmd[-1], "w") as f:
            f.write("- typed\n")

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    chronicle.edit_entry(tmp_path / "target.md")

    assert captured["cmd"][:-1] == ["vim", "-c", "$", "-c", "startinsert!"]


def test_edit_entry_cursor_flags_precede_user_supplied_args(monkeypatch, tmp_path):
    # EDITOR values ending in an option terminator like "--" would make vim
    # treat flags appended after it as filenames instead of options; cursor
    # flags must be inserted right after the executable, not appended last.
    monkeypatch.setenv("EDITOR", "vim --")
    captured = {}

    def fake_run(cmd, check):
        captured["cmd"] = cmd
        with open(cmd[-1], "w") as f:
            f.write("ok")

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    chronicle.edit_entry(tmp_path / "target.md")

    assert captured["cmd"] == [
        "vim",
        "-c",
        "$",
        "-c",
        "startinsert!",
        "--",
        captured["cmd"][-1],
    ]


def test_edit_entry_no_cursor_flags_for_unrecognized_editor(monkeypatch, tmp_path):
    editor = tmp_path / "editor.sh"
    editor.write_text('#!/bin/sh\necho x > "$1"\n')
    editor.chmod(0o755)
    monkeypatch.setenv("EDITOR", str(editor))
    captured = {}

    def fake_run(cmd, check):
        captured["cmd"] = cmd
        with open(cmd[-1], "w") as f:
            f.write("ok")

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    chronicle.edit_entry(tmp_path / "target.md")

    assert captured["cmd"] == [str(editor), captured["cmd"][-1]]


def test_edit_entry_cleans_up_temp_file(monkeypatch, tmp_path):
    monkeypatch.delenv("EDITOR", raising=False)

    created_paths = []

    def fake_run(cmd, check):
        created_paths.append(cmd[-1])

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    chronicle.edit_entry(tmp_path / "target.md")

    import os

    assert all(not os.path.exists(p) for p in created_paths)
