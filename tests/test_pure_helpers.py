"""Tests for chronicle's pure, I/O-free helper functions."""

from pathlib import Path

import chronicle


def test_last_day_header_date_single_present():
    lines = ["## August\n", "### 2026-08-12, Wednesday\n"]
    assert chronicle.last_day_header_date(lines) == (2026, 8, 12)


def test_last_day_header_date_returns_last_not_first():
    # A month name (and thus a "## <Month>" heading) can recur across
    # years in a long-lived target file; only the day heading's full ISO
    # date unambiguously says whether the file's last section is *this*
    # year-month or an older one with the same name.
    lines = [
        "## September\n",
        "### 2026-09-04, Friday\n",
        "## September\n",
        "### 2027-09-04, Saturday\n",
    ]
    assert chronicle.last_day_header_date(lines) == (2027, 9, 4)


def test_last_day_header_date_ignores_month_header():
    lines = ["## August\n"]
    assert chronicle.last_day_header_date(lines) is None


def test_last_day_header_date_absent():
    lines = ["not a heading\n"]
    assert chronicle.last_day_header_date(lines) is None


def test_last_day_header_date_empty_lines():
    assert chronicle.last_day_header_date([]) is None


def test_last_day_header_date_ignores_weekday_suffix():
    lines = ["### 2026-08-12, Wednesday -- planning notes\n"]
    assert chronicle.last_day_header_date(lines) == (2026, 8, 12)


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


def test_cursor_flags_vim_jumps_to_last_line_then_enters_insert_mode():
    # Two prefilled lines now: the target-path header, then "- ". Without
    # jumping to the last line first, startinsert! would land on line 1.
    assert chronicle.cursor_flags(["vim"]) == ["-c", "$", "-c", "startinsert!"]


def test_cursor_flags_nvim_same_as_vim():
    assert chronicle.cursor_flags(["nvim"]) == ["-c", "$", "-c", "startinsert!"]


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
    assert chronicle.cursor_flags(["/usr/bin/vim"]) == ["-c", "$", "-c", "startinsert!"]


def test_cursor_flags_empty_argv_returns_nothing():
    assert chronicle.cursor_flags([]) == []


def test_strip_target_header_line_exact_match_removes_it():
    path = Path("/some/target.md")
    raw = f"# {path}\n- my entry"
    assert chronicle.strip_target_header_line(raw, path) == "- my entry"


def test_strip_target_header_line_no_header_leaves_content_untouched():
    path = Path("/some/target.md")
    raw = "- my entry"
    assert chronicle.strip_target_header_line(raw, path) == "- my entry"


def test_strip_target_header_line_near_miss_is_kept():
    # A first line that merely looks like a heading (or names a different
    # path) must never be silently eaten.
    path = Path("/some/target.md")
    raw = "# /some/other.md\n- my entry"
    assert chronicle.strip_target_header_line(raw, path) == raw


def test_strip_target_header_line_header_only_no_trailing_newline():
    path = Path("/some/target.md")
    raw = f"# {path}"
    assert chronicle.strip_target_header_line(raw, path) == ""


def test_strip_target_header_line_real_entry_starting_with_hash_is_kept():
    path = Path("/some/target.md")
    raw = "# not the header line\nmore text"
    assert chronicle.strip_target_header_line(raw, path) == raw
