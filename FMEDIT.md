# fmedit

A small Bash terminal editor, inspired by Zepto. One script, no compilation
and no ncurses. Designed for text files and shell scripts.

Included in the [fm repository](https://github.com/vroby65/fm).
See [README.md](README.md) for installation of both programs and F4 integration.
The imported source is from `vroby65/fmedit`, branch `main`, commit
`d6c003da133d07c77e4797dc87eeb9059045418a`.

## Getting started

```bash
./fmedit notes.txt
./fmedit                 # new unnamed buffer
./fmedit -- -file-name    # name beginning with a dash
```

Requires Bash 4+, an ANSI/VT terminal, and `stty`, `mktemp`, `cp`, `mv`, `rm`.
Saving through a symbolic link also requires `readlink -f`. Python is not needed
at runtime. Developed and tested on Linux.

To add it to your PATH, run from the project directory:

```bash
install -Dm755 fmedit "$HOME/.local/bin/fmedit"
```

Repeat the install command after updating your checkout.

## Commands

| Key | Action |
| --- | --- |
| F1 | Help |
| F2 / Ctrl+S | Save; ask for a name for a new buffer |
| F10 | Save and quit |
| Esc / Ctrl+Q | Quit; if modified, ask whether to save, discard or cancel |
| Arrows, Home, End, PgUp, PgDown | Move the cursor |
| Ctrl+Home / Ctrl+End | Start / end of document |
| Shift+arrows, Shift+Home/End | Select text |
| Ctrl+A | Select all |
| Ctrl+C / Ctrl+X / Ctrl+V | Copy / cut / paste using the internal clipboard |
| Ctrl+Z / Ctrl+Y | Undo / redo (last 100 edits) |
| F7 / Ctrl+F | Find literal, case-sensitive text |
| Ctrl+N | Find the next occurrence, wrapping to the beginning |

Type a response in a prompt and press Enter; Esc cancels. Unsaved changes offer
`s` to save, `d` to discard, and Enter to cancel quitting. Overwriting an existing
file requires `y` or `Y`; an empty response cancels.
The terminal must forward key combinations to the editor: some applications
intercept function keys or Shift+arrows.

## Behavior

- Palette matches `fm`: dark gray background, muted yellow text and teal
  selection; bars, prompts and help use the same colors as `fm`.
- Line numbers, vertical and horizontal scrolling, and a modification indicator.
  A line index avoids scanning the document on every movement; rendering reads
  the visible page directly.
- Undo/redo stores only replaced and inserted text, up to 100 edits, instead of
  copying the whole document for every keystroke.
- Basic colors for comments, strings and `$` in `.sh` and `.bashrc` files;
  highlighting is limited to the current line.
- Bracketed terminal paste is recorded as one edit. Pasted control keys do not
  execute editor commands.
- UTF-8 follows the Bash locale. Tabs display at four-column intervals.
- Preserves the text exactly, including the presence or absence of a final
  newline and CRLF endings. Files containing NUL bytes are rejected.
- Saves through a temporary file in the destination directory and a final rename;
  preserves existing permissions. New files have permissions `0600`.
  Follows existing symbolic links without replacing the link.
- Restores terminal mode, cursor and screen on exit and on HUP, INT and TERM.
  Unsaved changes remain in memory only.

## Current limitations

The buffer is a Bash string and the index is rebuilt after edits: very large files
and long lines can still be slow. Large selections in history may use substantial
memory. Each typed character is one history entry. Emoji, double-width characters
and combining marks may misalign the cursor. Control characters in files display
as `?` and are never sent directly to the terminal.

Mouse support, multiple buffers, text replacement and system clipboard integration
are not implemented. Saving by rename replaces the inode: hard links continue
pointing to the old version. Concurrent changes from other programs are not
handled, and persistence during a power failure is not guaranteed.

## Verification

Tests require the distribution's Python 3 and use only its standard library:

```bash
bash -n fmedit
python3 -m unittest discover -s tests -v
```

Tests cover buffer operations, file preservation and real pseudo-terminal sessions
for shortcuts, paste, prompts and terminal restoration. They also check navigation
and editing across 40,000 lines with external commands disabled, saving 10,000
UTF-8/CRLF lines, English help, overwrite confirmation and save/discard on exit.
