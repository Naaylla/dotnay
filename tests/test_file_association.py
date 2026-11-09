import unittest

from dotnay.file_association import build_open_command


class FileAssociationTests(unittest.TestCase):
    def test_open_command_quotes_python_path_and_filename(self):
        command = build_open_command(r"C:\Program Files\Python\pythonw.exe")
        self.assertEqual(
            command,
            '"C:\\Program Files\\Python\\pythonw.exe" -m dotnay.app "%1"',
        )


if __name__ == "__main__":
    unittest.main()
