# Shufflepuck Café — reforged

A complete reverse-engineering of **Shufflepuck Café** (Atari ST,
Brøderbund/Loriciel, 1989, by Christopher Gross), and a faithful rebuild of
the game for the web, from an original copy of the disks.

**Play it:** <https://fab48.github.io/shufflepuck-cafe-reforged/>

Nothing is redrawn and nothing is guessed: the images, sounds, physics,
opponent AI, animations and menus are read byte by byte from the disks and
from the 68000 code, then transcribed. Where the original could not be read,
the code says so (`RECONSTRUCTION`).

## Playing

- **Online** — the link above, rebuilt from `web/` on every push.
- **One file** — [`dist/shufflepuck.html`](dist/shufflepuck.html) holds
  everything (code, images, sounds). Download it and double-click it: no
  server, no Python, no Node.
- **From the sources** — ES modules need a server. From the project root:

  ```bash
  python -m http.server 8731 --directory web
  ```

  or double-click `run/web.bat`, then open <http://localhost:8731>.

**Controls, as on the ST.** The mouse drives your paddle; holding the
button gives the harder shot. Click the table to capture the mouse, *Esc*
releases it. **Space** opens the original menu:

| Entry | What it does |
|---|---|
| `scores` | the hall of fame |
| `jeu` | new game, new opponent (back to the bar) |
| `palette` | your paddle: size, and the physics of both buttons |
| `obstacle` | none, small, medium, large, or your own sliding block |
| `robot` | only against **Dc3**, the training robot: every one of its parameters |

**F10** (or the *version* button in the banner) crossfades, at any time, to
the **special edition**, in the manner of *Monkey Island Special Edition*:
the same game, the same 68000 logic, with remastered graphics. For now,
the title screen and the table are remastered; the rest keeps its original
pixels. `?se` in
the address starts in the special edition.

Right-click closes a menu. In a dialog, drag the sliders, then **SET-IT**
to keep or **CANCEL** to undo. The banner has a full-screen button, a mouse
sensitivity slider and a sound toggle (`?muet` in the address starts muted,
`?debug` shows the engine state). On the welcome screen, a click skips the
music, then the disk loading.

Modern mice are far more sensitive than the ST's ball mouse, and the game's
collision is swept: a paddle flicked at full speed covers half the table in
one frame. The game therefore asks the browser for raw mouse movement (no OS
acceleration, Chrome and Edge) and scales it by the slider, identically on
both axes, as the original does. Everything after that is the 68000's.

## What was done

**The disks.** Neither disk has a usable file system (the FAT is a decoy,
the game reads absolute sectors). Every file was found by its signature and
verified by an exact size match; every decompressor is a transcription of
the game's own loader.

| Format | What it is |
|---|---|
| `.PC1` | Degas Elite screens (PackBits) |
| `.CPL` | sprite banks (RLE with an inverted convention) |
| `.TC0` | the nine opponents: sprites *and* voice (byte-pair encoding) |
| `.ECH` | sound banks |

**The sound.** An STF has no DMA audio. The game still plays digitised
sound: each sample byte indexes a table of YM2149 volume triplets, one byte
per Timer A tick. The puck's bounce is not 23 recordings but one, replayed
at 23 timer divisors.

**The code.** Recursive 68000 disassembly seeded by the compiler's
`link a5` prologues, then a routine-by-routine transcription: the game loop,
the puck and its collisions, the nine AIs, the 3D paddles and painter's
order, the animation scripts that rewrite themselves, the robot hand that
chalks the score, the bar, the menu system and its dialogs, the obstacle,
the welcome sequence. Timing was measured in the emulator (25 fps, and the
recorded slowdown while the glass shatters).

How it was done, step by step, with the tools: **[METHODOLOGY.md](METHODOLOGY.md)**.

## Repository layout

```
web/            the game (HTML + JavaScript modules) and its assets
dist/           the single-file build
tools/          extraction, disassembly and build tools (Python)
run/            Hatari launchers and configuration, to play the original
work/assets/    raw extraction output (the rest of work/ stays local)
METHODOLOGY.md  the method, in English
PHYSICS.md      engine specification (French)
ASSETS.md       file formats and what came out of them (French)
FINDINGS.md     the research journal, mistakes included (French)
```

The French notebooks are kept as they were written: they carry the
evidence, address by address, and every correction with its cause.

## Rebuilding

```bash
python tools/exporter_web.py      # web/assets from the disk images and RAM dumps
python tools/construire_html.py   # dist/shufflepuck.html
```

The disk images and RAM dumps (`work/`) are not versioned: they come from
your own original disks (see `METHODOLOGY.md`).

## Thanks

Thanks to Colin Leroy-Mira, whose earlier [port of Shufflepuck Café to the
8-bit Apple II](https://www.colino.net/wordpress/archives/2026/02/23/the-challenges-of-porting-shufflepuck-cafe-to-the-8-bits-apple-ii/)
was both inspiring and instructive.

## Rights

The reverse-engineering code is ours; the game's images, sounds and data
are not. Shufflepuck Café belongs to its rights holders (Brøderbund → The
Learning Company → Mattel → Gores → Ubisoft for the game catalogue, 2001 —
never re-released since 1989). The assets were extracted from an owned
original copy. One sound is not from the game: the floppy-drive noise on
the welcome screen ("reading floppy disc 2", freesound_community).
