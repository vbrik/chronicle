"""Tests for chronicle's config-file I/O and target-path resolution."""

import chronicle
import pytest


def test_load_config_parser_valid_ini(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[targets]\n0 = /some/file.md\n")
    parser = chronicle.load_config_parser(config_path)
    assert parser.get("targets", "0") == "/some/file.md"


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


def test_load_config_parser_keys_are_case_sensitive(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[targets]\nA = /upper.md\na = /lower.md\n")
    parser = chronicle.load_config_parser(config_path)
    assert parser.get("targets", "A") == "/upper.md"
    assert parser.get("targets", "a") == "/lower.md"


def test_load_config_parser_default_section_does_not_leak_into_others(tmp_path):
    # configparser's [DEFAULT] section is normally inherited by every other
    # section; a [targets] section must be judged only on its own entries,
    # since [DEFAULT] is a fairly ordinary INI section name someone could
    # use for an unrelated purpose in the same file.
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[DEFAULT]\nfallback = /oops.md\n\n[targets]\n")
    parser = chronicle.load_config_parser(config_path)
    assert dict(parser["targets"]) == {}


def test_load_config_parser_percent_sign_in_value_is_not_interpolated(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[targets]\n0 = /home/user/50%-done/notes.md\n")
    parser = chronicle.load_config_parser(config_path)
    assert parser.get("targets", "0") == "/home/user/50%-done/notes.md"


def test_resolve_target_path_explicit_key(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    target = tmp_path / "one.md"
    config_path.write_text(f"[targets]\n0 = {target}\n1 = /other.md\n")

    key, path = chronicle.resolve_target_path(config_path, "0", False)

    assert key == "0"
    assert path == target.resolve()


def test_resolve_target_path_default_uses_first_entry(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    first = tmp_path / "first.md"
    config_path.write_text(f"[targets]\n1 = {first}\n0 = /second.md\n")

    key, path = chronicle.resolve_target_path(config_path, None, False)

    assert key == "1"
    assert path == first.resolve()


def test_resolve_target_path_expands_tilde_and_relative(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[targets]\n0 = ~/journal.md\n")

    _, path = chronicle.resolve_target_path(config_path, "0", False)

    assert "~" not in str(path)
    assert path.is_absolute()


def test_resolve_target_path_unknown_key_exits_with_template(tmp_path, capsys):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[targets]\n0 = /some/file.md\n")

    with pytest.raises(SystemExit) as exc_info:
        chronicle.resolve_target_path(config_path, "9", False)

    assert exc_info.value.code == 1
    stderr = capsys.readouterr().err
    assert '"9"' in stderr
    assert "[targets]" in stderr
    assert str(config_path) in stderr


def test_resolve_target_path_missing_section_exits_with_template(tmp_path, capsys):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[other]\nkey = value\n")

    with pytest.raises(SystemExit) as exc_info:
        chronicle.resolve_target_path(config_path, "0", False)

    assert exc_info.value.code == 1
    assert "[targets]" in capsys.readouterr().err


def test_resolve_target_path_missing_config_file_exits_with_template(tmp_path, capsys):
    missing_config = tmp_path / "does-not-exist.conf"

    with pytest.raises(SystemExit) as exc_info:
        chronicle.resolve_target_path(missing_config, None, False)

    assert exc_info.value.code == 1
    assert "[targets]" in capsys.readouterr().err


def test_resolve_target_path_no_key_message_does_not_mention_a_key(tmp_path, capsys):
    # Distinguishes the "nothing configured at all" message from the
    # "this specific key is missing" one (which does quote a key).
    missing_config = tmp_path / "does-not-exist.conf"

    with pytest.raises(SystemExit):
        chronicle.resolve_target_path(missing_config, None, False)

    stderr = capsys.readouterr().err
    assert "no targets configured" in stderr
    assert '"' not in stderr.splitlines()[0]


def test_resolve_target_path_blank_value_exits_with_template(tmp_path, capsys):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[targets]\n0 = \n")

    with pytest.raises(SystemExit) as exc_info:
        chronicle.resolve_target_path(config_path, "0", False)

    assert exc_info.value.code == 1
    stderr = capsys.readouterr().err
    assert '"0"' in stderr
    assert "[targets]" in stderr


def test_resolve_target_path_empty_targets_section_no_key_exits(tmp_path, capsys):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[targets]\n")

    with pytest.raises(SystemExit) as exc_info:
        chronicle.resolve_target_path(config_path, None, False)

    assert exc_info.value.code == 1
    assert "[targets]" in capsys.readouterr().err


def test_resolve_target_path_explicit_config_missing_file_distinct_error(
    tmp_path, capsys
):
    missing_config = tmp_path / "does-not-exist.conf"

    with pytest.raises(SystemExit) as exc_info:
        chronicle.resolve_target_path(missing_config, "0", True)

    assert exc_info.value.code == 1
    assert "config file not found" in capsys.readouterr().err


def test_resolve_target_path_default_section_not_treated_as_a_target(tmp_path, capsys):
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text("[DEFAULT]\nfallback = /oops.md\n\n[targets]\n")

    with pytest.raises(SystemExit) as exc_info:
        chronicle.resolve_target_path(config_path, None, False)

    assert exc_info.value.code == 1
    assert "no targets configured" in capsys.readouterr().err


def test_resolve_target_path_value_with_percent_sign(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    target = tmp_path / "50%-done" / "notes.md"
    config_path.write_text(f"[targets]\n0 = {target}\n")

    _, path = chronicle.resolve_target_path(config_path, "0", False)

    assert path == target.resolve()


def test_resolve_target_path_key_lookup_is_case_sensitive(tmp_path):
    config_path = tmp_path / "chronicle.conf"
    upper = tmp_path / "upper.md"
    lower = tmp_path / "lower.md"
    config_path.write_text(f"[targets]\nA = {upper}\na = {lower}\n")

    _, path_upper = chronicle.resolve_target_path(config_path, "A", False)
    _, path_lower = chronicle.resolve_target_path(config_path, "a", False)

    assert path_upper == upper.resolve()
    assert path_lower == lower.resolve()
