# Maintaining fm

Linux one- or two-pane TUI file manager. The source and entry point is `fm`, a
Bash 4+ script using stty, GNU commands and /dev/tty, without TUI libraries.

vroby's preference (16 November 2026): make changes in the local checkout, then
commit and push directly to the intended branch. Do not open pull requests.
fm updates include local installation and GitHub publication. After verification,
commit and push without asking for additional confirmation, preserving unrelated
changes.

`main` documentation is in English; `italiano` has Italian installation
instructions and an Italian editor guide. Earlier merges aligned the current
scripts and tests in both branches with the English version. Keep prompts and
confirmation answers consistent with PTY expectations. Port functional updates
explicitly to both branches. Installation URLs must use the intended branch.

## Terminal and file operations

The script handles keyboard/mouse input, selection, rendering and file operations.
Always restore the terminal on exit. Preserve permanent-deletion confirmation and
protection against overwriting existing destinations. F5/F6 display the first
error before summary counts; cp/mv errors pass through `safe`. Public variables
ABFM_NO_ALT_SCREEN, ABFM_NO_COLOR and ABFM_ASCII are documented in the README.

`file_command` handles rename, copy, move, mkdir, delete, link, chmod and chown.
It retries only C-locale authorization errors with `sudo --`; `run_program` gives
sudo the original terminal and returns its exit status. These helpers are grouped
beside file operations. Copy/move share `transfer_command`, counts and errors.
Only sudo handles passwords; Ctrl+C returns to the TUI. Test sudo through PTY
stubs, never real privileges. Apply ownership before permissions because chown can
clear special bits. chmod/chown are nonrecursive and chmod skips symlinks.

F2 opens `rename_dialog` with the name preselected; typing replaces it. Support
arrows/Home/End/Backspace/Delete/Ctrl+U, Tab and mouse between field and buttons,
Enter to confirm and Esc to cancel. Unchanged names do nothing. F3 marks, F4 opens
$EDITOR (fallback nano), F5 copies and F6 moves to the other pane, asking for a
destination in single-pane mode. F7 creates directories, F8 confirms deletion,
F10 exits. q/Q never quit, even on a small terminal; F10 remains available there.
Resize redraws the background first.

Modal windows use the MC modarin256-thin palette (`CLR_DIALOG*`), centered titles,
focused Apply/Cancel buttons and mouse support. `modal_frame` supplies coordinates
to `modal_buttons` and `modal_button_at`; `modal_cancel` sets the notice and redraw
without deciding the caller's return code. Ctrl+X C opens `attributes_items`:
one window for chmod/chown with an rwx/octal grid, getent users/groups lists and
five focus areas. Short terminals alternate grid and lists in the same space.
Only modified fields are applied. Ctrl+X O is removed; Ctrl+X S and Ctrl+S create
absolute `<name>.lnk` links. `ixon` is disabled in the TUI to receive Ctrl+S; child
programs and editors receive the original terminal.

## Panes, filters and navigation

At 100 columns there are two panes. Tab/mouse switches sides; `save_pane` and
`load_pane` retain directory, cursor, scroll, filter and marks. Hidden-file
visibility is shared. Columns Name, Size (bytes, IEC above ten digits) and
Last modified (local `dd/mm/yyyy hh:mm`) have headings at row 3 and data from row 4. `entry_columns`
maintains widths/separators in Unicode/ASCII, including empty rows to the bottom.
The palette uses dark gray, muted yellow and teal selection; column headings use
MC's bright bold ANSI yellow (`CLR_HEADER`). Without colors, the active cursor
uses `>` in the padding immediately before the selection mark. `draw_panel` uses
local Bash state to render the inactive pane without changing the active one.

Ctrl+F opens `filter_items`, with local name/text fields and Search/Cancel buttons.
Enter applies `filter` and `content_filter` together; Esc/F10 cancel without
changing existing criteria. Search is literal, case-insensitive, current-directory
only: names include directories, content uses GNU grep -iIFq only on readable
regular files, excluding symlinks and binaries. Fields support Tab/mouse, arrows,
Home/End/Backspace/Delete/Ctrl+U. `pane_contents` parallels `pane_filters`;
`search_cache`/`search_counts` retain each pane's results. `load_pane` calls
`reload cached "$id"` to avoid rereading contents during redraw/focus changes.
Applying criteria and r call reload without cache. Toggling hidden files,
`file_command` and return from `run_program` invalidate both panes' caches. Local
state in draw_panel, menu_other_panel and add_shortcut includes content_filter.

Esc in a pane calls `clear_filter` for both fields. Enter/Right with zero matches
does not navigate. Row clicks, F3, opening and operations clear filters while
preserving the highlighted item and marks; screen position remains stable for
double-clicks. Up/Down browse filtered results. Ctrl+h and Alt+. toggle dotfiles
in both panes, clear selection in the active pane and retain both filter criteria.
Ctrl+h uses 0x08, Alt+. uses Esc followed by a dot, and Backspace uses 0x7f.
Resize preserves both panes and the shared visibility setting.

`change_directory` retains session memory in `directory_focus`/`directory_scroll`
per pane+cwd and `directory_marks` per pane+path (value cwd), then restores only
visible surviving entries. Remember cursor by path, not index. Update the snapshot
on each departure; marks consumed by operations must not reappear. `go_parent`
uses this transition but highlights the directory left and adjusts scroll.
`selection_sources` remembers each pane's last explicit marking directory. Only
F5/F6 call `collect transfer`, recovering absolute sources from `directory_marks`
in single-pane mode even after navigating elsewhere. Empty Enter in the destination
prompt uses cwd when sources are elsewhere. After an attempt, remove target marks
from memory and clear the selection source. F8/attributes remain local to cwd.
Missing sources must never fall back to the highlighted destination file.

`selection_status` sanitizes the raw readlink target with `safe` and displays it
for the active pane, including broken links. `draw` keeps `painted_status` separate
from notice, redrawing only when changed; operation messages are not overwritten.

`input_key` maps Esc followed within 0.50 seconds by 1…9/0 to F1…F9/F10 (F9 unused),
and CSI 2~ (Ins) to F3. Esc alone cancels after timeout. F3/Ins/Space mark and advance;
.. cannot be marked and the last row stops the cursor. `select_current` does not
advance, preserving mouse behavior. On scroll, redraw only active rows without
load_pane/reload on the other pane. The main loop batches up to 256 queued navigation
keys, preserving and executing the first other command. The filter dialog reads
characters independently of this loop. Test decoding, delayed Esc+digit, selection
bounds, queued bursts and a following rename in one/two panes.

## MC commands menu

F1 calls `user_menu`, reading `${XDG_CONFIG_HOME:-$HOME/.config}/mc/menu`, falling
back to `/etc/mc/mc.menu`. `load_user_menu` reads scripts/conditions (+, =, =+);
`menu_condition` evaluates left to right without eval. `expand_user_command`
shell-quotes macros, prompts and view directives. Uppercase macros use the opposite
pane; %u/%U clear marks. Explicit menu scripts run via `run_program` in cwd; %view
uses PAGER/less. Preserve personal MC customizations and their language without
changing the source menu. Tests must use temporary menus and never run real
installation, mail or remote commands. The F1–F10 bar has three widths with hitboxes
derived from its labels.

? opens `show_help` in panes and Connections, remaining literal in the filter.
Help reads usage, wraps with GNU fold to available width and supports arrows,
Pg/Home/End, wheel, resize and Close. Enter/Esc/?/F10 closes help without exiting fm.

## MIME opening

`enter_dir` retains directory → archive → executable precedence; other regular
files go to `open_document` through Enter/Right/double-click. It invokes gio open
with a quoted absolute path, stdin/stdout on /dev/null, stderr in mktemp, reporting
sanitized errors without corrupting the TUI. No eval, extension table or MIME
association changes. GIO is optional (libglib2.0-bin). Executables still use
`run_executable` with the interactive terminal. Broken links never reach the
launcher; archive external-link checks remain. PTY tests intercept only gio open,
delegating other GIO operations. A separate real-GIO test uses temporary XDG MIME
associations and desktop entries without changing personal preferences.

## Archives

`is_archive_file` recognizes extensions; `open_archive` uses the Python helper in
`remote_mount` with protocol archive. Quote the file URI for mounting, then quote
it a second time for the published root used by find_enclosing_mount.
`archive_sources` maps FUSE roots to originals; `display_path` recursively composes
`!/` paths; `go_parent` returns to and highlights the archive. Nested/remote archive
files must be copied to a private mktemp directory because the backend cannot read
other GVfs mounts directly. `archive_cache` tracks only those private mounts;
cleanup unmounts before deleting copies, leaving shared original mounts alone.
Never extract the entire archive.

`perform_key` blocks archive modifications; `transfer_items` rejects archive
destinations and F6 from remembered archive selections outside cwd. `file_command`
must never propose sudo for archive paths. F5 stays available. Do not execute
archive files or follow links outside the FUSE root. Separate archive integration
tests use fixtures and a temporary bus/runtime, covering navigation/copy/return,
nesting, two panes, read-only restrictions, external links and errors, with 7Z
optional.

## Connections and bookmarks

The virtual `connections_root` (`@connections`) sits above `/`. reload generates
local/ssh/ftp and calls `load_saved_connections`; paint_entry shows This PC/SSH/FTP
and saved names. perform_key routes F2/F8 to saved-entry operations and blocks other
file operations. `change_directory` handles the virtual root; go_parent enters it
from local/remote roots. `remote_protocols` distinguishes FTP/SFTP. `display_path`
replaces FUSE paths with readable labels; virtual views retain normal pane state.

`save_connection` atomically writes protocol, address, name as three lines under
`fm/connections/<sha256(protocol + NUL + address)>`, permissions 0600. Names are
labels, never paths. Reconnecting preserves aliases without duplication.
`load_saved_connections` imports last-ssh/last-ftp only when connections does not
exist; preserve that directory after F8 so deleted profiles cannot reappear.
F2 reuses rename_dialog; F8 confirms profile-only removal. `profile:<id>` passes
protocol/address to connect_remote, always showing an empty password dialog.

`connection_dialog` keeps address/password local to `connect_remote`.
`remote_mount` contains the optional Python/GIO helper. Passwords pass through a
process-substitution FD, never argv/env/files. Result files hold only a path/error.
GIO uses PasswordSave.PERMANENTLY; GVfs stores successful passwords in the system
keyring and retrieves them before ask-password. SSH host trust requires terminal
confirmation. Wait briefly for FUSE export after mounting; keyring authentication
can finish first. Remember addresses/profiles only after successful connection,
with atomic 0600 writes. Never fall back to plaintext secrets. The field stays
empty with keyring-reuse help. F8 only removes profiles; do not automatically
unmount shared GVfs mounts on exit or try local sudo for remote permission errors.
FTP copies do not preserve Unix attributes; cross-mount F6 removes only after a
successful copy.

`shortcuts_dir` is fm/shortcuts under XDG config; reload appends real symlinks,
including broken ones, after profiles. With Connections in one pane, Ctrl+X S or
Ctrl+S calls add_shortcut on the directory highlighted in the other, regardless
of focus. Default basename.lnk, no overwrites. Without Connections, create_symlink
retains normal behavior. Local targets are physical absolute paths; remote targets
are quoted sftp:// or ftp:// URIs with no credentials. `remote_addresses` parallels
labels/protocols to reconstruct endpoints. `open_shortcut` decodes URIs and reuses
mounts or calls connect_remote with an additional remote path, retaining the
normal dialog/keyring/profile behavior. F2 reuses rename_item with shortcuts_dir
as destination; F8 confirms and uses rm without -r to remove only the link.
Test creation, opening, persistence, rename, safe deletion, existing/broken links,
duplicate protection, both focuses and help scrolling/resize/return. Remote tests
cover saved paths with spaces/Unicode through reuse/restart/disconnection and
SFTP password/key plus FTP.

## Verification and installation

Change `fm` for behavior, `README.md` for usage/installation and `tests/smoke.py`
for PTY checks. `.github/workflows/test.yml` runs checks on GitHub. Install with
`install -Dm755 fm "$HOME/.local/bin/fm"`.

Before completing changes, run from the project root:

```bash
bash -n fm
python3 tests/smoke.py
```

When available, also run `shellcheck -S warning fm`. For manual verification run
`./fm` interactively and quit with F10. Review the diff and update README/this guide
when structure, public options, invariants or verification commands change.
Tests use standard Python and temporary directories.

Optional remote verification: `/usr/bin/python3 tests/remote_integration.py`, with
paramiko/pyftpdlib and GVfs. Servers are loopback only; SSH keys/config, D-Bus and
keyring services are isolated in temporary directories. With `--keyring`, start
gnome-keyring-daemon on that private bus, with temporary HOME/XDG/control-directory
and a fixture password. Verify the secret with libsecret, restart the daemon,
unmount before reconnection and check that keyring files do not contain plaintext
secrets. Terminate the daemon afterward. Without --keyring, cover connections
without secret services. Never test credentials or changes on real devices.

Optional archives: `/usr/bin/python3 tests/archive_integration.py`, using only
fixtures and an isolated bus/runtime. Do not touch personal mounts.

## Bundled fmedit

`fmedit` and `tests/test_editor.py` are included in this repository. User commands
and limits are in [FMEDIT.md](../FMEDIT.md); editor maintenance invariants are in
[fmedit.md](fmedit.md). F4 still uses EDITOR with nano as fallback. Install the
editor with `install -Dm755 fmedit "$HOME/.local/bin/fmedit"` in addition to fm.
Run `bash -n fmedit` and
`python3 -m unittest discover -s tests -p test_editor.py -v` as well as fm checks;
GitHub Actions runs both suites. Keep future editor updates and their tests here.
