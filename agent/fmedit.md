# Maintenance guide

`fmedit` is a Linux terminal editor written in Bash 4+, with no compilation or
ncurses dependency. See `../FMEDIT.md` for commands and supported limitations.

`fmedit` was imported with its tests from the corresponding upstream branch.
Current source and tests are English in both branches after earlier merges.
Keep prompts and accepted answers consistent with PTY expectations. Port functional
changes to both branches and update the editor guide in each branch’s language.

- `fmedit`: the only source and executable. `z_main` initializes the terminal and
  starts the input, dispatch and rendering loop. It can be sourced to test
  functions without starting the interface.
- `tests/test_editor.py`: buffer, save and pseudo-terminal tests using only the
  Python standard library.
- User installation: `install -Dm755 fmedit "$HOME/.local/bin/fmedit"`.

The ANSI `Z_*` palette matches `fm` for the editor, selection, bars, prompts and
help. Style changes must retain an explicit background.

Buffer changes must respect selection and undo/redo history. History stores
replaced and inserted ranges, edit location and cursor, never full buffer copies.
`z_checkpoint` receives the start, end and inserted text before replacement.
`z_index` maintains `buffer_lines` and `buffer_offsets` in characters, rebuilding
them when `text` changes; `z_location` searches the index and rendering accesses
only visible lines. An empty final line represents the buffer's final newline.
Preserve supported file bytes exactly and reject NUL. Saving uses a temporary
file in the destination directory, preserves permissions and follows symlinks.
Rendering must never execute control sequences from files. Every exit must
restore the terminal. Trap functions must account for Bash dynamic variable
scope, including `IFS`.

Verify from the project root:

```bash
bash -n fmedit
python3 -m unittest discover -s tests -v
./fmedit --help
./fmedit --version
git diff --check
```

For manual verification, open a temporary file with `./fmedit`, edit, save with F2
and quit with Ctrl+Q. Update the README and this guide when commands, dependencies,
structure, invariants or verification procedures change. Run relevant checks and
review the diff before finishing.
