"""Tests for chronicle's pure, I/O-free helper functions."""

import datetime
from pathlib import Path

import chronicle
import pytest


@pytest.mark.parametrize(
    ("month", "expected_quarter"),
    [
        (1, 1),
        (2, 1),
        (3, 1),
        (4, 2),
        (5, 2),
        (6, 2),
        (7, 3),
        (8, 3),
        (9, 3),
        (10, 4),
        (11, 4),
        (12, 4),
    ],
)
def test_quarter_of(month, expected_quarter):
    assert chronicle.quarter_of(datetime.date(2026, month, 15)) == expected_quarter


def test_quarter_of_leap_year_feb29():
    assert chronicle.quarter_of(datetime.date(2024, 2, 29)) == 1


@pytest.mark.parametrize(
    ("month", "expected_quarter"),
    [(1, 1), (4, 2), (7, 3), (10, 4)],
)
def test_chronicle_path_quarter_in_filename(month, expected_quarter):
    date = datetime.date(2026, month, 1)
    path = chronicle.chronicle_path(date, Path("/root"))
    assert path == Path(f"/root/2026-q{expected_quarter}.md")


def test_chronicle_path_different_years_differ():
    dir_ = Path("/root")
    p2025 = chronicle.chronicle_path(datetime.date(2025, 1, 1), dir_)
    p2026 = chronicle.chronicle_path(datetime.date(2026, 1, 1), dir_)
    assert p2025 != p2026
    assert p2025 == Path("/root/2025-q1.md")
    assert p2026 == Path("/root/2026-q1.md")


def test_find_month_header_present():
    lines = ["# 2026 Q3\n", "## August\n", "### 2026-08-12\n"]
    assert chronicle.find_month_header(lines, "## August") == 1


def test_find_month_header_absent():
    lines = ["# 2026 Q3\n", "## July\n"]
    assert chronicle.find_month_header(lines, "## August") is None


def test_find_month_header_empty_lines():
    assert chronicle.find_month_header([], "## August") is None


def test_find_month_header_does_not_match_day_header():
    # Equality check, not substring: a day heading under August must not
    # be mistaken for the "## August" month heading itself.
    lines = ["### August 12\n"]
    assert chronicle.find_month_header(lines, "## August") is None


def test_find_month_header_exact_match_only():
    # Documents current behavior: trailing whitespace on the heading line
    # breaks the exact-equality match.
    lines = ["## August \n"]
    assert chronicle.find_month_header(lines, "## August") is None


def test_find_day_header_plain():
    lines = ["### 2026-08-12\n", "- entry\n"]
    assert chronicle.find_day_header(lines, "2026-08-12") == 0


def test_find_day_header_with_weekday_suffix():
    lines = ["### 2026-08-12, Wednesday\n"]
    assert chronicle.find_day_header(lines, "2026-08-12") == 0


def test_find_day_header_with_extra_trailing_text():
    lines = ["### 2026-08-12, Wednesday -- planning notes\n"]
    assert chronicle.find_day_header(lines, "2026-08-12") == 0


def test_find_day_header_absent():
    lines = ["### 2026-08-11, Tuesday\n"]
    assert chronicle.find_day_header(lines, "2026-08-12") is None


def test_trim_trailing_blank_lines_removes_trailing():
    lines = ["a\n", "b\n", "  \n", "\n"]
    chronicle.trim_trailing_blank_lines(lines)
    assert lines == ["a\n", "b\n"]


def test_trim_trailing_blank_lines_noop_when_no_trailing_blanks():
    lines = ["a\n", "b\n"]
    chronicle.trim_trailing_blank_lines(lines)
    assert lines == ["a\n", "b\n"]


def test_trim_trailing_blank_lines_all_blank():
    lines = ["\n", "  \n"]
    chronicle.trim_trailing_blank_lines(lines)
    assert lines == []


def test_trim_trailing_blank_lines_empty_list():
    lines = []
    chronicle.trim_trailing_blank_lines(lines)
    assert lines == []


def test_trim_trailing_blank_lines_preserves_middle_blanks():
    lines = ["a\n", "\n", "b\n"]
    chronicle.trim_trailing_blank_lines(lines)
    assert lines == ["a\n", "\n", "b\n"]


def test_trim_trailing_blank_lines_mutates_in_place():
    lines = ["a\n", "\n"]
    original_id = id(lines)
    result = chronicle.trim_trailing_blank_lines(lines)
    assert id(lines) == original_id
    assert result is None


def test_section_end_next_heading_present():
    lines = ["## August\n", "- a\n", "## September\n"]
    assert chronicle.section_end(lines, 0) == 2


def test_section_end_no_further_heading():
    lines = ["## August\n", "- a\n", "- b\n"]
    assert chronicle.section_end(lines, 0) == 3


def test_section_end_heading_immediately_follows():
    lines = ["## August\n", "## September\n"]
    assert chronicle.section_end(lines, 0) == 1


def test_section_end_any_hash_prefix_is_a_boundary():
    lines = ["## August\n", "- a\n", "#### stray\n"]
    assert chronicle.section_end(lines, 0) == 2


def test_insert_in_section_no_trailing_blanks():
    lines = ["### 2026-08-12, Wednesday\n", "- a\n", "## September\n"]
    chronicle.insert_in_section(lines, 0, "- b")
    assert lines == [
        "### 2026-08-12, Wednesday\n",
        "- a\n",
        "- b\n",
        "## September\n",
    ]


def test_insert_in_section_before_trailing_blanks():
    lines = ["### 2026-08-10, Monday\n", "- a\n", "\n", "## September\n"]
    chronicle.insert_in_section(lines, 0, "- b")
    assert lines == [
        "### 2026-08-10, Monday\n",
        "- a\n",
        "- b\n",
        "\n",
        "## September\n",
    ]


def test_insert_in_section_header_only_section():
    lines = ["### 2026-08-12, Wednesday\n"]
    chronicle.insert_in_section(lines, 0, "- hi")
    assert lines == ["### 2026-08-12, Wednesday\n", "- hi\n"]


def test_insert_in_section_last_section_in_file():
    lines = ["### 2026-08-12, Wednesday\n", "- a\n", "\n"]
    chronicle.insert_in_section(lines, 0, "- b")
    assert lines == ["### 2026-08-12, Wednesday\n", "- a\n", "- b\n", "\n"]


def test_format_entry_single_line():
    assert chronicle.format_entry("hello world") == "hello world"


def test_format_entry_strips_leading_and_trailing_newlines():
    assert chronicle.format_entry("\n\nhello\n\n") == "hello"


def test_format_entry_strips_trailing_whitespace_per_line():
    assert chronicle.format_entry("hello   \n  world  \n") == ("hello\n  world")


def test_format_entry_strips_outer_newlines_keeps_inner():
    content = "\n\nfirst\nsecond\n\n"
    assert chronicle.format_entry(content) == "first\nsecond"


def test_is_blank_entry_empty_string():
    assert chronicle.is_blank_entry("") is True


def test_is_blank_entry_whitespace_only():
    assert chronicle.is_blank_entry("   ") is True


def test_is_blank_entry_unmodified_dash_prefill():
    assert chronicle.is_blank_entry("-") is True


def test_is_blank_entry_dash_with_content_is_not_blank():
    assert chronicle.is_blank_entry("- did something") is False


def test_cursor_flags_vim_enters_insert_mode_at_end_of_line():
    assert chronicle.cursor_flags(["vim"]) == ["-c", "startinsert!"]


def test_cursor_flags_nvim_same_as_vim():
    assert chronicle.cursor_flags(["nvim"]) == ["-c", "startinsert!"]


def test_cursor_flags_unknown_editor_returns_nothing():
    assert chronicle.cursor_flags(["code", "--wait"]) == []


def test_cursor_flags_emacs_not_recognized():
    # Not verified against a real emacs; deliberately left unhandled rather
    # than guessed (a wrong flag risks being parsed as a second filename).
    assert chronicle.cursor_flags(["emacs"]) == []


def test_cursor_flags_nano_not_recognized():
    assert chronicle.cursor_flags(["nano"]) == []


def test_cursor_flags_plain_vi_returns_nothing():
    # Plain "vi" may be nvi/BSD vi, which lacks vim's :startinsert command;
    # only vim/nvim get cursor flags.
    assert chronicle.cursor_flags(["vi"]) == []


def test_cursor_flags_matches_by_basename_not_full_path():
    assert chronicle.cursor_flags(["/usr/bin/vim"]) == ["-c", "startinsert!"]


def test_cursor_flags_empty_argv_returns_nothing():
    assert chronicle.cursor_flags([]) == []
