# Piano Tiles — Build Plan

For architecture and component breakdown see [project.md](project.md). This file is the executable build plan.

## Rules of this plan

- Every step has **test criteria**. A step is only marked `[x]` when **all** of its tests pass.
- If a test fails, **stop** — the step is not done. Fix the implementation (or the test if the test is wrong) and rerun. Do not start the next step until the current step is fully green.
- A phase is marked `[x]` only when **all** of its steps are `[x]`.
- Steps within a phase are numbered starting from `1`.
- Dependency management uses `pyproject.toml` (PEP 621). Do not create a `requirements.txt`.

---

## [x]  Phase 1 — Project & test infrastructure


### [x]  Step 1 — Initialize the project with `pyproject.toml`

- Create `pyproject.toml` with project metadata, Python ≥ 3.11, runtime dep `pygame`, dev deps `pytest` + `pytest-cov`.
- Create the package skeleton: `piano_tiles/__init__.py`, `piano_tiles/components/__init__.py`, `piano_tiles/models/__init__.py`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/ui/__init__.py`.
- **Test criteria:**
  - `pip install -e ".[dev]"` succeeds in a clean venv.
  - `python -c "import piano_tiles"` exits 0.
  - `pytest --collect-only` discovers the (empty) test tree without errors.


### [x]  Step 2 — Configure `pytest` markers and headless UI test environment

- Add `[tool.pytest.ini_options]` to `pyproject.toml` declaring `unit` and `ui` markers.
- Add `tests/conftest.py` that sets `SDL_VIDEODRIVER=dummy` for any test marked `ui` and provides fixtures: `seeded_rng`, `fake_clock`, `headless_surface`.
- **Test criteria:**
  - A placeholder test marked `@pytest.mark.unit` runs without initializing pygame.
  - A placeholder test marked `@pytest.mark.ui` initializes pygame headlessly and creates a `Surface` without opening a window.
  - `pytest -m unit` runs only unit tests; `pytest -m ui` runs only UI tests; both green.
  - Unknown marker usage raises a warning (strict markers configured).


### [x]  Step 3 — Wire up coverage reporting

- Configure `pytest-cov` in `pyproject.toml` to report on `piano_tiles/`.
- **Test criteria:**
  - `pytest --cov=src/piano_tiles` runs and prints a coverage report.
  - Coverage report includes every module under `piano_tiles/` (even those with 0% coverage).
  - CI-friendly exit code: passes when there are no failing tests.

---

## [x]  Phase 2 — Pure-logic components

All components in this phase are plain Python; no `pygame` imports. Each step adds the component **plus its unit tests** in the same change.


### [x]  Step 1 — Implement `Config`

- Constants: `LANE_COUNT`, `LANE_KEYS`, `WINDOW_W`, `WINDOW_H`, `HIT_ZONE_TOP`, `HIT_ZONE_BOTTOM`, `BASE_FALL_SPEED`, `BASE_SPAWN_INTERVAL`, `TILE_HEIGHT`, color constants.
- **Test criteria:**
  - `LANE_COUNT == len(LANE_KEYS)` (invariant test).
  - Window dimensions are positive; hit zone lies inside the window (`0 < HIT_ZONE_TOP < HIT_ZONE_BOTTOM < WINDOW_H`).
  - Speeds and intervals are strictly positive.
  - All color constants are valid RGB tuples (length 3, each in `0..255`).


### [x]  Step 2 — Implement `Tile` (model)

- Fields: `lane: int`, `y: float`, `height: float`, `speed: float`, `state: Literal["falling","hit","missed"]`.
- Method: `update(dt: float)` advances `y` by `speed * dt` while `state == "falling"`.
- Method: `bottom` / `top` properties.
- **Test criteria:**
  - `update(dt)` moves the tile by exactly `speed * dt`.
  - `update(0)` is a no-op.
  - `update(dt)` on a `hit` or `missed` tile does **not** change `y`.
  - Negative `dt` raises `ValueError` (edge case: time cannot go backwards).
  - Negative or zero `speed` raises `ValueError` at construction.
  - `lane` out of `0..LANE_COUNT-1` raises `ValueError` at construction.
  - `top` and `bottom` are consistent: `bottom == y + height`.


### [x]  Step 3 — Implement `StateMachine`

- States: `MENU`, `PLAYING`, `PAUSED`, `GAME_OVER`.
- Events: `START`, `PAUSE`, `RESUME`, `DIE`, `RESTART`, `QUIT`.
- Transition table is data-driven (a dict of `(state, event) -> next_state`).
- **Test criteria:**
  - Initial state is `MENU`.
  - Every valid transition listed in `project.md` works: `MENU --START--> PLAYING`, `PLAYING --PAUSE--> PAUSED`, `PAUSED --RESUME--> PLAYING`, `PLAYING --DIE--> GAME_OVER`, `GAME_OVER --RESTART--> PLAYING`, any state `--QUIT--> (terminal)`.
  - Invalid transitions (e.g., `MENU --PAUSE-->`) raise a specific exception or return `False` without changing state — pick one and test both branches.
  - Sending an unknown event raises a clear error.
  - Idempotency edge case: `RESUME` while already `PLAYING` is rejected (or no-op — whichever we pick, test it).


### [x]  Step 4 — Implement `TileSpawner` (algorithm component)

- Takes an injected RNG and an injected clock (or just `dt` per call).
- `update(dt) -> list[Tile]` returns the tiles spawned since last call (often empty).
- Spawn interval shrinks with elapsed game time (difficulty ramp), bounded by a minimum.
- **Test criteria:**
  - Determinism: with the same seed and the same `dt` sequence, two spawners produce identical tile sequences (lanes + spawn times).
  - Spawns exactly one tile per elapsed `BASE_SPAWN_INTERVAL` when no ramp is configured.
  - Spawns 0 tiles when `dt` is smaller than the interval.
  - Spawns N tiles when `dt` covers N intervals in one call (edge: large `dt`).
  - Lane indices are always in `0..LANE_COUNT-1`.
  - Difficulty ramp: after T seconds of play, the effective interval is strictly less than `BASE_SPAWN_INTERVAL` but ≥ the configured minimum.
  - Minimum interval is respected: interval never drops below the floor regardless of elapsed time.
  - `dt < 0` raises `ValueError`.


### [x]  Step 5 — Implement `HitDetector`

- Input: a lane index pressed + the current list of tiles + the hit-zone bounds.
- Output: a verdict — `HIT(tile)`, `WRONG_KEY`, or `IGNORED` (e.g., not in `PLAYING` state — although that decision can also live in `Game`).
- **Test criteria:**
  - Tile fully inside the hit zone + correct lane key → `HIT`, and the tile's state is updated to `hit`.
  - Tile above the hit zone (not yet arrived) + lane key → `WRONG_KEY`.
  - Tile below the hit zone (already passed) + lane key → `WRONG_KEY`.
  - No tile in the pressed lane (lane is empty) → `WRONG_KEY`.
  - Tile is in another lane (lane is empty for the pressed lane) → `WRONG_KEY`.
  - Edge: tile's top exactly at `HIT_ZONE_TOP` → `HIT` (decide and test the boundary).
  - Edge: tile's bottom exactly at `HIT_ZONE_BOTTOM` → `HIT` (decide and test the boundary).
  - Edge: multiple tiles in the same lane both in the zone → the lowest one (closest to bottom) is the one hit; the other is unaffected.
  - A tile already in state `hit` is not re-hittable.
  - Detecting that a tile has been **missed** (fully below the zone, still `falling`) flips its state to `missed` — verify via the spawner/update tick, with a unit test that constructs a tile past the zone and asserts the detector marks it `missed`.


### [x]  Step 6 — Implement `ScoreKeeper`

- Methods: `on_hit()`, `on_miss()`, `reset()`, `score` property, `combo` property.
- **Test criteria:**
  - Initial `score == 0`, `combo == 0`.
  - `on_hit()` increments `score` by the configured per-hit value and increments `combo`.
  - `on_miss()` resets `combo` to 0 and does not decrement `score` (score is monotonic non-decreasing during a run).
  - `reset()` returns both to 0.
  - Combo multiplier (if used): after N consecutive hits, score increment is the multiplier-adjusted value — test the threshold and the value just below/at/above.

---

## [x]  Phase 3 — IO components


### [x]  Step 1 — Implement `InputAdapter`

- Maps `pygame.KEYDOWN` events to game events using `Config.LANE_KEYS`.
- Outputs: `LANE_PRESS(lane_idx)`, `PAUSE`, `RESTART`, `QUIT`.
- **Test criteria (unit, fake event objects — no real pygame loop):**
  - Each of `LANE_KEYS[i]` produces `LANE_PRESS(i)`.
  - The configured pause key produces `PAUSE`.
  - The configured restart key produces `RESTART`.
  - The configured quit key (or window close event) produces `QUIT`.
  - Unmapped keys produce no event.
  - `KEYUP` events are ignored (we only act on `KEYDOWN`).
  - Multiple events in one batch return all corresponding game events in order.


### [x]  Step 2 — Implement `Renderer`

- Takes a `GameState` snapshot (current state, tiles, score, hit-zone bounds) and renders to a passed-in `Surface`.
- Draws: background, lane dividers, hit zone, tiles colored by state, score text, and state overlays (e.g., "Press SPACE to start", "GAME OVER").
- **Test criteria (UI tests, `SDL_VIDEODRIVER=dummy`):**
  - Empty `GameState` in `MENU` → background filled with the configured color; menu text region is non-background.
  - One falling tile in lane 2 → the pixel column for lane 2 at the tile's y has the tile color; other lanes' columns at the same y have the background color.
  - Tile in `hit` state is rendered in the hit color (different from falling color).
  - Hit zone band is rendered with the configured color across the full window width within `HIT_ZONE_TOP..HIT_ZONE_BOTTOM`.
  - Score text region is non-background when score > 0.
  - `GAME_OVER` state renders the game-over overlay (sample pixels in the overlay region are non-background and differ from the menu overlay).
  - Edge: tile partially off-screen at the top renders only its on-screen part (no exception).
  - Edge: rendering with a very long tile list (e.g., 500 tiles) does not raise and completes within a reasonable budget (smoke check, not a strict perf test).

---

## [x]  Phase 4 — Game orchestrator


### [x]  Step 1 — Implement `Game` orchestrator

- Owns the main loop: poll input → step `update(dt)` → render.
- Wires `InputAdapter`, `StateMachine`, `TileSpawner`, `HitDetector`, `ScoreKeeper`, `Renderer`.
- Supports an injectable clock and an injectable event source so it can run headless.
- **Test criteria:**
  - **Unit:** with a fake clock and a scripted input stream, the orchestrator transitions `MENU --START--> PLAYING` on the start key.
  - **Unit:** during `PLAYING`, a correct lane press inside the hit zone increments the score by exactly the per-hit value.
  - **Unit:** during `PLAYING`, a wrong-lane press transitions to `GAME_OVER`.
  - **Unit:** during `PLAYING`, a tile that falls past the hit zone untouched transitions to `GAME_OVER`.
  - **Unit:** in `GAME_OVER`, pressing restart transitions back to `PLAYING` and resets the score and tiles.
  - **Unit:** pause/resume preserves all tile positions and score across the pause.
  - **UI smoke:** boot the game headlessly, simulate the start key + a precisely timed sequence of lane presses for spawned tiles, run N frames, assert final score and final state.


### [x]  Step 2 — Implement `main.py` entry point

- Initializes pygame, creates a real window, constructs `Game`, runs the loop until quit.
- **Test criteria:**
  - **UI smoke:** invoke the entry point with `SDL_VIDEODRIVER=dummy` and a stubbed event queue that immediately sends `QUIT`; the process exits cleanly with code 0.
  - The entry point does not contain game logic (statically checked: e.g., a test that asserts `main.py` has no `if`/`while` over tile state — easiest is to keep `main.py` minimal, then assert line count is under a small threshold).

---

## [x]  Phase 5 — End-to-end gameplay


### [x]  Step 1 — Full flow: Menu → Playing → GameOver → Restart

- Verify the full loop works in a real window (manual) and in a UI smoke test (automated).
- **Test criteria:**
  - **UI smoke:** scripted run goes Menu → Playing → GameOver → Playing → exits cleanly.
  - **UI smoke:** after restart, score is 0 and there are no leftover tiles from the previous run.
  - Manual check: open a real window, play through one round, restart, quit. (Not gating, but should be done before marking the step.)


### [x]  Step 2 — Lose conditions verified end-to-end

- **Test criteria:**
  - **UI smoke:** with no input, the first spawned tile falls past the zone and the game ends in `GAME_OVER`.
  - **UI smoke:** pressing a lane with no tile in the zone ends the game in `GAME_OVER` on the next frame.

---

## [x]  Phase 6 — Difficulty ramp & polish


### [x]  Step 1 — Difficulty ramp wired through `TileSpawner` and `Tile.speed`

- **Test criteria:**
  - **Unit:** after T seconds of simulated play, the average spawn interval is strictly less than at `t=0`.
  - **Unit:** after T seconds, the tile fall speed is strictly greater than `BASE_FALL_SPEED`, bounded by a configured maximum.
  - **Unit:** ramp is monotonic — interval is non-increasing, speed is non-decreasing, over time.


### [x]  Step 2 — Visual polish pass

- Final color choices, lane dividers, score font/size, menu and game-over overlays.
- **Test criteria:**
  - **UI:** snapshot/pixel-region tests for each game state (`MENU`, `PLAYING`, `GAME_OVER`) — assert key regions have the expected non-background colors.
  - No regressions in earlier UI tests.


### [x]  Step 3 — Final acceptance pass

- **Test criteria:**
  - `pytest` (all markers) is green.
  - `pytest --cov=src/piano_tiles` reports ≥ 90% coverage on `src/piano_tiles/components/` and `src/piano_tiles/models/`; the orchestrator and entry point may be lower but must be exercised at least once.
  - Manual playthrough: at least one full round played in a real window without crashes.

#### Acceptance results

- `pytest` — **287 passed**, 0 failed (all markers).
- `pytest --cov=src/piano_tiles` — **100 % line and 100 % branch** on every module, including all of `src/piano_tiles/components/` and `src/piano_tiles/models/`. The orchestrator (`game.py`) and entry point (`main.py`, via `tests/ui/test_main.py`) are exercised end-to-end.

| Module                                       | Stmts | Branch | Cover |
| -------------------------------------------- | ----: | -----: | ----: |
| `piano_tiles/__init__.py`                    |     0 |      0 |  100% |
| `piano_tiles/config.py`                      |    32 |      0 |  100% |
| `piano_tiles/game.py`                        |   126 |     38 |  100% |
| `piano_tiles/pygame_seams.py`                |    11 |      0 |  100% |
| `piano_tiles/models/__init__.py`             |     0 |      0 |  100% |
| `piano_tiles/models/state.py`                |     8 |      0 |  100% |
| `piano_tiles/models/tile.py`                 |    44 |      8 |  100% |
| `piano_tiles/models/game_state.py`           |    14 |      0 |  100% |
| `piano_tiles/components/__init__.py`         |     0 |      0 |  100% |
| `piano_tiles/components/state_machine.py`    |    28 |      2 |  100% |
| `piano_tiles/components/phase_schedule.py`   |    33 |     10 |  100% |
| `piano_tiles/components/phase_tracker.py`    |    50 |      6 |  100% |
| `piano_tiles/components/spawner.py`          |    37 |     10 |  100% |
| `piano_tiles/components/hit_detector.py`     |    25 |      6 |  100% |
| `piano_tiles/components/score.py`            |    33 |      8 |  100% |
| `piano_tiles/components/input_adapter.py`    |    40 |     14 |  100% |
| `piano_tiles/components/overlay.py`          |    27 |      6 |  100% |
| `piano_tiles/components/renderer.py`         |    65 |     16 |  100% |
| **Total**                                    | **573** | **124** | **100 %** |

- Manual playthrough — `python main.py` boots a real window; one round played end-to-end (Menu → Playing → Phase break → Playing → GameOver → Restart → Quit) without crashes.

---

## [x]  Phase 7 — Background music

Adds a looping music track (`assets/SDITD.ogg`, ~3:29) that plays during gameplay and reacts to state transitions. Reuses the existing seam pattern (`Clock`, `EventSource`): a `MusicPlayer` Protocol lives next to the orchestrator, a real pygame-backed implementation lives in `pygame_seams.py`, and tests inject a scripted fake. Sound effects (per-tile hit sounds, etc.) remain out of scope — this phase is only the background track.

**Spec recap (per user):**
- Music starts when the player presses Space to start a round.
- Music loops indefinitely when the track ends (the file is shorter than a long playthrough).
- On game-over, music **does not stop** — its volume is ducked to `BGM_GAME_OVER_VOLUME` (default `0.3`) so the menu still has ambient music.
- On restart (Space from `GAME_OVER`), volume returns to `1.0` and the track restarts from the beginning.
- Pause/Resume pause/resume the music alongside the game.


### [x]  Step 1 — `MusicPlayer` seam: Protocol + scripted fake

- Declare a `MusicPlayer` Protocol in `piano_tiles/game.py` alongside `Clock` and `EventSource`. Methods:
  - `play(path: str, *, loop: bool = True) -> None`
  - `pause() -> None`
  - `resume() -> None`
  - `stop() -> None`
  - `set_volume(level: float) -> None` (level clamped to `0.0..1.0`)
  - `is_playing` property (`bool`)
  - `volume` property (`float`, starts at `1.0`)
- Add a `ScriptedMusicPlayer` to `tests/scripted.py` that records every call as a `(method, *args)` tuple and maintains correct `is_playing` and `volume` state, so unit tests can assert which transitions trigger which audio actions.
- Add a `SilentMusicPlayer` (a no-op implementation) — used as the default in tests that don't care about audio so the bulk of the existing test suite needs no changes.
- **Test criteria (unit):**
  - `ScriptedMusicPlayer().play("x")` records `("play", "x", True)`, `is_playing` becomes `True`, and `volume` stays at its current value (play does not reset volume).
  - `play(...)` while already playing records the new call and overwrites the active track (no implicit stop required — the contract matches `pygame.mixer.music.play`).
  - `pause()` flips `is_playing` to `False`; `resume()` flips it back to `True`.
  - `stop()` clears `is_playing` regardless of pause state.
  - `set_volume(0.5)` records the call and sets `volume == 0.5`.
  - Edge: `pause()` called twice in a row is idempotent — second call records but `is_playing` stays `False`.
  - Edge: `resume()` when nothing has ever played is a no-op — `is_playing` stays `False`.
  - Edge: `stop()` when nothing is playing is a no-op — no exception, `is_playing` stays `False`.
  - Edge: `set_volume(-0.1)` clamps to `0.0`; `set_volume(1.5)` clamps to `1.0` (test both bounds and at-bound values `0.0` and `1.0`).
  - `SilentMusicPlayer` accepts every call without raising and never reports `is_playing == True`.


### [x]  Step 2 — `PygameMusicPlayer` (production seam)

- Implement `PygameMusicPlayer` in `piano_tiles/pygame_seams.py`, backed by `pygame.mixer.music`.
- `__init__` calls `pygame.mixer.init()` (guarded so a second `__init__` doesn't re-init — check `pygame.mixer.get_init()` first). Document that callers must have called `pygame.init()` first.
- `play(path, *, loop=True)` calls `pygame.mixer.music.load(path)` then `pygame.mixer.music.play(-1 if loop else 0)` (`-1` is pygame's "loop forever" — covers the "loops when the music ends" requirement).
- `set_volume(level)` clamps to `0.0..1.0` and calls `pygame.mixer.music.set_volume(level)`.
- `is_playing` reads `pygame.mixer.music.get_busy()`; `volume` reads `pygame.mixer.music.get_volume()`.
- **Test criteria (UI tests, `SDL_VIDEODRIVER=dummy` + `SDL_AUDIODRIVER=dummy`):**
  - Constructing `PygameMusicPlayer()` after `pygame.init()` does not raise.
  - `play(assets/SDITD.ogg)` does not raise. (Note: `get_busy()` under the dummy audio driver may not reliably flip to `True` — if so, the test asserts no-raise only, not `is_playing`.)
  - `pause()` then `resume()` round-trip without raising.
  - `stop()` does not raise; subsequent `is_playing` is `False`.
  - `set_volume(0.3)` then `volume` returns approximately `0.3` (use `pytest.approx` — pygame stores as float).
  - Edge: `play()` with a path that does not exist raises a clear error (we let `pygame.error` propagate — we do not silently swallow it, because "music is missing" is a real bug we want to surface).
  - Edge: `set_volume(-0.1)` clamps to `0.0`; `set_volume(1.5)` clamps to `1.0`.
  - Edge: constructing two `PygameMusicPlayer` instances in the same test process does not double-initialize the mixer (the second `__init__` is a no-op when `pygame.mixer.get_init()` is already truthy).


### [x]  Step 3 — Wire `MusicPlayer` into `Game`

- `Game.__init__` accepts an injectable `music: MusicPlayer` (default: `SilentMusicPlayer()` so existing tests stay quiet without changes).
- Add to `piano_tiles/config.py`:
  - `BGM_PATH` — absolute path to `assets/SDITD.ogg`, resolved via `Path(__file__).resolve().parent.parent / "assets" / "SDITD.ogg"` so `python main.py` works from any cwd.
  - `BGM_GAME_OVER_VOLUME = 0.3` — the ducked level during `GAME_OVER`.
- State-transition hooks — wired by overriding `Game._fire(event)` to translate each `Event` into music-player calls. The decisions, fixed up-front so the test list maps 1:1:
  - `START` (`MENU → PLAYING`): `music.set_volume(1.0)` then `music.play(BGM_PATH, loop=True)`.
  - `PAUSE` (`PLAYING → PAUSED`): `music.pause()`.
  - `RESUME` (`PAUSED → PLAYING`): `music.resume()`.
  - `WRONG_KEY` (`PLAYING → DYING`): **no music change.** Music keeps playing at full volume during the brief red flash.
  - `DIE` (`PLAYING → GAME_OVER` on a miss, or `DYING → GAME_OVER` when the flash ends): `music.set_volume(BGM_GAME_OVER_VOLUME)`. **Music keeps playing** — we do not call `stop()`.
  - `RESTART` (`GAME_OVER → PLAYING`): `music.set_volume(1.0)` then `music.play(BGM_PATH, loop=True)` — restarts the track from the beginning at full volume.
  - `QUIT` (any state → `QUIT`): `music.stop()` exactly once on shutdown.
  - Phase break entry/exit and banner expiry: no music change (phase transitions don't fire through `_fire`).
- **Test criteria (unit, with `ScriptedMusicPlayer`):**
  - Booting `Game` and idling in `MENU` records zero music calls.
  - First `START` records `set_volume(1.0)` then `play(BGM_PATH, loop=True)` (in that order).
  - `PAUSE` from `PLAYING` records exactly one `pause()`; subsequent `RESUME` records exactly one `resume()`.
  - `DIE` from `PLAYING` (wrong key or missed tile) records exactly one `set_volume(BGM_GAME_OVER_VOLUME)` and **no** `stop()`; player's `is_playing` is still `True` afterwards.
  - During `GAME_OVER`, ticking `update(dt)` does not touch the music — volume stays at `BGM_GAME_OVER_VOLUME`, `is_playing` stays `True`.
  - `RESTART` from `GAME_OVER` records `set_volume(1.0)` then `play(BGM_PATH, loop=True)`. Combined with the previous `set_volume(BGM_GAME_OVER_VOLUME)` from `DIE`, the ordered tail of the call log reads `…, set_volume(0.3), set_volume(1.0), play(...), …`.
  - During an entire `PLAYING` round with no pause/die/quit, the music-call log contains exactly the startup `set_volume(1.0)` + `play(...)` — `update(dt)` ticks do **not** add any calls.
  - Phase-break entry and phase-break exit do **not** touch the music player (regression guard — record the call log around a forced phase break and assert it is unchanged).
  - `QUIT` from any state records exactly one `stop()` and no further calls.
  - Edge: rapid `PAUSE/RESUME/PAUSE/RESUME` records the four calls in order; no extra `play`, `stop`, or `set_volume` is emitted.
  - Edge: `DIE` while a banner is active still calls `set_volume(BGM_GAME_OVER_VOLUME)` (the audio decision is independent of the banner timer).
  - Edge: `RESTART` immediately followed by `DIE` (e.g., player presses Space then a wrong key on the very next frame) records the full sequence `…, set_volume(1.0), play(...), set_volume(0.3)` without any spurious `stop()`.


### [x]  Step 4 — Hook `PygameMusicPlayer` into `main.py` and verify the asset

- `assets/SDITD.ogg` is already in the repo (3.2 MB, ~3:29, Ogg Vorbis).
- `main.py` constructs `PygameMusicPlayer()` after `pygame.init()` and passes it into `Game(..., music=player)`. No game-logic additions in `main.py` (preserves the line-count guard from Phase 4 Step 2 — if the guard threshold is too tight, raise it explicitly with a one-line rationale).
- **Test criteria:**
  - **UI smoke** (extend `tests/ui/test_main.py`): `main.py` with `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` and a stubbed event queue that immediately sends `QUIT` exits cleanly with code 0.
  - Asset file exists: a unit test does `Config.BGM_PATH.exists()` (silent-absent is a real failure mode — better to fail loudly in CI).
  - `BGM_PATH` resolves to the same absolute path whether the test is invoked from the project root or from a subdirectory.
  - Manual playthrough: launch `python main.py`, press Space, confirm music plays; press pause, confirm music pauses; resume, confirm music resumes; trigger a wrong-key death, confirm music drops to ~30% volume but keeps playing; press Space, confirm music restarts from the beginning at full volume; quit, confirm music stops.

---

## [x]  Phase 8 — Main menu, song choices & themes

Adds a boot screen the player lands on before any round: it lists the controls and a set of **clickable song choices**. Picking a song advances to the existing "Press SPACE to start" screen, loads that song's track (Phase 7's music seam), and recolours the whole game in that song's **theme**. This introduces a new `MAIN_MENU` state that sits *before* `MENU` in the flow (`MAIN_MENU --SELECT_SONG--> MENU`), a `Song` catalog, and a per-song `Palette`.

**Spec recap (per user):**
- The boot screen shows the title, the controls, a "Choose a song:" header, and one clickable box per song (`"Title - Artist"`). Slots past the end of the catalog render as empty placeholders.
- Clicking a song selects it, loads its track, and goes to the start screen; clicking empty space does nothing.
- Each song carries its own colour theme: the play-field (background, the hit-zone line, and the two tile bands) plus the three overlay bands (`MENU` / `PAUSED` / `GAME_OVER`). Overlay text stays white, so every song band is dark enough to contrast.
- Current catalog: **Slow Dancing In The Dark — JOJI** (Mint & Blush theme) and **Loose — Daniel Caesar** (Peach Sorbet theme).


### [x]  Step 1 — `MAIN_MENU` boot screen + song-selection flow

- Add a `MAIN_MENU` state as the initial state; the state machine gains `MAIN_MENU --SELECT_SONG--> MENU` and `GAME_OVER --TO_MAIN_MENU--> MAIN_MENU` (return to the picker).
- `main_menu` policy component: `instruction_lines()`, `song_label(song)`, `song_option_box(index)` (the box rectangle), and `song_index_at(pos)` (hit-test a click). The renderer paints; the geometry/policy is pure.
- `Renderer` draws the boot screen: the bokeh photo background, the title, the control lines, the "Choose a song:" header, and `SONG_SLOT_COUNT` boxes — filled + labelled for real songs, empty placeholders beyond the catalog.
- `Game` translates a click on the boot screen into song selection (`_handle_song_click`); a click that misses every box is a silent no-op.
- **Test criteria:**
  - **Unit:** initial state is `MAIN_MENU`; score is 0; no tiles.
  - **Unit:** `song_index_at(pos)` returns the index for a click inside a box and `None` for a miss — boundary cases at a box's edges and in the empty-slot region.
  - **Unit:** clicking a song box transitions `MAIN_MENU → MENU` and records `selected_song`; clicking empty space stays in `MAIN_MENU` with `selected_song is None`.
  - **Unit:** `_handle_song_click(None)` (a click event with no position) is a silent no-op.
  - **UI:** a real song slot is painted in the option color; the first slot past the catalog is painted in the empty-slot color; the title text is near-black against the light photo.


### [x]  Step 2 — Song catalog & per-song tracks

- `Song` dataclass (`title`, `artist`, `path`, `palette`) and a `SONGS` catalog in display order. Adding an entry lays out automatically (up to `SONG_SLOT_COUNT` boxes).
- Selecting a song routes **its own** track to the music seam via `MusicDirector.use_track(song.path)`, so START/RESTART play the chosen song (Phase 7 wiring unchanged otherwise).
- Each catalog track ships as Ogg **Vorbis** under `assets/` (the format `pygame.mixer.music` loads).
- **Test criteria:**
  - **Unit:** `song_label(song)` formats `"Title - Artist"`.
  - **Unit:** choosing the first vs. the second song records the matching title and hands the matching track path to the music player.
  - **Unit:** every `Song.path` is absolute, lives under `assets/`, and points to an existing file.
  - **UI:** the menu renders one labelled box per catalog song plus empty placeholder slots for the remainder.


### [x]  Step 3 — Per-song colour themes (`Palette`)

- `Palette` dataclass: `background`, `hit_zone`, `tile_falling`, `tile_held`, `menu_band`, `paused_band`, `game_over_band`. `DEFAULT_PALETTE` mirrors the classic cyan/magenta constants and is the fallback before any song is picked.
- `GameState` carries the active `palette`; `Game.palette` returns the chosen song's palette (or `DEFAULT_PALETTE`) and stamps it into every snapshot.
- `Renderer` reads the play-field colours from `state.palette`; `overlay_for` reads the band colour from the palette. Overlay text remains white (`OVERLAY_TEXT_COLOR`).
- Theme assignment: Slow Dancing In The Dark → **Mint & Blush**; Loose → **Peach Sorbet**.
- **Test criteria:**
  - **Unit:** every field of every palette is a valid RGB tuple; `DEFAULT_PALETTE` equals the classic colour constants.
  - **Unit:** each song-band colour (`menu_band` / `paused_band` / `game_over_band`) on the song palettes is dark enough for white text (perceived luminance under the contrast bar); the legacy `DEFAULT_PALETTE` is exempt.
  - **Unit:** the songs are themed as specified (Mint & Blush / Peach Sorbet).
  - **Unit:** `Game.palette` is the default before selection, becomes the chosen song's palette after, and the per-frame snapshot carries it.
  - **Unit:** `overlay_for` returns the palette's band colour for each overlay-bearing state; swapping the palette recolours the band but never changes the message.
  - **UI:** rendering `PLAYING` with a non-default palette paints the background, hit-zone line, and tile bands in that palette's colours; each overlay band (`MENU` / `PAUSED` / `GAME_OVER`) paints in the palette's band colour.

#### Acceptance results

- `pytest` (all markers) — **536 passed**, 0 failed.
- `pytest --cov=src/piano_tiles --cov-branch` — **100 % line and 100 % branch** on every module.

| Module                                       | Stmts | Branch | Cover |
| -------------------------------------------- | ----: | -----: | ----: |
| `piano_tiles/config.py`                      |    85 |      0 |  100% |
| `piano_tiles/game.py`                        |   229 |     76 |  100% |
| `piano_tiles/models/game_state.py`           |    16 |      0 |  100% |
| `piano_tiles/components/main_menu.py`        |    18 |      4 |  100% |
| `piano_tiles/components/overlay.py`          |    17 |      2 |  100% |
| `piano_tiles/components/renderer.py`         |   145 |     34 |  100% |
| **Total (all modules)**                      | **999** | **212** | **100 %** |

- Manual check: `python main.py` boots the song picker; clicking each song loads its track and recolours the play-field and overlays in that song's theme.
