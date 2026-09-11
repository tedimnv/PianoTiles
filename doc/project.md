# Piano Tiles — Decisions

Decisions taken on the project. Each entry: what we decided and (briefly) why.

---

## 1. Product requirements

- **Language:** Python 3.11+.
- **Type:** GUI desktop application.
- **Input:** keyboard only (4 keys, one per lane). Default: `D`, `F`, `J`, `K`.
- **Visuals:** colored — lanes, tiles, hit zone, score all rendered with distinct colors.
- **Rules:** standard Piano Tiles:
  - Tiles fall from the top in 4 lanes.
  - Player presses the lane's key as the tile crosses the hit zone.
  - Hit in zone → score up.
  - Tile missed (passes the zone) → game over.
  - Wrong-lane key press when no tile is in that lane's zone → game over.
- **Scope:** implemented end-to-end (menu → play → game over → restart).

## 2. Tech stack

- **GUI / game library:** `pygame` — mature, simple loop, good keyboard input, easy to run headless for tests via `SDL_VIDEODRIVER=dummy`.
- **Test framework:** `pytest`.
- **Test runner / structure:** `pytest` with separate `tests/unit/` and `tests/ui/` directories.
- **Dependencies declared in:** `pyproject.toml` (PEP 621) — runtime under `[project] dependencies`, dev under `[project.optional-dependencies.dev]`. No `requirements.txt`.

## 3. Architecture — component-based

Each component is a plain Python class with a narrow interface. Pure logic is kept free of `pygame` so it can be unit-tested in isolation. `pygame` only appears in the `Renderer`, the `InputAdapter`, and the top-level `Game` orchestrator.

### Components

1. **`StateMachine`** — manages high-level game states.
   - States: `MainMenu` (boot screen — controls + song selection), `Menu` (the post-selection "press SPACE to start" screen), `Playing`, `Paused`, `Dying` (transient wrong-key flash), `GameOver`, `Quit`. The app boots in `MainMenu`.
   - Pure logic, no pygame. Transitions triggered by events (`select_song`, `start`, `pause`, `resume`, `wrong_key`, `die`, `restart`, `to_main_menu`, `quit`). `select_song` moves `MainMenu → Menu`; `to_main_menu` moves `GameOver → MainMenu` (the player pressed M). A plain restart (`GameOver → Playing` via SPACE) does **not** revisit the main menu — only M does.
   - **Testable:** drive transitions in unit tests; assert current state.

2. **`TileSpawner` (the algorithm component)** — decides when and in which lane to spawn tiles.
   - Pure logic. Takes a seeded RNG so tests are deterministic.
   - Takes a `RampConfig` describing the difficulty curve (split out per SRP — see [Refactor notes](#7-refactor-notes)).
   - **Testable:** with a fixed seed, assert the exact sequence of spawns.

3. **`Tile`** — data model. Lane index, vertical position, height, speed, state (`falling`, `hit`, `missed`).
   - Owns its own geometry (`top`, `bottom`, `overlaps_band(top, bottom)`, `is_past(y)`) and its own state transitions (`mark_hit()`, `mark_missed()`, `is_hittable`). Callers tell the tile what happened; they don't reach in and read `state` to decide ("tell, don't ask").
   - **Testable:** advance time, query geometry, assert state transitions.

4. **`HitDetector`** — given a key press, the current tiles, and the hit-zone bounds, decide hit / wrong-key.
   - Pure logic; delegates all per-tile geometry and state checks to `Tile`.
   - Also exposes `mark_misses(tiles, zone_bottom)` to flip tiles that have fallen past the zone.
   - **Testable:** construct tile layouts and assert the verdict for each key press.

5. **`ScoreKeeper`** — score and combo tracking.
   - Pure logic.
   - **Testable:** feed it events, assert score.

6. **`InputAdapter`** — converts raw `pygame` events into game events (`LANE_PRESS(lane_idx)`, `LANE_RELEASE(lane_idx)`, `PAUSE`, `RESTART`, `MENU`, `QUIT`, and `CLICK(pos)` from a mouse-button press).
   - Thin wrapper. Keymap is config-driven. `CLICK` carries the mouse position so the main menu can hit-test it against the song boxes.
   - **Testable:** unit-test the event→event mapping with fake event objects.

7. **`Renderer`** — draws state to a `pygame.Surface`. The only component that touches `pygame.draw`.
   - Takes a `GameState` snapshot (tiles, score, hit zone, current state) and renders it.
   - **Testable:** render to an off-screen surface (SDL dummy driver) and assert pixel regions / non-blackness in expected areas. Also used in UI tests for snapshot comparisons.

8. **`Game` (orchestrator)** — owns the main loop. Wires the components together, runs `update(dt)` and `render()` each frame.
   - Thin glue; logic lives in the components.
   - **Testable:** can run a fixed number of frames headless with a scripted input stream.

9. **`Config`** — constants (lane count, keys, colors, sizes, base speed, difficulty ramp).
   - Plain module/dataclass. Imported by all components.

### File layout

The project uses a **src layout**: `src/` is a plain container directory (not
an importable package); the real package keeps its name, `piano_tiles`, inside
it. `assets/` (music + banner art) stays at the repo root — the package resolves
it relative to the repo root, two levels up from a module. `pyproject.toml`
points the build tool (`tool.setuptools.packages.find.where = ["src"]`) and the
test runner (`tool.pytest.ini_options.pythonpath = ["src", "."]`) at `src/`.

```
assets/                  # at the repo root: music + banner art + menu bg
  star.png
  crown.png
  menu_bg.jpg           # main-menu background photo (scaled to the window)
  SDITD.ogg             # looping background-music track
src/                     # src-layout container — NOT an importable package
  piano_tiles.egg-info/  # editable-install metadata (regenerated by pip install -e .)
  piano_tiles/           # the importable package
    __init__.py
    config.py
    pygame_seams.py      # PygameClock + PygameEventSource + PygameMusicPlayer (concrete seams)
    models/
      __init__.py
      state.py           # State enum (incl. transient DYING)
      tile.py
      game_state.py      # frozen snapshot consumed by Renderer
    components/
      __init__.py
      state_machine.py
      phase_schedule.py  # static difficulty curve
      phase_tracker.py   # runtime position within a PhaseSchedule
      banner.py          # BannerInfo + banner_for + BANNER_TOTAL_SECONDS
      banner_timer.py    # runtime state of the phase-change banner
      dying_flash.py     # runtime state of the wrong-key red flash
      spawner.py
      hit_detector.py
      score.py
      input_adapter.py
      overlay.py         # OverlayInfo + overlay_for — what to show, decoupled from how
      main_menu.py       # boot-screen content + clickable song-box geometry/hit-testing
      renderer.py
    music.py             # MusicPlayer Protocol + SilentMusicPlayer + MusicDirector (event→audio policy)
    game.py              # orchestrator + Clock / EventSource Protocols
main.py
tests/
  __init__.py
  conftest.py
  scripted.py            # shared FakeEvent / keydown / ScriptedClock / ScriptedEvents / ScriptedMusicPlayer
  unit/
    test_state_machine.py
    test_spawner.py
    test_phase_schedule.py
    test_phase_tracker.py
    test_banner.py
    test_banner_timer.py
    test_dying_flash.py
    test_tile.py
    test_hit_detector.py
    test_score.py
    test_input_adapter.py
    test_overlay.py
    test_main_menu.py       # boot-screen content + song-box geometry/hit-testing
    test_game.py
    test_game_music.py
    test_game_state.py
    test_config.py
    test_coverage_config.py
    test_music_player.py    # MusicPlayer seam (Scripted + Silent)
    test_music_director.py  # event→audio policy
  ui/
    test_renderer.py
    test_game_smoke.py
    test_full_flow.py
    test_main.py
    test_pygame_music_player.py
pyproject.toml           # PEP 621 — project metadata, deps, pytest + coverage config
```

## 4. Testing strategy

### Unit tests (`tests/unit/`)
- One file per component. Each component is tested in isolation, no pygame.
- Determinism: `TileSpawner` and anything else using randomness is seeded; time is injected (no real clock).
- Coverage goal: every public method of every component has at least one happy-path test and one edge-case test.

### UI tests (`tests/ui/`)
- Run under `SDL_VIDEODRIVER=dummy` so they don't need a real display (works in CI).
- **`test_renderer.py`:** construct a known `GameState`, render once to an off-screen surface, assert pixels at known coordinates (e.g., a tile in lane 2 produces non-background pixels in that lane's column).
- **`test_game_smoke.py`:** boot the `Game` with a scripted input stream and a fake clock, run N frames, assert the game ends up in the expected state (e.g., correct score, transitions to `GameOver` after a missed tile).

### Infrastructure
- `conftest.py` provides fixtures: seeded RNG, fake clock, headless pygame init, sample `GameState` builders.
- `pytest.ini` configures markers (`unit`, `ui`) and the `SDL_VIDEODRIVER=dummy` env for the `ui` marker.
- Runnable via `pytest`, `pytest -m unit`, `pytest -m ui`.

## 5. Default values (subject to playtesting)

- Window: 480 × 720.
- Lane count: 4. Lane width: 120 px.
- Hit zone: 130 px tall (rows 570–700), anchored near the bottom.
- Keys: `D`, `F`, `J`, `K` for lanes 1–4.
- Tile size: 120 × 180 px.
- Visible gap between same-lane tiles: 1 px (constant across every phase — the spawner derives its interval from the current phase's speed so the gap stays the same).
- Colors: dark blue background, faint lane dividers, magenta hit zone, cyan tiles, green for hit / phase-break overlay, blue menu overlay, yellow paused overlay, red game-over overlay.

### Difficulty phases

The game is divided into discrete numbered phases. Within a phase, speed is constant; speed jumps at phase boundaries. Between two phases the playfield clears and a green countdown popup appears for a short grace period (it fades in over the configured fade-in window) before the next phase starts. After the last phase ends the game stays at its settings indefinitely.

| Phase | Duration | Fall speed | Spawn interval (derived) |
|---|---|---|---|
| 1 | 30 s | 240 px/s | ≈ 0.754 s |
| 2 | 30 s | 290 px/s | ≈ 0.624 s |
| 3 | 30 s | 340 px/s | ≈ 0.532 s |
| 4 | 30 s | 390 px/s | ≈ 0.464 s |
| 5 | 30 s, then loops | 440 px/s | ≈ 0.411 s |

- Phase-break popup duration: **3 s** (countdown 3 → 2 → 1).
- Popup fade-in: **1.5 s** at the start of each break.
- All of the above live in `piano_tiles/config.py` under `PHASES`, `PHASE_BREAK_SECONDS`, and `PHASE_BREAK_FADE_IN_SECONDS`. Edit those constants to retune.

## 6. Out of scope (v1)

- ~~Sound and music.~~ — added later (looping background music; see Phase 7 in the plan).
- ~~Tile variants (long-hold, bomb, bonus).~~ — long-hold tiles added later (press-and-hold; see Pass 5).
- High-score persistence.
- Configurable keybindings UI.
- Per-tile sound effects.

These can come back in a later milestone if we want to extend.

## 6a. Main menu & song selection

The app boots into a **main menu** (`State.MainMenu`) shown ahead of the
"press SPACE to start" screen. It's backed by a light bokeh photo
(`assets/menu_bg.jpg`, scaled to the window) with near-black text, and shows
the control hints (`Play with D F J K`, `Press P to pause`) and a `Choose a
song:` list of song boxes.

- **Layout.** `SONG_SLOT_COUNT` boxes are drawn. Slots backed by a real song
  render in a muted purple (`SONG_OPTION_COLOR`) with a `Title - Artist` label;
  the extra slots are empty grey placeholders (`SONG_EMPTY_SLOT_COLOR`) — drawn
  so the layout is visible, but **not** clickable yet (`song_index_at` only
  returns indices for real songs).

- **Flow.** `MainMenu` → (click a song) → `Menu` ("press SPACE to start") →
  (SPACE) → `Playing`. From `GameOver`, SPACE restarts the same song directly
  (the main menu is **not** shown after every game over); pressing **M** is the
  only way back to `MainMenu` to pick a different song.
- **Input.** Song selection is by **mouse click**. `InputAdapter` turns a
  `MOUSEBUTTONDOWN` into `CLICK(pos)`; the orchestrator hit-tests `pos` against
  the song boxes (`main_menu.song_index_at`). The `M` key maps to a `MENU`
  input event.
- **Song catalog.** `config.SONGS` is a tuple of `Song(title, artist, path)`.
  One entry for now — *Slow Dancing In The Dark — JOJI*, backed by
  `assets/SDITD.ogg`. Adding more entries lays them out and makes them
  clickable automatically.
- **Music wiring.** Choosing a song calls `MusicDirector.use_track(song.path)`,
  so START/RESTART play the selected track. Returning to the menu (`M`,
  `TO_MAIN_MENU`) stops the music; a fresh pick loads its own track.
- **SRP.** `main_menu.py` is a pure module (no pygame) holding the boot-screen
  content and the song-box geometry, shared by the `Renderer` (draws the boxes)
  and the `Game` (hit-tests clicks) so the two never drift — the same
  decision-layer split used by `overlay.py`.

## 7. Refactor notes

### Pass 1 — applied after Phase 2, before starting Phase 3

- **Tell, don't ask.** `Tile` now owns its own predicates and mutators (`is_hittable`, `mark_hit`, `mark_missed`, `overlaps_band`, `is_past`). External callers no longer compare `tile.state` strings or compute geometry from `tile.y` / `tile.height`. The `HitDetector`'s private `_in_zone` helper was removed; geometry lives with the geometry data.
- **SRP — split the difficulty curve from the spawner.** `RampConfig` (frozen dataclass) encapsulates `base_interval` / `min_interval` / `ramp_rate` and computes `interval_at(t)`. `TileSpawner` only knows about spawn timing and tile creation. The two are tested in separate files (`test_ramp_config.py`, `test_spawner.py`).
- **De-dup.** Removed `interval_at` / `current_interval` delegates from `TileSpawner` — ramp queries go through `spawner.ramp` directly.
- **Style.** Sectioned `config.py` with grouping comments (lanes / geometry / timing / colors). Error messages have a consistent shape across components (`<thing> must be <bound>, got <value>`).
- **Outcome.** All 122 tests still pass; 100% line and 100% branch coverage across every component.

### Pass 2 — applied after Phase 3, before starting Phase 4

- **Layering — move `State` enum into the models layer.** `State` was previously defined inside `components/state_machine.py`, which meant `models/game_state.py` (the renderer's snapshot input) had to reach *up* into `components/` to import it. Wrong direction: models should not depend on components. `State` now lives in `piano_tiles/models/state.py`; `StateMachine`, `GameState`, and `Renderer` all import it from there. `state_machine.py` no longer owns the type — only the transitions and the runtime behavior.
- **Tell, don't ask — kill the last string-state comparison.** `Renderer._tile_color` was branching on `tile.state == "hit"` / `"missed"`. Added `Tile.is_hit` and `Tile.is_missed` (matching the existing `is_hittable` pattern); the renderer now asks the tile, not its raw state string. No production code outside `Tile` reads `tile.state` directly anymore.
- **Style.** Re-shaped `_key_code`'s error to match the project's `<thing> must be <bound>, got <value>` convention. Widened `InputAdapter.translate`'s parameter type from `list` to `Iterable[Any]` so callers can pass tuples or generators; added a test confirming both work. Replaced `field(default_factory=tuple)` with the literal `= ()` on `GameState.tiles` — tuples are immutable, the factory was ceremony.
- **Files reorganized.** `piano_tiles/models/state.py` (new), shared by `state_machine.py` and `game_state.py`.
- **Outcome.** All tests still pass; 100% line and 100% branch coverage across every component.

### Pass 5 — applied after the long-tile (press-and-hold) feature

- **Coverage outcome.** 368 tests passing, 100 % line and 100 % branch coverage across every module — the same bar as the previous passes, despite the substantial feature work.
- **Feature shape (briefly).** Consecutive same-lane spawns are merged into one continuous tile at spawn time, and the player presses + **holds** the lane key for the whole long tile. Short tiles still tap to hit; long tiles enter a held state on press, auto-complete (and score `segments` points) when the tile's top fully clears the hit zone, and trigger DIE if released before that. Held tiles render in `TILE_HELD_COLOR` so the press is visible.
- **Where the new logic lives.**
  - **`Tile` (model)** gained `segments`, `held`, `is_long`, `mark_held()` / `mark_released()`, and `extend_with(other, gap)`. The merge geometry is encapsulated on the tile itself, so `Game` doesn't reach into its fields. `mark_hit` / `mark_missed` also clear `held` for visual sanity.
  - **`Game._merge_into_previous`** walks back the active list to find the most-recent same-lane tile and extends it via `extend_with` when the spawn cadence put the new tile exactly `TILE_VISUAL_GAP_PX` above it. A speed-mismatch (phase boundary) or a non-hittable existing tile aborts the merge.
  - **`Game._tick_playing`** keeps its 6-line shape; a new `_complete_held_tiles` helper sits between spawn and miss-check and pulls held tiles that have fully cleared the zone. Both `_complete_held_tiles` and `_handle_lane_release` route through a shared `_complete_long_tile(tile)` so the score-and-remove logic exists in exactly one place.
  - **`InputAdapter`** now emits `LANE_RELEASE` on KEYUP for the lane keys. Control keys (pause / restart / quit) remain KEYDOWN-only.
  - **`Renderer._tile_color`** branches on `tile.held` before falling through to the regular colour — one branch, one decision point.
- **Tell, don't ask.**
  - The merge contract is `existing.extend_with(other, gap=GAP)` — Game tells the tile to absorb the other; the tile knows how to combine geometry and segment counts.
  - `_find_held_tile(lane)` lets Game ask the field "is anything held in this lane?" without scattering `tile.held` checks across the orchestrator.

### Pass 4 — applied after the Phase 6 feature work, before locking the game

- **SRP — extract `BannerTimer` from `Game`.** The phase-change banner's runtime state was sprawled across `Game` as `_banner_phase` + `_banner_elapsed` + `_advance_banner`, plus inline `is_active` checks (`if self._banner_phase is None`). Pulled all of it into `piano_tiles/components/banner_timer.py`. The timer exposes `is_active`, `phase_number`, `elapsed` and accepts `start(...) / tick(dt) / clear()`. `banner.py` (the rendering policy) stays separate, so "what the banner looks like" and "is one playing now" live in distinct modules — the same split we already have between `phase_schedule.py` and `phase_tracker.py`.
- **SRP — extract `DyingFlash` from `Game`.** Same shape for the wrong-key red flash: `_dying_phantom` + `_dying_elapsed` + the body of `_tick_dying` moved into `piano_tiles/components/dying_flash.py`. `tick(dt)` returns `True` iff the flash just ended; the orchestrator fires `DIE` and otherwise stays out of it.
- **SRP — split `Game._tick_playing` into a sequence of single-responsibility helpers.** What used to be one 23-line method with five responsibilities now reads as a five-line story: `_sync_phase` / `_update_falling_tiles` / `_spawn_new_tiles` / `_handle_misses` / `_cull_offscreen_tiles`. Each helper does one thing and the spawn-pause-during-banner guard now lives inside `_spawn_new_tiles` where it belongs.
- **Tell, don't ask.** `Game` stops asking `if self._banner_phase is None` and instead asks `if self._banner.is_active` — the timer owns the predicate. The phantom-Y calculation lifted out of `_begin_dying` into `_make_phantom` (which delegates to a tiny module-level `_hit_zone_center_y` helper, so the "no target" fallback is named and tested through its consumer).
- **De-dup — `_snapshot()` extracted from `_render`.** The seven-field `GameState` construction was inline in the render path. Pulled it into its own method so future snapshot additions land in one place.
- **Files reorganised.** New: `piano_tiles/components/banner_timer.py`, `piano_tiles/components/dying_flash.py`, `tests/unit/test_banner_timer.py`, `tests/unit/test_dying_flash.py`.
- **Outcome.** 339 tests passing (up from 319 after the new collaborator tests); 100 % line and 100 % branch coverage across every module, including the two new ones.

### Pass 3 — applied during Phase 6, before the final acceptance step

- **SRP — extract `PhaseTracker` from `Game`.** Phase progression was sprawled across `Game` as three scalar fields (`_phase_index`, `_phase_elapsed`, `_break_remaining`), a predicate method (`_should_begin_phase_break`), two lifecycle methods (`_begin_phase_break`, `_end_phase_break`), and an inline `break_elapsed` conditional in `_render`. Pulled all of it into `piano_tiles/components/phase_tracker.py`. `Game._tick_playing` and `_tick_phase_break` now read as two-line state machines (`advance_*` returns whether to transition); `_render` reads tracker properties instead of recomputing them. Reduced `game.py` from 255 → ~190 lines.
- **SRP — move the pygame-backed seams out of `game.py`.** `PygameClock` and `PygameEventSource` were sitting in the orchestrator module. They have nothing to do with the orchestrator; they're production wiring for the `Clock`/`EventSource` Protocols. Moved them to `piano_tiles/pygame_seams.py`. `main.py` and `test_game_smoke.py` import from the new location; the Protocols stay with their consumer (`Game`).
- **SRP — extract overlay decisions from `Renderer`.** Two module-level helpers (`_overlay_for`, `_overlay_alpha`) in `renderer.py` were deciding which color/text/alpha to show; the renderer was reading them and turning them into pixels. Pulled the decisions into `piano_tiles/components/overlay.py` behind a single `overlay_for(state) -> OverlayInfo | None`. Renderer now does one thing — paint whatever it's handed; adding a new overlay variant means touching `overlay.py`, not `renderer.py`.
- **Tell, don't ask — `_render` stops assembling break snapshot fields.** Previously `Game._render` asked `self.state is State.PHASE_BREAK`, then read private `_break_remaining`, then computed `break_elapsed = self._phases.break_seconds - self._break_remaining if in_break and ... else None`. Now it just reads `self._phases.break_remaining`, `.break_elapsed`, `.next_phase_number` — the tracker decides; Game packages and ships.
- **Style — drop the misleading underscore on `key_code`.** Five test modules and two production modules were importing `_key_code` from `input_adapter`. A name that's imported from five other modules isn't private. Renamed to `key_code`.
- **De-dup — consolidate scripted seams.** `FakeEvent` / `keydown` / `ScriptedClock` / `ScriptedEvents` were copy-pasted across `test_game.py`, `test_full_flow.py`, and `test_game_smoke.py`. Extracted to `tests/scripted.py`; the three test files import from there.
- **Files reorganized.** New: `piano_tiles/pygame_seams.py`, `piano_tiles/components/phase_tracker.py`, `piano_tiles/components/overlay.py`, `tests/scripted.py`, `tests/unit/test_phase_tracker.py`, `tests/unit/test_overlay.py`. The two `_overlay_alpha`-via-`GameState` tests moved from `test_renderer.py` into `test_overlay.py` and now test the decision layer directly.
- **Outcome.** 287 tests passing (up from 261 after the new collaborator tests); 100% line and 100% branch coverage across every module, including the new ones.

### Pass 6 — applied to the background-music and long-tile (press-and-hold) code

- **SRP / split the longest file — new `piano_tiles/music.py`.** The music seam was scattered through `game.py`: the `MusicPlayer` Protocol, the `SilentMusicPlayer` default, and `Game._react_music_to` (the event→audio policy) all lived in the orchestrator, the project's biggest module. Pulled all three into a dedicated `music.py`. The orchestrator no longer owns any audio decisions — it just hands each fired `Event` to a collaborator. The `MusicPlayer` Protocol moved with its implementation and policy because music now has a cohesive home of its own (the same reason `Verdict` lives in `hit_detector` and `Event` in `state_machine`); `Clock` and `EventSource` stay in `game.py` as they have no dedicated module. `pygame_seams.PygameMusicPlayer` is unchanged — it satisfies the Protocol structurally.
- **SRP — extract `MusicDirector` from `Game`.** The event→audio mapping is its own responsibility (audio *policy*) distinct from the `MusicPlayer` (audio *mechanism*). `MusicDirector` wraps a player and exposes `react_to(event)`; `Game._fire` shrank to `state_machine.process(event)` + `music.react_to(event)`. The director takes its track path and duck level as constructor args (defaulting to config) so the policy is unit-testable in isolation (`test_music_director.py`).
- **Reduce cyclomatic complexity — data-driven dispatch.** `_react_music_to`'s five-branch `if/elif` chain became an `Event → action` table in `MusicDirector`, mirroring `StateMachine`'s own transition table. `react_to` is now a single dict lookup; events absent from the table (`WRONG_KEY`, phase transitions) leave the music untouched by construction rather than by a fall-through `else`.
- **Tell, don't ask — `Tile.fill_overlay()`.** `Game` was reaching into a tile to paint a hit short tile green (`tile.held_amount = tile.original_height`). The tile now owns that with `fill_overlay()`; the orchestrator tells it to fill, and the geometry stays on the geometry data.
- **De-dup — shared `Game._complete_long_tile`.** The "bank the earned segments, then take the tile out of play" pair was duplicated in `_handle_lane_release` (pro-rated) and `_complete_held_tiles` (full). Both now route through `_complete_long_tile(tile)`, which awards `tile.segments_held(gap)` then marks it hit — a fully-held tile's `segments_held` already returns every segment, so the special case collapses into the shared path. (This restores the single-source-of-truth shape the Pass 5 note described.)
- **Reduce complexity — split `_merge_into_previous`.** The three inline guard-returns became a named predicate `_continues_run(existing, new_tile)` plus a `_most_recent_in_lane(lane)` lookup. The merge method now reads as find → check → extend, and the "what makes a run continuous" rule is testable on its own.
- **Style.** Trimmed the oversized inline comments on the long-tile press/release/merge methods; the rationale they carried now lives on the `Tile` methods they call.
- **Files reorganized.** New: `piano_tiles/music.py`, `tests/unit/test_music_director.py`. `tests/unit/test_music_player.py` now imports `SilentMusicPlayer` from `piano_tiles.music`.
- **Outcome.** 474 tests passing (up from 464 after the new `MusicDirector` / `fill_overlay` tests); 100% line and 100% branch coverage across every module, including `music.py`.
