"""dotnay - one calm editor for notes that delete themselves.

Write a note, save it with a timer, and reopen it later to see the locked
countdown. The note text remains editable until its timer expires.

    python -m dotnay.app
    python -m dotnay.app path/to/note.nayla
"""

from __future__ import annotations

import math
import sys
import time
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox
from typing import Optional

from .parser import NaylaError, load_nayla
from .timefmt import format_remaining
from .writer import write_nayla

# --- look ------------------------------------------------------------------

BG = "#08080a"        # window background
PAPER = "#0d0d11"     # the text box
TEXT = "#e9e9ef"
MUTED = "#575761"
RED = "#ff2d1a"       # the only accent
RED_SELECT = "#3a0f0a"

PIXEL_GLYPHS = {
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ":": ("00000", "00100", "00100", "00000", "00100", "00100", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10011", "01101"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}

ASSET_DIR = Path(__file__).resolve().parent / "assets"
DRAFT_DIR = Path.home() / "Documents" / "dotnay"

# --- colour helpers --------------------------------------------------------


def _rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in rgb)


def mix(first: str, second: str, amount: float) -> str:
    """Blend two colours; 0 = first, 1 = second."""
    return _hex(tuple(a + (b - a) * amount for a, b in zip(_rgb(first), _rgb(second))))


# --- the app ---------------------------------------------------------------


class NaylaApp(tk.Tk):
    def __init__(self, initial_file: Optional[str] = None) -> None:
        super().__init__()
        self.title("untitled.nayla")
        self.geometry("1000x760")
        self.minsize(760, 580)
        self.configure(bg=BG)

        # state
        self._icon = None
        self._path: Optional[Path] = None
        self._expiry_at: Optional[datetime] = None
        self._timer_dialog = None
        self._dirty = False
        self._status_job = None
        self._tick_job = None
        self._suspended = False
        self._fading = False
        self._closing = False

        self._build_icon()
        self._build_fonts()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if initial_file:
            # Let the window appear first, then open the file.
            self.after(80, lambda: self.open_path(initial_file))

        self._tick()

    # -- setup -------------------------------------------------------------

    def _build_icon(self) -> None:
        """The burning N: window icon plus a small mark in the corner."""
        ico = ASSET_DIR / "nayla.ico"
        png = ASSET_DIR / "nayla.png"
        if sys.platform == "win32" and ico.exists():
            try:
                self.iconbitmap(str(ico))
                self.iconbitmap(default=str(ico))
            except tk.TclError:
                pass
        if png.exists():
            try:
                self._icon = tk.PhotoImage(file=str(png))
                self.iconphoto(True, self._icon)
            except tk.TclError:
                self._icon = None

    def _build_fonts(self) -> None:
        # One family for the whole interface.
        available = set(tkfont.families(self))
        family = next(
            (name for name in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "DejaVu Sans")
             if name in available),
            "TkDefaultFont",
        )
        self.font_ui = tkfont.Font(root=self, family=family, size=9)
        self.font_chip = tkfont.Font(root=self, family=family, size=9, weight="bold")
        self.font_editor = tkfont.Font(root=self, family=family, size=13)
        self.font_count = tkfont.Font(root=self, family=family, size=16, weight="bold")
        self.font_status = tkfont.Font(root=self, family=family, size=8)

    def _build_ui(self) -> None:
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=54, pady=(28, 0))

        self.count = tk.Canvas(top, width=300, height=40, bg=BG, highlightthickness=0)
        self.count.pack(side="right")
        self._paint_countdown("--:--:--")

        bottom = tk.Frame(self, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=54, pady=(0, 32))
        self.status = tk.Label(
            bottom, text="", bg=BG, fg=MUTED, font=self.font_status, anchor="w"
        )
        self.status.pack(side="left")
        self.save_button = tk.Button(
            bottom,
            text="SAVE",
            command=self._save,
            bg=PAPER,
            fg=TEXT,
            activebackground=RED,
            activeforeground=TEXT,
            bd=0,
            relief="flat",
            highlightthickness=0,
            cursor="hand2",
            font=self.font_chip,
            padx=14,
            pady=8,
        )
        self.save_button.pack(side="right")

        # One big, borderless text box with space around it.
        self.note = tk.Text(
            self,
            bg=PAPER,
            fg=TEXT,
            insertbackground=RED,
            selectbackground=RED_SELECT,
            selectforeground=TEXT,
            bd=0,
            highlightthickness=0,
            wrap="word",
            undo=True,
            font=self.font_editor,
            padx=22,
            pady=20,
        )
        self.note.pack(fill="both", expand=True, padx=54, pady=(26, 10))
        self.note.bind("<<Modified>>", self._on_modified)
        self.note.focus_set()

        self.bind("<Control-s>", lambda _event: self._save())

    # -- saving ------------------------------------------------------------

    def _on_modified(self, _event=None) -> None:
        if not self.note.edit_modified():
            return
        self.note.edit_modified(False)  # re-arm the event
        if self._suspended or self._fading:
            return
        self._dirty = True
        self._update_save_button()
        self._update_window_title()
        self._status_to_name()

    def _save(self) -> None:
        """Save the note, asking for its one-time timer and filename first."""
        if self._fading or self._closing:
            return
        content = self.note.get("1.0", "end-1c")
        if self._path is None:
            if not content.strip():
                self._status_note("write something first", color=RED, hold=3000)
                return  # nothing worth saving yet
            self._show_timer_dialog()
            return
        self._save_existing(content)

    def _save_existing(self, content: str) -> None:
        if self._path is None or self._expiry_at is None:
            return
        try:
            # Keep the original deadline fixed even when the file is edited.
            expiry_spec = self._expiry_at.strftime("%Y-%m-%d %H:%M:%S")
            write_nayla(self._path, expiry_spec, content)
        except (NaylaError, OSError) as exc:
            self._status_note(f"could not save: {exc}", color=RED, hold=6000)
            return

        self._dirty = False
        self._update_save_button()
        self._update_window_title()
        self._status_to_name()

    def _show_timer_dialog(self) -> None:
        if self._timer_dialog is not None:
            self._timer_dialog.focus_set()
            return

        dialog = tk.Toplevel(self)
        self._timer_dialog = dialog
        dialog.title("Set the timer")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self)

        body = tk.Frame(dialog, bg=BG, padx=24, pady=20)
        body.pack(fill="both", expand=True)
        tk.Label(
            body,
            text="dies in...",
            bg=BG,
            fg=TEXT,
            font=self.font_count,
        ).pack(anchor="w", pady=(0, 14))

        fields = tk.Frame(body, bg=BG)
        fields.pack(anchor="w")
        values = (tk.StringVar(value="24"), tk.StringVar(value="00"), tk.StringVar(value="00"))
        for label, value, maximum in zip(
            ("hours", "minutes", "seconds"), values, (999, 59, 59)
        ):
            column = tk.Frame(fields, bg=BG)
            column.pack(side="left", padx=(0, 14))
            tk.Label(
                column, text=label, bg=BG, fg=MUTED, font=self.font_status
            ).pack(anchor="center", pady=(0, 5))
            tk.Spinbox(
                column,
                from_=0,
                to=maximum,
                textvariable=value,
                width=5,
                justify="center",
                format="%02.0f",
                bg=PAPER,
                fg=TEXT,
                insertbackground=RED,
                buttonbackground=PAPER,
                relief="flat",
                highlightthickness=0,
                font=self.font_count,
            ).pack(ipady=5)

        error = tk.Label(body, text="", bg=BG, fg=RED, font=self.font_status, anchor="w")
        error.pack(fill="x", pady=(8, 0))

        def save_note() -> None:
            try:
                hours, minutes, seconds = (int(value.get()) for value in values)
            except ValueError:
                error.configure(text="enter a whole number in each field")
                return
            if not 0 <= hours <= 999 or not 0 <= minutes <= 59 or not 0 <= seconds <= 59:
                error.configure(text="hours must be 0–999; minutes and seconds 0–59")
                return
            duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
            if duration.total_seconds() <= 0:
                error.configure(text="set a timer longer than zero")
                return

            try:
                DRAFT_DIR.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                error.configure(text=f"could not open save location: {exc}")
                return

            selected_path = filedialog.asksaveasfilename(
                parent=dialog,
                title="Save note",
                initialdir=str(DRAFT_DIR),
                initialfile="untitled.nayla",
                defaultextension=".nayla",
                filetypes=(("Nayla notes", "*.nayla"), ("All files", "*.*")),
            )
            if not selected_path:
                return

            path = Path(selected_path)
            if path.suffix.lower() != ".nayla":
                path = path.with_suffix(".nayla")

            started_at = datetime.now().replace(microsecond=0)
            expires_at = started_at + duration
            try:
                expiry_spec = expires_at.strftime("%Y-%m-%d %H:%M:%S")
                write_nayla(path, expiry_spec, self.note.get("1.0", "end-1c"))
            except OSError as exc:
                error.configure(text=f"could not save: {exc}")
                return

            self._path = path
            self._expiry_at = expires_at
            self._dirty = False
            self._update_save_button()
            self._update_window_title()
            self._status_to_name()
            self._paint_countdown(format_remaining(expires_at - datetime.now()))
            dialog.destroy()
            self._timer_dialog = None
            self.note.focus_set()

        tk.Button(
            body,
            text="SAVE",
            command=save_note,
            bg=RED,
            fg=TEXT,
            activebackground=RED,
            activeforeground=TEXT,
            bd=0,
            relief="flat",
            highlightthickness=0,
            cursor="hand2",
            font=self.font_chip,
            padx=14,
            pady=9,
        ).pack(anchor="e", pady=(14, 0))
        dialog.protocol("WM_DELETE_WINDOW", self._close_timer_dialog)
        dialog.bind("<Return>", lambda _event: save_note())
        dialog.grab_set()

    def _close_timer_dialog(self) -> None:
        if self._timer_dialog is not None:
            self._timer_dialog.destroy()
            self._timer_dialog = None
        self.note.focus_set()

    def _update_save_button(self) -> None:
        if self._path is None:
            self.save_button.configure(text="SAVE", state="normal")
        elif self._dirty:
            self.save_button.configure(text="SAVE", state="normal")
        else:
            self.save_button.configure(text="SAVE", state="disabled")

    def _update_window_title(self) -> None:
        filename = self._path.name if self._path is not None else "untitled.nayla"
        self.title(f"{filename}{'*' if self._dirty else ''}")

    # -- countdown ---------------------------------------------------------

    def _tick(self) -> None:
        if self._closing:
            return
        if self._expiry_at is not None and not self._fading:
            left = self._expiry_at - datetime.now()
            if left.total_seconds() <= 0:
                self._start_fade()
            else:
                self._paint_countdown(format_remaining(left), left.total_seconds() <= 10)
        self._tick_job = self.after(200, self._tick)

    def _paint_countdown(self, text: str, urgent: bool = False) -> None:
        """Draw a crisp pixel-font countdown using square canvas cells."""
        self.count.delete("all")
        width = self.count.winfo_width()
        height = self.count.winfo_height()
        if width < 50:  # not laid out yet
            width, height = 300, 40
        columns = len(text) * 6 - 1
        scale = max(1, min(4, (width - 8) // columns, (height - 8) // 7))
        text_width = columns * scale
        left = (width - text_width) / 2
        top = (height - 7 * scale) / 2
        pulse = 0.5 + 0.5 * math.sin(time.monotonic() * (6.0 if urgent else 1.6))
        bright = mix(RED, "#ffffff", 0.10 + 0.18 * pulse)
        for char_index, char in enumerate(text):
            glyph = PIXEL_GLYPHS[char]
            for row, pattern in enumerate(glyph):
                for column, pixel in enumerate(pattern):
                    if pixel != "1":
                        continue
                    x = left + (char_index * 6 + column) * scale
                    y = top + row * scale
                    self.count.create_rectangle(
                        x + 1,
                        y + 1,
                        x + scale + 1,
                        y + scale + 1,
                        fill=RED_SELECT,
                        outline="",
                    )
                    self.count.create_rectangle(
                        x,
                        y,
                        x + scale,
                        y + scale,
                        fill=bright,
                        outline="",
                    )

    # -- the end -----------------------------------------------------------

    def _start_fade(self) -> None:
        self._fading = True
        self.count.delete("all")
        self.note.configure(state="disabled")
        self._fade_step(0)

    def _fade_step(self, step: int) -> None:
        steps = 14
        if self._closing:
            return
        if step > steps:
            self._finish_fade()
            return
        self.note.configure(fg=mix(TEXT, PAPER, step / steps))
        self.after(50, lambda: self._fade_step(step + 1))

    def _finish_fade(self) -> None:
        path, self._path = self._path, None
        if path is not None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                self._status_note(f"could not delete: {exc}", color=RED, hold=6000)

        self._expiry_at = None
        self._fading = False
        self._clear_editor()
        self._update_save_button()
        self._paint_countdown("--:--:--")
        self._status_note("the note is gone", hold=2600)

    def _clear_editor(self) -> None:
        self._suspended = True
        self.note.configure(state="normal", fg=TEXT)
        self.note.delete("1.0", "end")
        self.note.edit_modified(False)
        self._suspended = False
        self._dirty = False
        self._update_window_title()
        self.note.focus_set()

    # -- opening a file ----------------------------------------------------

    def open_path(self, path) -> None:
        """Called when the app is launched with a .nayla path (double-click)."""
        path = Path(path).expanduser()
        try:
            document = load_nayla(path)
        except NaylaError as exc:
            self._status_note(f"cannot open: {exc}", color=RED, hold=6000)
            return

        if document.is_expired():
            # Never show an expired note: delete it and stay on a blank page.
            try:
                path.unlink()
            except OSError:
                pass
            self._status_note("that note had already expired", hold=4000)
            return

        self._path = path
        self._expiry_at = document.expires_at
        self._dirty = False
        self._update_window_title()
        self._suspended = True
        self.note.configure(state="normal", fg=TEXT)
        self.note.delete("1.0", "end")
        self.note.insert("1.0", document.content)
        self.note.edit_modified(False)
        self._suspended = False

        self._update_save_button()
        self._status_to_name()
        self.note.focus_set()
        self._paint_countdown(
            format_remaining(document.remaining()),
            document.remaining().total_seconds() <= 10,
        )

    # -- tiny status line --------------------------------------------------

    def _status_note(self, text: str, color: str = MUTED, hold: Optional[int] = None) -> None:
        if self._status_job is not None:
            self.after_cancel(self._status_job)
            self._status_job = None
        self.status.configure(text=text, fg=color)
        if hold:
            self._status_job = self.after(hold, self._status_to_name)

    def _status_to_name(self) -> None:
        self._status_job = None
        name = self._path.name if self._path is not None else ""
        self.status.configure(text=name, fg=MUTED)

    # -- lifecycle ---------------------------------------------------------

    def _on_close(self) -> None:
        """Save changes to an already-timed note before closing."""
        if self._path is None and self._dirty and self.note.get("1.0", "end-1c").strip():
            discard = messagebox.askyesno(
                "Unsaved note",
                "This note has not been saved or timed yet. Discard it?",
                parent=self,
            )
            if not discard:
                return
        elif self._path is not None and self._dirty:
            self._save_existing(self.note.get("1.0", "end-1c"))
            if self._dirty:
                return
        self._close_timer_dialog()
        # If we close while the note is expiring, finish the deletion now.
        if self._path is not None and self._expiry_at is not None:
            if self._fading or self._expiry_at <= datetime.now():
                try:
                    self._path.unlink()
                except OSError:
                    pass
                self._path = None
        self._closing = True
        self.destroy()

    def destroy(self) -> None:
        self._closing = True
        for job in (self._tick_job, self._status_job):
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        self._tick_job = self._status_job = None
        super().destroy()


# --- entry point -----------------------------------------------------------


def main(argv=None) -> int:
    # Crisp text on high-DPI Windows displays.
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    args = list(sys.argv[1:] if argv is None else argv)
    app = NaylaApp(initial_file=args[0] if args else None)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
