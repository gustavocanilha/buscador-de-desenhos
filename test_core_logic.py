import tempfile
import unittest
from pathlib import Path

import core_logic as cl


class ExtractCodesTest(unittest.TestCase):
    def test_extracts_codes_from_free_text(self):
        text = (
            "Segue a lista:\n"
            "1234-ABC-5678 - Chapa\n"
            "A1.2345\n"
            "repetido: 1234 - abc - 5678"
        )
        self.assertEqual(
            cl.extract_codes_from_text(text),
            ["1234-ABC-5678", "A1.2345"],
        )

    def test_returns_empty_without_codes(self):
        self.assertEqual(cl.extract_codes_from_text("sem codigo aqui"), [])

    def test_accepts_two_digits_and_two_letters(self):
        text = "M16.0001\nM17.0022\nM23.0037\nAA5.0033\nM1.0003"
        self.assertEqual(
            cl.extract_codes_from_text(text),
            ["M16.0001", "M17.0022", "M23.0037", "AA5.0033", "M1.0003"],
        )
        self.assertTrue(cl.is_valid_code("M16.0001"))
        self.assertTrue(cl.is_valid_code("AA5.0033"))


class FreeSearchTest(unittest.TestCase):
    def test_copies_found_file_to_numbered_result_folder(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "server"
            shop = root / "COMPRAS Geral"
            shop.mkdir(parents=True)
            source = shop / "1234-ABC-5678.pdf"
            source.write_bytes(b"pdf")
            source_mtime = source.stat().st_mtime_ns
            desktop = base / "desktop"

            report = cl.process_free_search(
                "1234-ABC-5678", root=root, desktop_dir=desktop, cache_ttl=0
            )

            self.assertEqual(report.destination, desktop / "Resultado")
            self.assertTrue((desktop / "Resultado" / "1234-ABC-5678.pdf").is_file())
            self.assertEqual(source.read_bytes(), b"pdf")
            self.assertEqual(source.stat().st_mtime_ns, source_mtime)
            self.assertEqual(
                [path.name for path in root.rglob("*") if path.is_file()],
                [source.name],
            )

            second = cl.process_free_search(
                "1234-ABC-5678", root=root, desktop_dir=desktop, cache_ttl=0
            )
            self.assertEqual(second.destination, desktop / "Resultado (2)")

    def test_does_not_create_folder_when_nothing_is_found(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "server"
            (root / "COMPRAS Geral").mkdir(parents=True)
            desktop = base / "desktop"

            report = cl.process_free_search(
                "9999-ZZZ-0000", root=root, desktop_dir=desktop, cache_ttl=0
            )

            self.assertIsNone(report.destination)
            self.assertFalse(desktop.exists())

    def test_rejects_text_without_codes(self):
        with self.assertRaises(cl.FreeSearchError):
            cl.process_free_search("sem codigo")


if __name__ == "__main__":
    unittest.main()
