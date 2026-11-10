import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from dotnay.app import NaylaApp
from dotnay.parser import load_nayla


class AppTests(unittest.TestCase):
    def test_empty_untimed_note_with_path_closes_without_saving(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new.nayla"
            path.touch()
            app = Mock()
            app.note.get.return_value = ""
            app._expiry_at = None
            app._dirty = True
            app._path = path
            app._fading = False

            NaylaApp._on_close(app)

            app._save_existing.assert_not_called()
            app.destroy.assert_called_once_with()
            self.assertTrue(path.exists())
            self.assertEqual(path.stat().st_size, 0)

    def test_opening_empty_file_keeps_path_without_starting_timer(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new.nayla"
            path.touch()
            app = Mock()
            app._open_blank_note.side_effect = (
                lambda selected_path: NaylaApp._open_blank_note(app, selected_path)
            )

            NaylaApp.open_path(app, path)

            self.assertEqual(app._path, path)
            self.assertIsNone(app._expiry_at)
            self.assertFalse(app._dirty)
            self.assertTrue(path.exists())
            self.assertEqual(path.stat().st_size, 0)
            app._update_window_title.assert_called_once_with()

    def test_first_save_initializes_empty_file_at_its_existing_path(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new.nayla"
            path.touch()
            app = Mock()
            app._path = path
            app._timer_dialog = None
            app.note.get.return_value = "first note"
            save_commands = []

            def make_button(*_args, **kwargs):
                save_commands.append(kwargs["command"])
                return Mock()

            with patch("dotnay.app.tk.Toplevel", return_value=Mock()), \
                    patch("dotnay.app.tk.Frame", return_value=Mock()), \
                    patch("dotnay.app.tk.Canvas", return_value=Mock()), \
                    patch("dotnay.app.tk.Label", return_value=Mock()), \
                    patch("dotnay.app.tk.Spinbox", return_value=Mock()), \
                    patch(
                        "dotnay.app.tk.StringVar",
                        side_effect=lambda value: Mock(get=lambda: value),
                    ), \
                    patch("dotnay.app.tk.Button", side_effect=make_button):
                NaylaApp._show_timer_dialog(app)
                save_commands[0]()

            document = load_nayla(path)
            self.assertEqual(document.content, "first note\n")
            self.assertGreater(document.remaining().total_seconds(), 0)
            self.assertEqual(app._path, path)


if __name__ == "__main__":
    unittest.main()
