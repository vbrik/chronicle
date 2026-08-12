"""Tests for chronicle's CLI argument parsing and main() integration."""

from pathlib import Path

import chronicle
import pytest


def test_parse_args_entry_words(monkeypatch):
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", "word1", "word2"])
    args = chronicle.parse_args()
    assert args.entry == ["word1", "word2"]
    assert args.config is None


def test_parse_args_explicit_config(monkeypatch):
    monkeypatch.setattr(
        chronicle.sys, "argv", ["chronicle", "--config", "/tmp/x.conf", "entry"]
    )
    args = chronicle.parse_args()
    assert args.config == Path("/tmp/x.conf")


def test_parse_args_requires_entry(monkeypatch, capsys):
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle"])
    with pytest.raises(SystemExit) as exc_info:
        chronicle.parse_args()
    assert exc_info.value.code == 2
    assert "usage" in capsys.readouterr().err


def test_parse_args_help(monkeypatch, capsys):
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", "-h"])
    with pytest.raises(SystemExit) as exc_info:
        chronicle.parse_args()
    assert exc_info.value.code == 0
    assert "usage" in capsys.readouterr().out


def _run_main(monkeypatch, argv):
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", *argv])
    return chronicle.main()


def test_main_creates_new_file(monkeypatch, tmp_path, freeze_date, capsys):
    freeze_date(2026, 8, 12)  # a Wednesday
    root = tmp_path / "journal"
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, ["my entry"])

    assert rc == 0
    quarter_file = root / "2026-q3.md"
    assert quarter_file.read_text() == (
        "# 2026 Q3\n## August\n\n### 2026-08-12, Wednesday\n- my entry\n"
    )
    assert capsys.readouterr().out == "- my entry\n"


def test_main_appends_to_existing_today_section(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    root.mkdir()
    quarter_file = root / "2026-q3.md"
    quarter_file.write_text(
        "# 2026 Q3\n## August\n\n### 2026-08-12, Wednesday\n- first entry\n"
    )
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, ["second entry"])

    assert rc == 0
    assert quarter_file.read_text() == (
        "# 2026 Q3\n"
        "## August\n"
        "\n"
        "### 2026-08-12, Wednesday\n"
        "- first entry\n"
        "- second entry\n"
    )


def test_main_existing_month_new_day(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    root.mkdir()
    quarter_file = root / "2026-q3.md"
    quarter_file.write_text(
        "# 2026 Q3\n## August\n\n### 2026-08-11, Tuesday\n- yesterday\n"
    )
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, ["today's entry"])

    assert rc == 0
    assert quarter_file.read_text() == (
        "# 2026 Q3\n"
        "## August\n"
        "\n"
        "### 2026-08-11, Tuesday\n"
        "- yesterday\n"
        "\n"
        "### 2026-08-12, Wednesday\n"
        "- today's entry\n"
    )
    # Month heading is not duplicated.
    assert quarter_file.read_text().count("## August") == 1


def test_main_trims_trailing_blank_lines(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    root.mkdir()
    quarter_file = root / "2026-q3.md"
    quarter_file.write_text(
        "# 2026 Q3\n## August\n\n### 2026-08-11, Tuesday\n- yesterday\n\n\n\n"
    )
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, ["today's entry"])

    assert rc == 0
    content = quarter_file.read_text()
    assert "\n\n\n" not in content


def test_main_empty_entry_rejected(monkeypatch, tmp_path, freeze_date, capsys):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, ["  ", ""])

    assert rc == 1
    assert "entry text is empty" in capsys.readouterr().err
    assert not (root / "2026-q3.md").exists()


def test_main_multi_word_entry_joined(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, ["hello", "world"])

    assert rc == 0
    assert "- hello world\n" in (root / "2026-q3.md").read_text()


def test_main_embedded_newline_collapsed(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, ["foo\nbar"])

    assert rc == 0
    assert "- foo bar\n" in (root / "2026-q3.md").read_text()


def test_main_explicit_config_missing_file_raises(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    missing_config = tmp_path / "does-not-exist.conf"

    with pytest.raises(SystemExit):
        _run_main(monkeypatch, ["--config", str(missing_config), "entry"])


def test_main_config_file_driven_root_dir(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text(f"[chronicle]\nroot_dir = {root}\n")

    rc = _run_main(monkeypatch, ["--config", str(config_path), "entry"])

    assert rc == 0
    assert (root / "2026-q3.md").exists()
