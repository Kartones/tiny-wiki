import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from convert_google_redirects import find_google_redirects, fix_text

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "convert_google_redirects.py"

EXAMPLE_REDIRECT = (
    "http://www.google.com/url?q=http%3A%2F%2Fbigocheatsheet.com%2F"
    "&sa=D&sntz=1&usg=AFQjCNFmKTm8NCPJNESYKwyMKZmXsfTAvw"
)


class TestFindGoogleRedirects(unittest.TestCase):
    def test_bare_redirect_is_detected_and_resolved(self):
        redirects = find_google_redirects(f"see {EXAMPLE_REDIRECT} for details\n")
        self.assertEqual(len(redirects), 1)
        self.assertEqual(redirects[0].original, EXAMPLE_REDIRECT)
        self.assertEqual(redirects[0].resolved, "https://bigocheatsheet.com/")

    def test_redirect_inside_markdown_link_is_detected(self):
        text = f"see [this page]({EXAMPLE_REDIRECT}) for details\n"
        redirects = find_google_redirects(text)
        self.assertEqual([r.resolved for r in redirects], ["https://bigocheatsheet.com/"])

    def test_non_redirect_google_url_is_ignored(self):
        redirects = find_google_redirects("see https://www.google.com/search?q=foo\n")
        self.assertEqual(redirects, [])

    def test_redirect_inside_fenced_code_block_is_not_detected(self):
        text = "\n".join(["```", EXAMPLE_REDIRECT, "```", ""])
        redirects = find_google_redirects(text)
        self.assertEqual(redirects, [])

    def test_redirect_inside_inline_code_is_not_detected(self):
        redirects = find_google_redirects(f"run `curl {EXAMPLE_REDIRECT}` please\n")
        self.assertEqual(redirects, [])

    def test_already_https_target_is_left_as_https(self):
        redirect = "http://www.google.com/url?q=https%3A%2F%2Fexample.com%2F&sa=D"
        redirects = find_google_redirects(redirect + "\n")
        self.assertEqual(redirects[0].resolved, "https://example.com/")

    def test_trailing_sentence_punctuation_is_excluded(self):
        redirects = find_google_redirects(f"see {EXAMPLE_REDIRECT}.\n")
        self.assertEqual(redirects[0].original, EXAMPLE_REDIRECT)


class TestFixText(unittest.TestCase):
    def test_fix_replaces_bare_redirect_with_resolved_url(self):
        result = fix_text(f"see {EXAMPLE_REDIRECT} for details\n")
        self.assertEqual(result, "see https://bigocheatsheet.com/ for details\n")

    def test_fix_replaces_url_inside_markdown_link_keeping_link_text(self):
        result = fix_text(f"see [this page]({EXAMPLE_REDIRECT}) for details\n")
        self.assertEqual(result, "see [this page](https://bigocheatsheet.com/) for details\n")

    def test_fix_leaves_non_redirect_urls_untouched(self):
        text = "see https://example.com/page for details\n"
        self.assertEqual(fix_text(text), text)

    def test_fixed_output_has_no_remaining_redirects(self):
        fixed = fix_text(f"see {EXAMPLE_REDIRECT} for details\n")
        self.assertEqual(find_google_redirects(fixed), [])


class TestMainCli(unittest.TestCase):
    def test_nonexistent_path_shows_error_and_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "/no/such/path.md"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("/no/such/path.md", result.stderr)

    def test_report_mode_exits_one_when_redirects_found(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(f"see {EXAMPLE_REDIRECT}\n")
            md_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), md_path],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("https://bigocheatsheet.com/", result.stdout)
        finally:
            Path(md_path).unlink()

    def test_fix_mode_exits_zero_and_rewrites_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(f"see {EXAMPLE_REDIRECT}\n")
            md_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), md_path, "--fix"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(Path(md_path).read_text(), "see https://bigocheatsheet.com/\n")
        finally:
            Path(md_path).unlink()

    def test_quiet_suppresses_stdout_but_keeps_exit_code(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(f"see {EXAMPLE_REDIRECT}\n")
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
