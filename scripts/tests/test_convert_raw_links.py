import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from convert_raw_links import find_raw_links, fix_text

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "convert_raw_links.py"


class TestFindRawLinks(unittest.TestCase):
    def test_plain_raw_url_is_detected(self):
        links = find_raw_links("check this out: https://example.com/page\n")
        self.assertEqual([l.url for l in links], ["https://example.com/page"])

    def test_url_already_wrapped_in_markdown_link_is_not_detected(self):
        links = find_raw_links("see [my page](https://example.com/page) for more\n")
        self.assertEqual(links, [])

    def test_bare_url_used_as_link_text_is_not_detected(self):
        links = find_raw_links("[https://example.com](https://example.com/other)\n")
        self.assertEqual(links, [])

    def test_url_inside_inline_code_is_not_detected(self):
        links = find_raw_links("run `curl https://example.com/api` please\n")
        self.assertEqual(links, [])

    def test_url_inside_fenced_code_block_is_not_detected(self):
        text = "\n".join(
            [
                "before",
                "```",
                "https://example.com/in-code",
                "```",
                "after https://example.com/out-of-code",
            ]
        )
        links = find_raw_links(text)
        self.assertEqual([l.url for l in links], ["https://example.com/out-of-code"])

    def test_url_inside_autolink_is_not_detected(self):
        links = find_raw_links("see <https://example.com/page> for more\n")
        self.assertEqual(links, [])

    def test_trailing_sentence_punctuation_is_excluded_from_url(self):
        links = find_raw_links("go to https://example.com/page.\n")
        self.assertEqual([l.url for l in links], ["https://example.com/page"])

    def test_multiple_raw_urls_on_one_line_are_all_detected(self):
        links = find_raw_links(
            "first https://example.com/a then https://example.com/b\n"
        )
        self.assertEqual(
            [l.url for l in links],
            ["https://example.com/a", "https://example.com/b"],
        )

    def test_raw_url_after_existing_link_on_same_line_is_not_over_matched(self):
        links = find_raw_links(
            "[a](https://example.com/a) and also https://example.com/b.\n"
        )
        self.assertEqual([l.url for l in links], ["https://example.com/b"])

    def test_line_numbers_are_reported_correctly(self):
        text = "line one\nline two https://example.com/page\nline three\n"
        links = find_raw_links(text)
        self.assertEqual(links[0].line, 2)


class TestFixText(unittest.TestCase):
    def test_fix_wraps_raw_url(self):
        result = fix_text("check this out: https://example.com/page\n")
        self.assertEqual(
            result, "check this out: [https://example.com/page](https://example.com/page)\n"
        )

    def test_fix_preserves_trailing_punctuation_outside_link(self):
        result = fix_text("go to https://example.com/page.\n")
        self.assertEqual(
            result, "go to [https://example.com/page](https://example.com/page).\n"
        )

    def test_fix_leaves_already_wrapped_links_untouched(self):
        text = "see [my page](https://example.com/page) for more\n"
        self.assertEqual(fix_text(text), text)

    def test_fix_leaves_code_blocks_untouched(self):
        text = "\n".join(["```", "https://example.com/in-code", "```", ""])
        self.assertEqual(fix_text(text), text)

    def test_fixed_output_has_no_remaining_raw_links(self):
        text = "first https://example.com/a then https://example.com/b\n"
        fixed = fix_text(text)
        self.assertEqual(find_raw_links(fixed), [])


class TestMainCli(unittest.TestCase):
    def test_nonexistent_path_shows_error_and_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "/no/such/path.md"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("/no/such/path.md", result.stderr)

    def test_fix_mode_exits_zero_after_successfully_fixing(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("check this out: https://example.com/page\n")
            md_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), md_path, "--fix"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0)
        finally:
            Path(md_path).unlink()

    def test_quiet_suppresses_stdout_but_keeps_exit_code(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("check this out: https://example.com/page\n")
            md_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), md_path, "--quiet"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.returncode, 1)
        finally:
            Path(md_path).unlink()


if __name__ == "__main__":
    unittest.main()
