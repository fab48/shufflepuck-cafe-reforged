# web/ — the game

Plain HTML and JavaScript modules, no build step, no dependency.

| File | Original routines |
|---|---|
| `index.html` | welcome sequence (`$D138`, curtain `$EA62`), game loop order (`$DAA4`), rendering (`$D5B0`, `$F860`, painter's order `$DF00`), audio banks (`$112C0`) |
| `moteur.js` | the engine: player paddle `$FB7A`, puck `$1034C`, collisions `$FEEC`, the nine AIs `$10EAA`, obstacle `$10614` / `$1023C`, score `$D4D4` |
| `animation.js` | the self-rewriting animation scripts (`$F440`, `$F480`, `$F690`, `$F778`) |
| `robot.js` | the hand that chalks the score on the board (`$E262`) |
| `bar.js` | the bar, where you pick your opponent (`$1205A`) |
| `menu.js` | the Space-bar menu, its dialogs and sliders (`$1299E`, `$1348C`) |
| `fonte.js` | the game font `quete.fnt` (`$14FA4`) |
| `assets/` | produced by `tools/exporter_web.py`; `manifeste.json` holds every table read from memory |
| `assets/se_*` | **not** from the disks: the special edition's remastered graphics (F10) |

Run it with `python -m http.server 8731 --directory web` from the project
root. `?debug` shows the engine state, `?muet` starts muted.

Two things matter when reading the code: the 68000 divides by truncating
towards zero (`DIVS`), so everything goes through `div()`, and every `.w`
operation wraps to 16 bits, through `w16()`.
