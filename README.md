# dotnay

A tiny, self-destructing plain-text note format with the extension `.nayla`.

A `.nayla` file is ordinary text. You can create one in any editor, save it, and it becomes invalid once its expiry is reached. The viewer deletes it; the background checker removes it even if nobody opens it.

## Format specification

A file is UTF-8 text with three required lines at the top, followed by the note:

```
NAYLA
expires: 24h
---
The content of the note goes here.
```

### Rules

1. Line 1 must be exactly `NAYLA` (case-sensitive). A UTF-8 BOM is tolerated.
2. Line 2 must start with `expires:` followed by one of:
   - A duration: a positive integer and a unit, `s`, `m`, `h`, or `d`.
     Examples: `30s`, `15m`, `24h`, `7d`.
   - An exact local date and time in `YYYY-MM-DD HH:MM` or
     `YYYY-MM-DD HH:MM:SS` form.
     Example: `2026-11-04 18:00` or `2026-11-04 18:00:30`.
3. Line 3 must be exactly `---`.
4. Everything after line 3 is the note, preserved verbatim, including blank lines and trailing newlines.
5. CRLF and LF line endings are both accepted.

### Expiry semantics

- A duration is measured from the file's creation time:
  - Windows: file creation time.
  - macOS: birth time.
  - Linux: birth time when the filesystem provides it, otherwise the last-modified time.
- An exact date is interpreted as local time and does not depend on creation time.
- A file is expired when the current time is at or after the computed expiry. Expired files are still parseable so a viewer can show them before deleting.

### Duration units

| Unit | Meaning | Seconds |
|------|---------|---------|
| `s`  | seconds | 1       |
| `m`  | minutes | 60      |
| `h`  | hours   | 3,600   |
| `d`  | days    | 86,400  |

## Examples

See the `examples/` folder:

- `quick-note.nayla` - lasts 24 hours from creation.
- `short-lived.nayla` - lasts 30 minutes from creation.
- `exact-date.nayla` - expires at a specific local date and time.

## Usage

Requires Python 3.9 or newer.

```powershell
python -m dotnay.cli examples/quick-note.nayla
```

Output:

```
Expires: 2026-11-04 14:32:10 (23:59:59.123456 left)
---
Remember to water the plants before the timer runs out.
```

Invalid files produce a single clear message and exit with code 1:

```
Invalid .nayla file: Line 3 must be '---', found 'note'
```

Optional editable install, which also provides the `nayla` command:

```powershell
pip install -e .
nayla examples/short-lived.nayla
```

## Desktop app

One calm screen: one big text box, a save button, and a small live countdown.
There is no open button; launch a `.nayla` file to reopen it.

- **Save and timer.** Write your note and click `SAVE & SET TIMER`. Choose
  `1H`, `24H`, `7D`, or `CUSTOM` (a duration like `90m` or an exact date like
  `2026-11-10 18:00`). The timer starts when the note is saved. A new note is
  created in `Documents/dotnay/`; its name is shown quietly at the bottom.
- **Reopen.** The note text remains editable and can be saved, but its timer is
  locked. The original countdown continues and is never reset by editing.
- **The end.** The countdown keeps running while you edit. At zero the text
  fades into the background, then the `.nayla` file is deleted.

Requires only Python and Tkinter (bundled with the official Windows/macOS
installers):

```powershell
python -m dotnay.app
python -m dotnay.app examples/exact-date.nayla
```

Or install it (adds a `dotnay` window launcher and the `nayla` CLI):

```powershell
pip install -e .
dotnay
```

Look: near-black background, a single "N" in the corner, red accents, one
font, and a softly pulsing red countdown. The icon is a burning pixel-art N.

## Project layout

```
dotnay/
  dotnay/
    __init__.py
    parser.py
    writer.py
    timefmt.py
    cli.py
    app.py
    assets/
      nayla.png
      nayla.ico
  examples/
    quick-note.nayla
    short-lived.nayla
    exact-date.nayla
  tests/
    test_parser.py
    test_writer.py
    test_timefmt.py
  tools/
    make_icon.py
  pyproject.toml
  README.md
```

The icon is generated from a 32x32 pixel grid with the standard library only:

```powershell
python tools/make_icon.py
```

## Tests

```powershell
python -m unittest discover -s tests -t . -v
```

## Roadmap

1. Parser and format specification (done).
2. Single-screen editor with autosave, live countdown, and self-deletion (done).
3. `.nayla` file association for double-click opening (no "Open" button).
4. Background checker that removes expired files.
