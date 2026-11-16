# fm

Questo è il branch `italiano`; il branch principale è [main](https://github.com/vroby65/fm/tree/main). Per scegliere questo branch in un clone, eseguire `git switch italiano`.

File manager **TUI a uno o due pannelli**, ispirato ai tasti funzione di Midnight Commander e pensato per una piccola finestra terminale in **ai-bar**.

Written in **Bash 4+**, with **xterm/SGR mouse support**, a **graphite gray theme**,
Lynx-style navigation and Unicode box-drawing frames (`┌─┐`, `│ │`, `└─┘`) with an
ASCII fallback. No ncurses, dialog, fzf or TUI libraries. Local operations require
Bash, `stty` and basic GNU utilities, including `cp`, `mv`, `mkdir`, `rm`, `grep`,
`stat`, `numfmt` and `fold`.

Le istruzioni di questo README si riferiscono al branch `italiano`. I precedenti
merge hanno allineato i sorgenti e i test alla versione inglese di `main`;
attualmente anche in questo branch interfaccia e conferme sono in inglese.

## Installazione rapida

Installare `fm` e `fmedit` da questo branch in `~/.local/bin`, senza sudo,
compilazione o clone:

```bash
mkdir -p "$HOME/.local/bin" &&
curl -fsSL "https://raw.githubusercontent.com/vroby65/fm/italiano/fm" -o "$HOME/.local/bin/fm" &&
curl -fsSL "https://raw.githubusercontent.com/vroby65/fm/italiano/fmedit" -o "$HOME/.local/bin/fmedit" &&
chmod +x "$HOME/.local/bin/fm" "$HOME/.local/bin/fmedit"
```

Ripetere i comandi per aggiornare entrambi. Per scaricare serve `curl`.
Eseguire `fm` o `fmedit` se `~/.local/bin` è nel PATH (anche da Fish).
Per la versione del branch `main`, sostituire `/italiano/` con `/main/` nell'URL.

## Getting started

```bash
git clone https://github.com/vroby65/fm.git
cd fm
./fm
./fm "$HOME/Documents"
```

Install from the checked-out source with:

```bash
install -Dm755 fm "$HOME/.local/bin/fm"
install -Dm755 fmedit "$HOME/.local/bin/fmedit"
```

Requires an interactive terminal of at least **35 columns × 12 rows**; **70+
columns** are recommended. For an embedded terminal managing its own screen:

```bash
ABFM_NO_ALT_SCREEN=1 fm
```

Disable colors or use ASCII frames with:

```bash
ABFM_NO_COLOR=1 fm
ABFM_ASCII=1 fm
```

`NO_COLOR` also disables colors. Unicode frames depend on a UTF-8 locale.

## Editor incluso: fmedit

Il repository comprende anche `fmedit`, editor Bash autonomo, la sua
[guida d'uso](FMEDIT.md) e `tests/test_editor.py`. I comandi sopra installano
entrambi i programmi da questo repository. Avviare `fmedit appunti.txt`, oppure
sceglierlo per **F4** in fm:

```bash
EDITOR=fmedit fm
```

Dal checkout senza installazione: `EDITOR="$PWD/fmedit" ./fm`. F4 continua a
usare `$EDITOR`, con fallback a `nano` se non impostato. L'installazione non cambia
EDITOR né le associazioni MIME. **F2 / Ctrl+S** salva, **F10** salva ed esce,
**Esc / Ctrl+Q** chiede come gestire le modifiche non salvate. La guida descrive
selezione, appunti, annulla/ripeti, ricerca e limiti.

## Theme and navigation

Panes use a **dark gray background and muted yellow text** (ANSI 256 colors).
The active row has a teal background and light text. Executables, symbolic links
and marked entries have distinct colors.

Each pane shows **Name**, **Size** and **Last modified**, with bright yellow
headings as in Midnight Commander. Size is in bytes, switching to IEC units above
ten digits. Directory sizes describe the directory entry, without summing its
contents. Modification dates use `dd/mm/yyyy hh:mm` in the local time zone. Long
names are truncated to keep columns aligned. Vertical separators continue through
empty rows to the bottom of each pane.

Navigation follows Lynx conventions: **Up/Down** (or `k`/`j`) moves the highlighted
row; **Right/Enter** (or `l`) opens it; **Left/Backspace** (or `h`) goes to the
parent, highlighting the directory just left. `/..` does the same. Directories
have a `/` prefix, symbolic links an `@`. **Hidden files and directories (`.name`)
are visible by default**; Ctrl+H toggles them in the active pane.

Double-click timing accepts either a comma or a dot in `EPOCHREALTIME`, including
Italian locales.

## Keys

Press **?** while navigating to open scrollable help. **Up/Down**, **PgUp/PgDn**,
**Home/End** and the mouse wheel scroll; **Enter**, **Esc**, **?**, **F10** or the
**Close** button returns to the pane. Help also works in Connections and adapts
to resize. In the Ctrl+F dialog, `?` remains literal search text.

| Key | Action |
| --- | --- |
| **?** | Open help and shortcuts |
| **F1** | Open the personal Midnight Commander commands menu |
| **F2** | Rename the highlighted file or directory |
| **F3** / **Ins** / Space | Select/unselect (`*`) and advance one row |
| **F4** | Edit with `$EDITOR`, or `nano` if unset |
| **F5** | Copy selection to the other pane; ask for destination with one pane |
| **F6** | Move selection to the other pane; ask for destination with one pane |
| **F7** | Create a directory; type its name and press Enter |
| **F8** | Delete selected files/directories after confirmation (`y`) |
| **F10** | Quit and restore the terminal (`q` and `Q` do not quit) |
| **Ctrl+X**, then **C** | Open permissions, owner and group dialog |
| **Ctrl+X**, then **S** / **Ctrl+S** | Create an absolute symbolic link `<name>.lnk` |
| **Tab** | Switch panes when both are visible |
| **Ctrl+H** | Toggle hidden files and directories in the active pane |
| **Ctrl+F** | Filter by file name and content in the current directory |
| ↑ / ↓, `k` / `j` | Move the cursor |
| PgUp / PgDn, Home / End | Navigate quickly |
| **Right** / Enter / `l` | Open a directory/document or run an executable |
| **Left** / Backspace / `h` | Go to parent and highlight the directory just left |
| Left mouse button | Select a row; double-click opens it like Enter |
| Mouse wheel | Scroll the list |
| `r` | Refresh the list |
| Esc then 1…9 / 0 within 0.5 seconds | F1…F9 / F10 (F9 unassigned) |

Function buttons also support mouse clicks. On narrow windows labels shorten;
the commands retain the same function keys. The parent entry cannot be marked;
selecting the last entry keeps the cursor there. Clicking the selection mark
toggles it without advancing.

During a session, every directory remembers its highlighted entry, scroll position
and F3/Ins/Space marks. State is separate for each pane, works in single-pane mode,
and ignores entries that disappear. Going to the parent instead highlights the
directory just left and scrolls it into view.

With one pane, F5/F6 ask for an existing destination directory, absolute or relative
to the current directory; Esc cancels. After marking files in one directory, you
can navigate elsewhere and transfer the last explicit selection using its absolute
source paths. An empty Enter then selects the current directory as destination.
The selection is consumed after the transfer attempt. A vanished source reports
an error instead of transferring the highlighted destination file. Without marks,
operations use the highlighted entry.

## Two panes and filtering

At **100 columns** or more, two panes appear automatically, initially in the same
directory. **Tab** or a click switches the active pane, marked `*` in its title.
Each side retains its directory, cursor, scroll, selection, filter and hidden-file
setting. Narrowing the window leaves the active pane visible; widening restores
both and their state.

Open a destination in one pane, Tab back to the source, mark files with **F3**,
then press **F5** to copy or **F6** to move. Both lists refresh afterward. Existing
destinations are never overwritten. Errors show the first cause, such as the same
source/destination directory, an existing name, a destination inside the source,
or the error returned by `cp`/`mv`.

**Ctrl+F** opens **Filter**, with **File name** and **Content text** fields.
Search is literal, case-insensitive and limited to the **current directory**,
without recursion. Empty fields impose no restriction; if both are filled, both
must match. Names are also matched for directories. Content is searched only in
readable regular files, excluding symbolic links and binary files; text is not
extracted from PDFs, Office documents or archives. Emptying both fields restores
the full list.

**Tab** or mouse switches fields/buttons. Arrows, Home/End, Backspace/Delete and
**Ctrl+U** edit the field. **Enter** or **Search** applies the criteria; **Esc**,
F10 or **Cancel** closes without changing the previous filter. **Up/Down** browses
results, **Enter** opens the highlighted entry. No results leaves the view in
place; Ctrl+F edits the criteria and Esc clears them.

Clicking a row, marking with F3, opening an entry or running file operations clears
the filter while preserving the highlighted entry and marks. Applying a filter
clears pane marks. Each pane remembers its criteria; results are cached across
redraws and **r** repeats the search. **Ctrl+H** includes/excludes hidden entries
from the search too.

## This PC, SSH and FTP

From `/`, **Left**, Backspace or `/..` opens **Connections**, starting with:

- **This PC**: return to the local filesystem root.
- **SSH**: connect using **SFTP over SSH**.
- **FTP**: connect using FTP.

Enter, Right or double-click opens an entry. SSH/FTP ask for **`user@host`** (also
`user@host:port`) and a masked **password**. Leave the password empty to reuse the
system keyring; SSH also supports keys configured in OpenSSH or its agent. If SSH
host verification is needed, the terminal displays its fingerprint and choices;
the user must confirm trust. Esc cancels the dialog; Ctrl+C interrupts a connection.

Successful connections appear below the three fixed entries and persist across
restarts. **F2** renames a profile; **F8** deletes it after confirmation. Deletion
only removes the saved profile: it does not disconnect the mount or delete remote
files. Opening a saved connection shows its address and an empty password field.
Reconnecting to the same endpoint preserves the chosen name without duplicates.

For **local or remote directory bookmarks**, keep the **Connections root** in one
pane and highlight the directory to remember in the other. **Ctrl+X S** or
**Ctrl+S** adds it to Connections, with either pane focused. The initial name is
`<directory>.lnk`, renameable with F2. Existing names are never overwritten.
Without a Connections pane, the shortcut creates a normal link in the current
directory.

Bookmarks are real symbolic links under
`${XDG_CONFIG_HOME:-$HOME/.config}/fm/shortcuts/`. Local targets are absolute paths;
SSH/FTP targets are URIs containing the endpoint and remote path, never a password.
Manually added links are displayed too. Enter/Right/double-click opens the target.
Remote bookmarks reuse known mounts; after restart/disconnection they reopen the
prefilled connection dialog, then enter the saved directory. Passwords use the
keyring as for other connections. **F8** removes only the link after confirmation,
leaving the target and its contents intact. Broken local links remain visible and
can be renamed or deleted; their target appears in the status bar.

Profiles contain only protocol, address and name under
`${XDG_CONFIG_HOME:-$HOME/.config}/fm/connections/`, with permissions `0600`.
Last addresses from the previous version are imported once; deleted entries are
not recreated automatically. Successful connections also update `fm/last-ssh`
and `fm/last-ftp`, with permissions `0600`.

**Passwords are never written to fm files, process arguments or environment
variables**. They pass through an anonymous file descriptor; GVfs stores them in
the **system keyring** using
[PasswordSave.PERMANENTLY](https://docs.gtk.org/gio/enum.PasswordSave.html).
The empty password field never displays the secret: GVfs retrieves it while
connecting. The keyring must be available and unlocked and may show its own unlock
dialog. Without a keyring, typed-password connections remain possible, but fm
never creates plaintext copies. Manage credentials with Passwords and Keys
(Seahorse); F8 only deletes the fm profile.

Remote directories support normal navigation, selection, F5/F6 and file commands.
Left from the remote root returns to Connections. Panes may mix local and remote
directories. FTP copies do not preserve Unix attributes; moves across mounts remove
the source only after a successful copy. Remote permissions apply; server refusals
do not trigger local sudo. GVfs session mounts can be shared with other applications
and may remain connected after fm exits.

Optional remote support requires **`/usr/bin/python3`, `python3-gi`, `gvfs-backends`,
`gvfs-fuse`**, FUSE and an active user D-Bus session. Local operations remain usable
without these dependencies.

## Archives and symbolic links

**Enter**, **Right** or double-click opens an archive like a directory. Recognized
extensions include ZIP, TAR (also GZ, BZ2, XZ and ZST), TGZ, TBZ/TBZ2, TXZ, TZST,
7Z and RAR. Actual support depends on installed libarchive/GVfs backends. Some
7Z/RAR files require seeking that the backend cannot provide and report an error.
Paths display as `archive.zip!/directory`. Left, Backspace or `..` from the archive
root returns to its containing directory and highlights the archive.

**F3/Ins/Space** marks entries; **F5** copies files/directories outside the archive,
including into the other pane. Archive navigation is **read-only**: rename, edit,
move, delete, creation, attributes and commands menus are disabled inside; copying
new files into an archive is also blocked. To edit contents, copy them into an
ordinary directory first. The original archive remains unchanged.

Nested archives and archives on remote mounts are supported by copying only the
compressed file being opened into a private temporary directory, without extracting
the entire archive. Private mounts and copies are removed on exit. Archive links
may be followed only within the archive. Damaged/unsupported archives report an
error; encrypted archive password entry is not supported. Requires `gvfsd-archive`
from `gvfs-backends`, plus the GIO/FUSE stack used for SSH/FTP.

Highlighting a **symbolic link** shows **`Link -> target`** in the status bar,
including broken links. It displays the stored relative or absolute target.
Selecting another entry restores navigation help; operation messages occupy the
line below.

## F1 commands menu

**F1** reads the personal MC menu from `${XDG_CONFIG_HOME:-$HOME/.config}/mc/menu`,
falling back to `/etc/mc/mc.menu`. Entries and customizations are read every time,
including `.deb` installation, touch and ZIP commands if present. Entry-specific
programs must be installed. Personal menu labels and prompts retain their original
language.

**Up/Down**, **PgUp/PgDn**, **Home/End** select entries; **Enter**, the entry hotkey
or **Run** starts one. Mouse selection, double-click, wheel and buttons work too.
Esc cancels. MC conditions filter entries by name, directory, file type, selection
and executable availability, respecting `shell_patterns=0/1` and default choices.

Menu scripts run in Bash in the active pane directory. Supported macros are
`%f`/`%p` (current file), `%d` (directory), `%s` (marks or current file), `%t`
(marks), `%u` (marks to clear), their uppercase equivalents for the other pane,
`%%` and `%{prompt}`. Names are shell-quoted; `%0`/`%1` control quoting as in MC.
`%view{...}` sends output to `$PAGER` (default `less`); other commands leave output
in the terminal and wait for Enter. Scripts containing `sudo` keep their own
authentication prompts. The source MC menu is never modified.

## Execution and attributes

**Enter/Right/double-click** runs regular executable files directly, without eval.
The child receives the normal terminal on stdin/stdout/stderr; fm waits for Enter
when it finishes, then restores the TUI. Other regular files open with the desktop's
default MIME application through **`gio open`**: PDFs in a PDF reader, images in
an image viewer, text in the associated editor. Existing MIME associations are
respected and never changed. Archives keep opening inside fm. Single-click only
selects the row.

MIME opening requires `gio` (`libglib2.0-bin` on Debian/Ubuntu/Mint) and an associated
application. The file manager stays usable while the application runs. Missing
associations or launch failures appear in the status line. Change associations
through desktop preferences or `xdg-mime default name.desktop type/mime`.

**Ctrl+X C/S** are sequences: press Ctrl+X, release, then `c` for attributes or
`s` for a symbolic link. The old Ctrl+X O sequence is removed. Ctrl+S is direct.

- **Rename**: F2 opens the current name and a preselected new-name field. Typing
  replaces it; arrows, Home/End, Backspace/Delete edit, Ctrl+U clears. Tab cycles
  through the field and Rename/Cancel buttons. Enter confirms, Esc cancels; mouse
  buttons work too. An unchanged name does nothing; existing names are protected.
- **Permissions and owner**: Ctrl+X C opens nine **r/w/x** boxes for User, Group,
  Others, an octal field and **Users/Groups** lists from `getent`. Tab cycles the
  grid, users, groups and Apply/Cancel buttons. In the grid, arrows move and Space
  toggles a box; modes such as `755` or `0644` can be typed. Lists support arrows,
  PgUp/PgDn and Home/End; names, IDs or `user:group` can also be typed. Mouse selects
  boxes, entries and buttons. On short terminals Tab alternates the grid and lists
  in the same space. **Enter applies only changed fields; Esc cancels everything.**
- Rename, copy, move, mkdir/link creation, deletion, `chmod` and `chown` retry
  authorization errors with **sudo**, temporarily returning to the normal terminal.
  Only sudo reads the password; fm never reads or stores it. **Ctrl+C** cancels
  authentication and returns to fm. Other errors, such as an invalid user, do not
  request sudo. Results depend on the user's sudo privileges. Deletion confirmation
  and overwrite protection remain active. Ownership is applied before permissions
  to preserve requested special bits. chmod/chown are nonrecursive; chmod skips
  symbolic links.
- **Symbolic link** appends `.lnk` to the highlighted entry's full name, for example
  `file.txt.lnk`, in the current directory, pointing to an **absolute target**.
  Moving the link does not change its target; moving/deleting the original may
  break it. Existing files or links are never overwritten.

chmod/chown operate on F3-marked entries, or the current row without marks.
Link creation always uses only the current row. F4 passes the terminal to the
editor and restores the TUI afterward. `EDITOR` may include space-separated
arguments, for example `EDITOR="nano -w"`; it is not interpreted as shell code.
The editor must be installed.

## Redrawing

Cursor movement redraws only the previous and current rows. Scrolling redraws
only the active list without reloading the other pane. Queued navigation keys are
batched before drawing, retaining the next command. Full redraws handle directory
changes, refresh and resize. The bottom border emits no newline that could scroll
the screen or misalign mouse coordinates.

## Safety and limitations

- **No overwrites**: F2/F5/F6 report existing destinations as failures.
- F8 performs **permanent recursive deletion** (`rm -rf`) after explicit `y`/`Y`
  confirmation; it does not use the trash. Empty Enter cancels.
- Local copy preserves metadata and symbolic links using `cp -a`; move and rename
  use `mv`. Directories cannot be copied or moved inside themselves.
- Entries follow shell locale ordering. Long text is truncated; width uses Bash
  character counts, so double-width Unicode characters may misalign frames.
- Function-key sequences target common xterm/Linux terminals; graphical terminals
  may intercept F2–F8 and require shortcut changes.

## ai-bar integration

Run fm inside an embedded **PTY** or a terminal emulator supporting **xterm SGR
mouse sequences (1000/1006)**. It uses `/dev/tty`, noncanonical keyboard input,
standard ANSI sequences and, unless disabled, the alternate screen. Local use does
not require a GUI or desktop. A future selection mode could print a chosen path
to stdout; that mode is not implemented.

## Tests

Local operations use Bash; optional remote support uses Python 3/GIO. PTY tests
use only the Python standard library:

```bash
bash -n fm
bash -n fmedit
python3 tests/smoke.py
python3 -m unittest discover -s tests -p test_editor.py -v
shellcheck -S warning fm    # when installed
```

Temporary directories and pseudo-terminals cover filtering, independent panes,
Tab, resize, rename, interactive editors, multiselection, copy/move, mkdir, links,
deletion, overwrite protection, mouse/double-click/wheel, function buttons, prompts,
English help and affirmative/default-cancel deletion.

Optional real protocol tests also require `paramiko`, `pyftpdlib`,
`dbus-run-session` and the OpenSSH client. They run loopback servers with temporary
keys/directories and an isolated D-Bus session, with the keyring disabled by default:

```bash
/usr/bin/python3 tests/remote_integration.py
```

Add `--keyring` to test encrypted saving, keyring restart and SSH/FTP reconnection
without typing passwords. Also requires `gnome-keyring-daemon` and Python Secret
introspection (`gir1.2-secret-1`). Personal credentials/configurations are not used.

Optional archive tests use GVfs/FUSE on an isolated bus and temporary paths:

```bash
/usr/bin/python3 tests/archive_integration.py
```

They cover ZIP, TAR/GZ/BZ2/XZ, nesting, copying, return selection, two panes,
read-only restrictions and damaged archives. With `7z`, they also test reading
that format or reporting the backend's seek limitation.

## License

MIT; see [LICENSE](LICENSE).
