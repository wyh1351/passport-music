import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from music_font_hash import source_digest_matches

class FontHashTests(unittest.TestCase):
    def test_windows_and_git_checkouts_validate_same_source(self):
        lf = b"const int glyphs[] = {1,2,3};\nconst int width = 20;\n"
        crlf = lf.replace(b"\n", b"\r\n")
        for inventory in (lf, crlf):
            digest = hashlib.sha256(inventory).hexdigest()
            self.assertTrue(source_digest_matches(lf, digest))
            self.assertTrue(source_digest_matches(crlf, digest))
            self.assertFalse(source_digest_matches(lf.replace(b"1,2,3", b"1,2,4"), digest))
            self.assertFalse(source_digest_matches(lf + b" ", digest))

    def test_bare_carriage_return_is_not_a_newline_conversion(self):
        data = b"const int glyph = 1;\r"
        self.assertFalse(source_digest_matches(data, hashlib.sha256(data).hexdigest()))

if __name__ == "__main__":
    unittest.main()
