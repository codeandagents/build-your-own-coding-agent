"""The search tools (episode 2), offline: search_files finds lines by regex, find_files finds files by glob."""
from agent.tools import SEARCH_LIMIT, TOOLS, describe, run_tool


def call(tmp_path, name, **args):
    return run_tool(name, args, tmp_path)


def put(tmp_path, name, data: bytes):
    (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / name).write_bytes(data)


def test_search_returns_path_line_text_sorted_by_path(tmp_path):
    put(tmp_path, "b.py", b"x = 1\ndef total():\n")
    put(tmp_path, "src/a.py", b"def money():\n    pass\n")
    output, is_error = call(tmp_path, "search_files", pattern=r"^def \w+")
    assert not is_error and output == "b.py:2:def total():\nsrc/a.py:1:def money():"


def test_a_glob_without_a_folder_matches_at_any_depth(tmp_path):  # as in rg; find_files keeps glob's own meaning
    put(tmp_path, "src/a.py", b"TODO\n")
    put(tmp_path, "notes.md", b"TODO\n")
    assert call(tmp_path, "search_files", pattern="TODO", glob="*.py")[0] == "src/a.py:1:TODO"
    assert call(tmp_path, "search_files", pattern="TODO", glob="src/*.md")[0] == "No matches in 0 files"


def test_ignore_case_and_one_file_as_the_path(tmp_path):
    put(tmp_path, "log.txt", b"species Canine\nspecies dog\n")
    put(tmp_path, "other.txt", b"canine\n")
    output, _ = call(tmp_path, "search_files", pattern="canine", path="log.txt", ignore_case=True)
    assert output == "log.txt:1:species Canine"


def test_context_shows_lines_around_each_match(tmp_path):
    put(tmp_path, "t.md", b"".join(b"line %d\n" % n for n in range(1, 11)))
    output, _ = call(tmp_path, "search_files", pattern="line (2|3|8)$", context=1)
    assert output.splitlines() == ["t.md-1-line 1", "t.md:2:line 2", "t.md:3:line 3", "t.md-4-line 4", "--",
                                   "t.md-7-line 7", "t.md:8:line 8", "t.md-9-line 9"]


def test_the_cap_says_how_many_more_matched(tmp_path):
    put(tmp_path, "big.log", b"WARNING row\n" * (SEARCH_LIMIT + 37))
    output, _ = call(tmp_path, "search_files", pattern="WARNING")
    lines = output.splitlines()
    assert len(lines) == SEARCH_LIMIT + 1 and lines[-2] == f"big.log:{SEARCH_LIMIT}:WARNING row"
    assert lines[-1] == "[37 more matches not shown: narrow the pattern, path or glob]"


def test_no_match_says_how_many_files_were_searched(tmp_path):
    put(tmp_path, "a.py", b"x\n")
    put(tmp_path, "b.py", b"y\n")
    assert call(tmp_path, "search_files", pattern="zebra") == ("No matches in 2 files", False)


def test_a_bad_regex_is_an_error_not_a_crash(tmp_path):
    output, is_error = call(tmp_path, "search_files", pattern="(unclosed")
    assert is_error and output.startswith("Bad pattern:")


def test_windows_line_ends_and_non_ascii_text(tmp_path):
    put(tmp_path, "m.txt", "Kia ora\r\nNgā mihi\r\n".encode("utf-8"))
    assert call(tmp_path, "search_files", pattern="mihi$")[0] == "m.txt:2:Ngā mihi"


def test_hidden_folders_binary_files_and_env_files_are_skipped(tmp_path):
    put(tmp_path, ".git/config", b"needle\n")
    put(tmp_path, "pkg/__pycache__/m.cpython-312.pyc", b"needle\n")
    put(tmp_path, "logo.png", b"\x89PNG\x00needle\n")
    put(tmp_path, "config/prod.env", b"needle\n")
    put(tmp_path, "app.py", b"needle\n")
    assert call(tmp_path, "search_files", pattern="needle")[0] == "app.py:1:needle"
    assert call(tmp_path, "search_files", pattern="needle", path="config/prod.env")[0].startswith("Blocked")
    assert call(tmp_path, "find_files", pattern="**/*")[0] == "app.py\nlogo.png"


def test_searches_stay_in_the_project(tmp_path):
    work = tmp_path / "work"
    put(work, "a.py", b"secret\n")
    put(tmp_path, "outside.py", b"secret\n")
    assert call(work, "search_files", pattern="secret", path="..")[0].startswith("Blocked by the harness")
    assert call(work, "search_files", pattern="secret", path=str(tmp_path))[0].startswith("Blocked by the harness")
    assert call(work, "search_files", pattern="secret", glob="../*.py")[0] == "No matches in 0 files"
    assert call(work, "find_files", pattern="../*")[0] == "No files found"
    output, is_error = call(work, "find_files", pattern=str(tmp_path / "*.py"))
    assert is_error and "relative" in output


def test_find_files_by_glob_sorted(tmp_path):
    for name in ("docs/b.md", "docs/a.md", "data/fees.json", "data/x.csv", "README.md", "src/deep/m.py"):
        put(tmp_path, name, b"\n")
    assert call(tmp_path, "find_files", pattern="**/*.md")[0] == "README.md\ndocs/a.md\ndocs/b.md"
    assert call(tmp_path, "find_files", pattern="*.md")[0] == "README.md"  # this folder only
    assert call(tmp_path, "find_files", pattern="*.{json,csv}", path="data")[0] == "data/fees.json\ndata/x.csv"
    assert call(tmp_path, "find_files", pattern="**/*.py")[0] == "src/deep/m.py"
    assert call(tmp_path, "find_files", pattern="*.txt") == ("No files found", False)


def test_find_files_caps_its_list_and_says_how_many_more(tmp_path):
    for n in range(SEARCH_LIMIT + 5):
        put(tmp_path, f"f{n:03}.txt", b"\n")
    lines = call(tmp_path, "find_files", pattern="*.txt")[0].splitlines()
    assert len(lines) == SEARCH_LIMIT + 1 and lines[0] == "f000.txt"
    assert lines[-1] == "[5 more files not shown: narrow the pattern or path]"


def test_bash_steers_searching_to_the_search_tools():
    bash = next(tool for tool in TOOLS if tool["name"] == "bash")["description"]
    assert "search_files (not grep or rg)" in bash and "find_files (not find or ls)" in bash


def test_the_log_shows_a_search_as_a_call():
    assert describe("search_files", {"pattern": "canine", "path": "logs", "context": 2}) == \
        "> search_files(canine, path=logs, context=2)"
    assert describe("find_files", {"pattern": "**/*.md"}) == "> find_files(**/*.md)"
    assert describe("read_file", {"path": "t.md", "offset": 3}) == "> read_file(t.md, offset=3)"
