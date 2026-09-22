# Methodology — how the game was taken apart and rebuilt

This is the working method behind the project, written so that the whole
process can be repeated from an original pair of disks. The detailed
evidence lives in the French notebooks: `ASSETS.md` (file formats),
`PHYSICS.md` (engine specification), `FINDINGS.md` (the journal, including
every mistake and how it was caught).

## The one rule

**No claim without the bytes that carry it.** Every offset, format and
constant is tied to an address in the original program or a sector on the
disks. What is *not* read from the original is labelled `RECONSTRUCTION` in
the code, and listed as such. When the code and a memory of the game
disagree, the code wins — but a visual report from someone who played it is
a reason to go and re-read the code (that is how a sprite-mirroring bug was
found, see `FINDINGS.md`).

## 1. From disks to raw images

The originals are Pasti `.STX` dumps (disk 1 is copy-protected: track 79
carries 70 phantom sectors).

    python tools/stx_image.py work/disks/disk1.stx work/img/disk1.img

Neither disk has a usable file system: the FAT is blanked and the directory
is empty. The game reads by absolute sector through its own directory
(256-byte units). So files are found by **signature**, and every hit is
**verified by an exact size match** (compressed length, then decompressed
length) before it is trusted:

| Tool | Format |
|---|---|
| `tools/trouver_pc1.py` | `.PC1`, Degas Elite screens (PackBits, line-planar) |
| `tools/trouver_cpl.py` | `.CPL`, sprite banks (RLE with an inverted convention) |
| `tools/trouver_tc0.py`, `tools/tc0.py` | `.TC0`, the nine opponents (byte-pair encoding) |
| `tools/trouver_ech.py`, `tools/extraire_ech.py` | `.ECH`, sound banks |
| `tools/extraire_voix.py` | each opponent's voice (part 0 of its `.TC0`) |
| `tools/carte_disque.py` | the sector map: what is identified, what is not |

Each decompressor is a transcription of the game's own loader (the address
is in the tool's docstring), not a guess at the format.

## 2. From a running game to a memory image

Code and live data are read from RAM snapshots taken in **Hatari** (1.8,
`--machine ste` to avoid a blocking TOS dialog, accurate FDC, no speed
hacks — see `run/NOTES.md`).

- `run/jouer.bat` runs the original; `run/capturer.bat` records an AVI.
- Hatari's debugger dumps memory on a breakpoint (`work/dump/setup.txt`,
  `on_break.txt`), or `tools/extract_ram.py` extracts RAM from a `.sav`
  snapshot. Several dumps exist on purpose: `loaded.ram` has some code
  bytes overwritten, so code is read from `tr.ram`, data from `loaded.ram`.

## 3. Disassembly

68000, with [capstone](https://www.capstone-engine.org/).

- `tools/recursif.py` — **recursive** disassembly: only follow what can
  execute, never sweep linearly through data. Seeds: known entry points,
  interrupt handlers installed at run time, the targets of the compiler's
  jump tables, and — the decisive one — function prologues: this compiler
  opens every function with `link a5,#-N`, and a `4E 55` right after an
  `rts` is a function.
- `tools/pointeurs.py` harvests function-pointer tables that `jsr (a0)`
  hides from recursion.
- `tools/lister.py` prints an annotated listing of a range (call sites,
  data holes); `tools/disasm.py` shows one function, or cross-references.
- `tools/chaines.py` lists strings and who uses them; `tools/carte.py`
  gives an honest coverage figure (code / data / empty).
- `tools/editeur.py` decodes the parameter editor the developers left in
  the binary: French labels and bounds for every engine field.

## 4. Transcription

The engine is rewritten routine by routine in `web/*.js`:

- each function carries the **address** of the original routine;
- global variables keep the name of their address where it helps checking;
- arithmetic is 16-bit: `w16()` wraps like a `.w` operation and `div()`
  truncates towards zero like `DIVS` (`Math.floor` would be wrong for
  negatives); `MULU` keeps the low 16 bits;
- data are never typed in by hand: `tools/exporter_web.py` reads them from
  the RAM image (opponent table, animation scripts, menus and dialogs,
  font, glass shards…) into `web/assets/manifeste.json`;
- polling loops of the original (wait for a button, redraw, swap) become
  `async` functions that yield one frame per screen swap.

## 5. Measuring, not assuming

Timing is measured on the original, not inferred: an AVI recorded in
Hatari at every VBL is cut into frames (`tools/extraire_avi.py`), and
frames are compared to find when the screen actually changes. That is how
the game runs at **25 fps** (one screen swap every two VBLs) and how the
slowdown after a point (7–8 VBLs per frame while glass shards fly) was
recorded as a table rather than modelled.

## 6. Building and shipping

    python tools/exporter_web.py        # assets + manifest from disks and RAM
    python tools/construire_html.py     # dist/shufflepuck.html, one self-contained file

Every push to `main` deploys `web/` and the single-file build to GitHub
Pages (`.github/workflows/pages.yml`).

## What is not original

Listed in the code as `RECONSTRUCTION` or as a deliberate addition:
the mouse input scaling (raw browser movement times a user-set factor,
the same on both axes as in `$15AB6` and `$FB7A`), clicks that skip the
welcome music and disk loading, the 2-second wait on the Brøderbund crowns (the original chains as soon as
the music is loaded), the frame rate of the menu and bar screens (25 fps,
not measured), a blank score board when a new opponent is chosen (the
original wipes it with the sponge), the tournament flag `$1B596` assumed
off, the disk-2 prompt placed on the welcome screen as a wink (the box
itself is the game's), and the floppy-drive noise that follows — a
recording, not a sound from the game (`tools/bruit_disquette.py`).
