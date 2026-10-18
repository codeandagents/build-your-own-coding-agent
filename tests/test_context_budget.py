"""The context budget (episode 3), offline: how much of a tool's output reaches the model, and how it gets the rest.
Claude Code's rules: a long result is saved to a file (path + preview), a failed command keeps its start and end, a
long file is read in pages with a PARTIAL notice, and a search pages on with offset."""
from agent.tools import FAILED_MAX, INLINE_MAX, PAGE_MAX, PREVIEW, SEARCH_LIMIT, TOOLS, WHOLE_MAX, run_tool


def call(tmp_path, name, **args):
    return run_tool(name, args, tmp_path)


def put(tmp_path, name, data: bytes):
    (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / name).write_bytes(data)


def ticket(lines: int, width: int = 90) -> bytes:  # numbered lines of the same length, the needle near the end
    rows = [f"row {n:04} " + "." * (width - 9) for n in range(1, lines + 1)]
    rows[-5] = "row DECISION the wording the vets agreed".ljust(width, ".")
    return ("\n".join(rows) + "\n").encode()


def test_a_short_result_comes_back_as_is(tmp_path):
    put(tmp_path, "t.md", b"x" * (INLINE_MAX - 1))
    assert call(tmp_path, "bash", command="cat t.md") == ("x" * (INLINE_MAX - 1), False)
    assert not (tmp_path / ".outputs").exists()


def test_a_long_result_is_saved_to_a_file_with_its_path_and_a_preview(tmp_path):
    put(tmp_path, "t.md", ticket(400))
    output, is_error = call(tmp_path, "bash", command="cat t.md")
    head, preview = output.split("\n\nPreview (first 2KB):\n")
    assert not is_error and head == "Output too large (35.5KB). Full output saved to: .outputs/bash-001.txt"
    assert preview == ticket(400).decode()[:PREVIEW] + "\n..."
    assert (tmp_path / ".outputs/bash-001.txt").read_bytes() == ticket(400)  # all of it, and no \r added
    assert call(tmp_path, "bash", command="cat t.md")[0].endswith(".outputs/bash-002.txt\n\nPreview (first 2KB):\n"
                                                                  + ticket(400).decode()[:PREVIEW] + "\n...")


def test_the_saved_output_can_be_read_whole_and_searched(tmp_path):
    put(tmp_path, "t.md", ticket(400))
    call(tmp_path, "bash", command="cat t.md")
    output, _ = call(tmp_path, "read_file", path=".outputs/bash-001.txt")
    assert "DECISION" in output and "PARTIAL" not in output
    assert call(tmp_path, "search_files", pattern="DECISION", path=".outputs")[0] == ".outputs/bash-001.txt"
    assert call(tmp_path, "search_files", pattern="DECISION")[0] == "t.md"  # a project search skips .outputs


def test_a_failed_command_keeps_its_start_and_its_end(tmp_path):
    put(tmp_path, "log.txt", b"".join(b"line %05d\n" % n for n in range(3000)))
    output, is_error = call(tmp_path, "bash", command="cat log.txt; echo 'E   AssertionError: the end'; exit 3")
    assert not is_error and not (tmp_path / ".outputs").exists()
    assert output.startswith("line 00000\n") and output.endswith("E   AssertionError: the end\n\n[exit code 3]")
    assert "characters cut from the middle ...]" in output and len(output) < FAILED_MAX + 100


def test_grep_finding_nothing_is_not_a_failure(tmp_path):
    put(tmp_path, "t.md", ticket(400))
    for command in ("cat t.md; grep -c nothing t.md", "cat t.md && [ -f nothing ]"):
        output, _ = call(tmp_path, "bash", command=command)
        assert output.startswith("Output too large") and output.endswith("[exit code 1]")


def test_a_long_file_is_read_in_pages_with_claude_codes_notice(tmp_path):
    put(tmp_path, "t.md", ticket(600))  # 600 lines of 97 characters with the line number: two pages
    output, is_error = call(tmp_path, "read_file", path="t.md")
    page, notice = output.split("\n\n[PARTIAL view of t.md: ")
    last = len(page.splitlines())
    assert not is_error and len(page) <= PAGE_MAX and page.splitlines()[-1].startswith(f"{last:>6}\trow {last:04}")
    assert notice == (f"showing lines 1-{last} of 600 total (54,600 characters, cap {PAGE_MAX:,} per read). Call "
                      f"read_file with offset={last + 1} limit={last} for the next page, or search_files to find a "
                      "specific section. Do NOT answer from this page alone if the answer may be further in the file.]")
    rest, is_error = call(tmp_path, "read_file", path="t.md", offset=last + 1, limit=last)
    assert not is_error and "DECISION" in rest and rest.splitlines()[-1].startswith("   600\t")


def test_a_ticket_under_the_page_cap_is_read_whole(tmp_path):
    put(tmp_path, "t.md", ticket(380))  # ~37,000 characters with line numbers: one page, as the tickets are
    output, _ = call(tmp_path, "read_file", path="t.md")
    assert "DECISION" in output and "PARTIAL" not in output and output.splitlines()[-1].startswith("   380\t")


def test_more_than_2000_short_lines_is_partial_too(tmp_path):
    put(tmp_path, "a.log", b"ok\n" * 2500)
    output, _ = call(tmp_path, "read_file", path="a.log")
    assert "showing lines 1-2000 of 2500 total" in output and "offset=2001 limit=2000" in output


def test_a_range_over_the_cap_is_refused_and_says_what_fits(tmp_path):
    put(tmp_path, "t.md", ticket(600))
    output, is_error = call(tmp_path, "read_file", path="t.md", offset=10)
    assert is_error and output.startswith("Lines 10-600 of t.md are more than 40,000 characters: read fewer (offset=10 "
                                          "limit=") and output.endswith("fits), or search it with search_files")
    fits = int(output.split("limit=")[1].split(" ")[0])
    assert not call(tmp_path, "read_file", path="t.md", offset=10, limit=fits)[1]
    assert call(tmp_path, "read_file", path="t.md", offset=10, limit=fits + 1)[1]


def test_a_whole_file_over_256_kb_is_refused_but_a_part_can_be_read(tmp_path):
    put(tmp_path, "import.log", b"WARNING row 5400: species 'canine' not known\n" * (WHOLE_MAX // 40))
    output, is_error = call(tmp_path, "read_file", path="import.log")
    assert is_error and "more than a whole read allows (256 KB): read a part with offset and limit" in output
    assert call(tmp_path, "read_file", path="import.log", offset=1, limit=2) == (
        "     1\tWARNING row 5400: species 'canine' not known\n     2\tWARNING row 5400: species 'canine' not known",
        False)


def test_one_line_over_the_cap_is_refused(tmp_path):
    put(tmp_path, "min.json", b"{" + b'"a": 1, ' * 6000 + b"}\n")
    output, is_error = call(tmp_path, "read_file", path="min.json")
    assert is_error and output == "Line 1 of min.json alone is over 40,000 characters: search it with search_files"


def test_a_search_pages_on_with_offset(tmp_path):
    put(tmp_path, "big.log", b"".join(b"WARNING row %d\n" % n for n in range(1, 251)))
    second = call(tmp_path, "search_files", pattern="WARNING", output_mode="content", offset=SEARCH_LIMIT)[0]
    assert second.splitlines()[0] == "big.log:101:WARNING row 101" and len(second.splitlines()) == SEARCH_LIMIT + 1
    assert second.splitlines()[-1] == ("[50 more matches not shown: narrow the pattern, path or glob, or offset=200 "
                                       "for the next page]")
    third = call(tmp_path, "search_files", pattern="WARNING", output_mode="content", offset=200)[0].splitlines()
    assert third[0] == "big.log:201:WARNING row 201" and third[-1] == "big.log:250:WARNING row 250"
    assert call(tmp_path, "search_files", pattern="WARNING", output_mode="content", offset=250)[0] == \
        "No entries at this offset"
    assert call(tmp_path, "search_files", pattern="nothing", offset=250)[0] == "No matches in 1 files"


def test_a_search_pages_across_files(tmp_path):
    for n in range(3):
        put(tmp_path, f"logs/{n}.log", b"hit\n" * 60)
    output = call(tmp_path, "search_files", pattern="hit", output_mode="content", offset=110)[0].splitlines()
    assert output[0] == "logs/1.log:51:hit" and output[10] == "logs/2.log:1:hit" and output[-1] == "logs/2.log:60:hit"
    assert len(output) == 70


def test_a_long_search_result_is_saved_too(tmp_path):
    put(tmp_path, "wide.json", b"".join(b'{"note": "%s"}\n' % (b"leave " * 60) for _ in range(SEARCH_LIMIT)))
    output, _ = call(tmp_path, "search_files", pattern="leave", output_mode="content")
    assert output.startswith("Output too large") and "saved to: .outputs/search_files-001.txt" in output


def test_the_descriptions_say_what_happens_to_long_output():
    tool = {t["name"]: t for t in TOOLS}
    assert "Output over 30,000 characters is saved to a file" in tool["bash"]["description"]
    assert "up to 2000 lines or 40,000 characters" in tool["read_file"]["description"]
    assert "offset" in tool["search_files"]["input_schema"]["properties"]
