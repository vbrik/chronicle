"""Tests for chronicle's config-file I/O and root-dir resolution."""

import configparser

import chronicle
import pytest


def test_load_config_parser_valid_ini(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[chronicle]\nroot_dir = /some/dir\n")
    parser = chronicle.load_config_parser(config_path)
    assert parser.get("chronicle", "root_dir") == "/some/dir"


def test_load_config_parser_nonexistent_path(tmp_path):
    config_path = tmp_path / "does-not-exist.conf"
    parser = chronicle.load_config_parser(config_path)
    assert parser.sections() == []


def test_load_config_parser_malformed_ini(tmp_path, capsys):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("no_section_header = oops\n")
    with pytest.raises(SystemExit) as exc_info:
        chronicle.load_config_parser(config_path)
    assert exc_info.value.code == 1
    assert str(config_path) in capsys.readouterr().err


def test_read_config_root_dir_missing_file(tmp_path):
    assert chronicle.read_config_root_dir(tmp_path / "missing.conf") is None


def test_read_config_root_dir_present(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[chronicle]\nroot_dir = /some/dir\n")
    assert chronicle.read_config_root_dir(config_path) == "/some/dir"


def test_read_config_root_dir_section_missing(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[other]\nkey = value\n")
    assert chronicle.read_config_root_dir(config_path) is None


def test_read_config_root_dir_key_missing(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[chronicle]\nother_key = value\n")
    assert chronicle.read_config_root_dir(config_path) is None


def test_read_config_root_dir_malformed_propagates_exit(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("no_section_header = oops\n")
    with pytest.raises(SystemExit):
        chronicle.read_config_root_dir(config_path)


def test_write_config_root_dir_creates_missing_parents(tmp_path):
    config_path = tmp_path / "nested" / "dir" / "chronicle.conf"
    chronicle.write_config_root_dir(config_path, "/some/dir")
    assert config_path.exists()
    assert chronicle.read_config_root_dir(config_path) == "/some/dir"


def test_write_config_root_dir_preserves_other_settings(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[chronicle]\nroot_dir = /old/dir\n\n[other]\nkey = value\n")
    chronicle.write_config_root_dir(config_path, "/new/dir")

    parser = configparser.ConfigParser()
    parser.read(config_path)
    assert parser.get("chronicle", "root_dir") == "/new/dir"
    assert parser.get("other", "key") == "value"


def test_write_config_root_dir_overwrites_existing_value(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[chronicle]\nroot_dir = /old/dir\n")
    chronicle.write_config_root_dir(config_path, "/new/dir")
    assert chronicle.read_config_root_dir(config_path) == "/new/dir"


def test_prompt_for_root_dir_non_interactive_exits(tmp_path, capsys):
    config_path = tmp_path / "chronicle.conf"
    with pytest.raises(SystemExit) as exc_info:
        chronicle.prompt_for_root_dir(config_path)
    assert exc_info.value.code == 1
    stderr = capsys.readouterr().err
    assert chronicle.ENV_VAR in stderr
    assert chronicle.CONFIG_KEY in stderr
    assert chronicle.CONFIG_SECTION in stderr
    assert not config_path.exists()


def test_prompt_for_root_dir_blank_answer_exits(monkeypatch, tmp_path):
    config_path = tmp_path / "chronicle.conf"
    monkeypatch.setattr(chronicle.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "   ")
    with pytest.raises(SystemExit) as exc_info:
        chronicle.prompt_for_root_dir(config_path)
    assert exc_info.value.code == 1
    assert not config_path.exists()


def test_prompt_for_root_dir_valid_answer_writes_config(monkeypatch, tmp_path):
    config_path = tmp_path / "chronicle.conf"
    answer_dir = tmp_path / "journal"
    monkeypatch.setattr(chronicle.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: str(answer_dir))

    result = chronicle.prompt_for_root_dir(config_path)

    assert result == answer_dir.expanduser().resolve()
    assert chronicle.read_config_root_dir(config_path) == str(answer_dir)


def test_prompt_for_root_dir_expands_tilde(monkeypatch, tmp_path):
    config_path = tmp_path / "chronicle.conf"
    monkeypatch.setattr(chronicle.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "~/journal")

    result = chronicle.prompt_for_root_dir(config_path)

    assert "~" not in str(result)
    assert result.is_absolute()


def test_resolve_chronicle_dir_env_var_wins_over_missing_explicit_config(
    monkeypatch, tmp_path
):
    monkeypatch.setenv(chronicle.ENV_VAR, str(tmp_path / "from-env"))
    missing_config = tmp_path / "does-not-exist.conf"

    result = chronicle.resolve_chronicle_dir(
        missing_config, config_path_is_explicit=True
    )

    assert result == (tmp_path / "from-env").resolve()


def test_resolve_chronicle_dir_explicit_missing_config_exits(
    monkeypatch, tmp_path, capsys
):
    missing_config = tmp_path / "does-not-exist.conf"
    with pytest.raises(SystemExit) as exc_info:
        chronicle.resolve_chronicle_dir(missing_config, config_path_is_explicit=True)
    assert exc_info.value.code == 1
    assert "config file not found" in capsys.readouterr().err


def test_resolve_chronicle_dir_explicit_config_with_value(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    root = tmp_path / "journal"
    config_path.write_text(f"[chronicle]\nroot_dir = {root}\n")

    result = chronicle.resolve_chronicle_dir(config_path, config_path_is_explicit=True)

    assert result == root.resolve()


def test_resolve_chronicle_dir_default_missing_falls_through_to_prompt(tmp_path):
    # Non-explicit + missing file is not a hard error; it falls through to
    # the prompt, which (stdin is non-interactive, per the autouse fixture)
    # exits cleanly rather than raising for a bad reason.
    missing_config = tmp_path / "does-not-exist.conf"
    with pytest.raises(SystemExit) as exc_info:
        chronicle.resolve_chronicle_dir(missing_config, config_path_is_explicit=False)
    assert exc_info.value.code == 1


def test_resolve_chronicle_dir_reaches_prompt_when_all_else_absent(
    monkeypatch, tmp_path
):
    missing_config = tmp_path / "does-not-exist.conf"
    called = {}

    def fake_prompt(config_path):
        called["config_path"] = config_path
        return tmp_path / "prompted"

    monkeypatch.setattr(chronicle, "prompt_for_root_dir", fake_prompt)

    result = chronicle.resolve_chronicle_dir(
        missing_config, config_path_is_explicit=False
    )

    assert called["config_path"] == missing_config
    assert result == tmp_path / "prompted"


def test_resolve_chronicle_dir_empty_config_value_falls_through_to_prompt(
    monkeypatch, tmp_path
):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[chronicle]\nroot_dir = \n")
    monkeypatch.setattr(
        chronicle, "prompt_for_root_dir", lambda config_path: tmp_path / "prompted"
    )

    result = chronicle.resolve_chronicle_dir(config_path, config_path_is_explicit=False)

    assert result == tmp_path / "prompted"


def test_resolve_chronicle_dir_expands_tilde_and_relative(monkeypatch, tmp_path):
    monkeypatch.setenv(chronicle.ENV_VAR, "~/journal")
    result = chronicle.resolve_chronicle_dir(tmp_path / "unused.conf", False)
    assert "~" not in str(result)
    assert result.is_absolute()
