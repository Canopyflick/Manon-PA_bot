# features/library/test_parsing.py
import unittest

from features.library.parsing import extract_title, parse_library_message

PETE = "https://substack.com/home/post/p-217275140"


class ParseLibraryMessageTests(unittest.TestCase):
    def test_bare_url(self):
        self.assertEqual(parse_library_message(PETE), ("file", PETE, None))

    def test_url_with_note(self):
        text = f"{PETE}: recommended by Pete"
        self.assertEqual(
            parse_library_message(text),
            ("file", PETE, "recommended by Pete"),
        )

    def test_done_marks_read(self):
        self.assertEqual(
            parse_library_message(f"{PETE}:done"),
            ("status", PETE, "read"),
        )

    def test_read_and_archive_keywords(self):
        self.assertEqual(
            parse_library_message(f"{PETE}:read"),
            ("status", PETE, "read"),
        )
        self.assertEqual(
            parse_library_message(f"{PETE}:archive"),
            ("status", PETE, "archived"),
        )
        self.assertEqual(
            parse_library_message(f"{PETE}:archived"),
            ("status", PETE, "archived"),
        )

    def test_status_keyword_with_space_and_any_case(self):
        self.assertEqual(
            parse_library_message(f"{PETE}: Done"),
            ("status", PETE, "read"),
        )
        self.assertEqual(
            parse_library_message(f"{PETE}: ARCHIVE"),
            ("status", PETE, "archived"),
        )

    def test_port_stays_in_the_url(self):
        url = "http://localhost:8080/watch"
        self.assertEqual(parse_library_message(url), ("file", url, None))
        self.assertEqual(
            parse_library_message(f"{url}: later"),
            ("file", url, "later"),
        )

    def test_colon_inside_the_url_is_not_a_separator(self):
        url = "https://example.com/path?q=a:b"
        self.assertEqual(parse_library_message(url), ("file", url, None))
        self.assertEqual(
            parse_library_message(f"{url}: a note: with a colon"),
            ("file", url, "a note: with a colon"),
        )

    def test_url_inside_a_sentence_is_ignored(self):
        self.assertIsNone(parse_library_message(f"look at {PETE}"))
        self.assertIsNone(parse_library_message(f"{PETE} is worth reading"))
        self.assertIsNone(parse_library_message(""))
        self.assertIsNone(parse_library_message("   "))
        self.assertIsNone(parse_library_message(None))

    def test_trailing_colon_files_without_a_note(self):
        self.assertEqual(parse_library_message(f"{PETE}:"), ("file", PETE, None))
        self.assertEqual(parse_library_message(f"  {PETE}  "), ("file", PETE, None))


class ExtractTitleTests(unittest.TestCase):
    def test_og_title(self):
        page = '<html><meta property="og:title" content="Pete&#39;s post"><title>Other</title>'
        self.assertEqual(extract_title(page), "Pete's post")

    def test_og_title_content_before_property(self):
        page = '<meta content="Video title" property="og:title">'
        self.assertEqual(extract_title(page), "Video title")

    def test_title_tag_fallback(self):
        page = "<html><head><title>\n  A   long   one\n</title></head>"
        self.assertEqual(extract_title(page), "A long one")

    def test_missing_title(self):
        self.assertIsNone(extract_title(""))
        self.assertIsNone(extract_title("<html><p>no title</p></html>"))
        self.assertIsNone(extract_title(None))


if __name__ == "__main__":
    unittest.main()
