# AI-Traffic-Brain — Second Walkthrough (Post-Fix Audit)

This is a re-review against the previous `REVIEW.md`. For each item I flagged before, I checked whether the change actually landed in the working tree.

---

## CRITICAL REGRESSION: half your Python files are truncated

Five files are syntactically broken right now. Python can't parse any of them. The CLI and the live-map page will fail on import:

| File | Line | Error |
|---|---|---|
| `main.py` | 622 | `'(' was never closed` — file ends mid-call inside `run_rl_pretrain(` |
| `core/camera_detector.py` | 504 | unterminated triple-quoted string — `_is_emergency` docstring cut off |
| `core/fixed_controller.py` | 144 | `IndentationError: expected an indented block` — `_advance_phase` body missing |
| `core/rl_controller.py` | 989 | unterminated string literal — `_save_qtable` cut off in mid-message |
| `core/vision_bridge.py` | 440 | unterminated triple-quoted string — `_locate_emergency_axis` docstring cut off |
| `dashboard/pages/live_map.py` | 219 | unterminated triple-quoted string — HTML f-string never closed |

This is the immediate blocker — the project does not run at all in this state. `python -m py_compile main.py` fails on the parse step before any logic executes.

Looking at file ends:
```python
# main.py last line
        run_rl_pretrain(
            pretrain_       # ← cut off mid-token

# core/fixed_controller.py last line
    def _advance_phase(self) -> None:
                                       # ← function declared but never bodied

# core/rl_controller.py last line
            logger.error("Q-table atomic replace failed (%s) — "
                         "temp left at %s.   # ← string never closed, no )
```

This pattern (every truncated file ends in the middle of the same area) suggests a save / sync / encoding step lost trailing content across multiple files in one batch. Possible causes: a partial save from an editor, a `git checkout` that hit a bad encoding, an antivirus mid-write quarantine, or a OneDrive / Dropbox sync conflict. Most likely: when Windows tools rewrote the files with CRLF, something stopped writing partway through each file.

**Fix path:**
1. Restore the files from git: `git checkout -- main.py core/camera_detector.py core/fixed_controller.py core/rl_controller.py core/vision_bridge.py dashboard/pages/live_map.py`. That gives you back the previous good content but loses your fixes.
2. Then re-apply the small content changes you intended (yellow=3, RL seed varies per ep, hybrid qtable warning, vision yellow insertion, camera fallback fix). Commit these as separate small commits so a future regression is easy to revert.
3. Add a pre-commit hook that runs `python -m compileall -q core/ dashboard/ main.py` and rejects commits with syntax errors. Three-line script, prevents this from happening again.

Until the truncation is reversed, none of the fixes below are running in production — they're sitting in broken files.

---

## Line-ending churn is masking what actually changed

`git diff` against the committed version shows essentially every file has been rewritten end-to-end. The reason isn't real edits — it's a CRLF/LF mismatch:

```
.gitignore                       — CRLF, 0 real lines changed (pure CRLF noise)
README.md                        — 0 real lines changed
simulation/intersection.net.xml  — 0 real lines changed
dashboard/map_view.py            — 0 real lines changed
```

I.e. these four files report as "modified" in `git status` but their content is byte-identical to the committed version once you ignore CR. **Effect:** the README still says "30 s / 5 s yellow" even though the controller is now 30 / 3, because the README never actually got edited.

**Fix:**
- Add `.gitattributes` with `* text=auto eol=lf` (Linux-style) or `eol=crlf` (Windows). Pick one and commit it.
- Run `git add --renormalize .` once. From then on Git stores LF and your editor sees CRLF, with no diff noise.
- Without this, every commit you make will look like 1500 lines changed even when 3 lines changed.

---

## Item-by-item: what's fixed, what's not

### 1. Untracked `dashboard/intersection_diagram.py` — **PARTIALLY FIXED**
- `git status` now shows `AM dashboard/intersection_diagram.py` (added to index, modified after).
- It's staged but not committed. After your next commit it'll be in the repo. Good.
- The file itself parses cleanly.

### 2. `.claude/` markdown escapes — **PARTIALLY FIXED**
- All 8 `.claude/skills/*/SKILL.md` files are now clean (proper `---` frontmatter, real headings, real bullets). Skills are now loadable.
- Still escaped: `.claude/CLAUDE.md` (still `\#`, `\##`, `\-`, `1\.`).
- Still escaped: `.claude/agents/safety-reviewer.md`.
- `.claude/skills/spec-feature/SKILL.md` declares `name: eval-model` — *still* the wrong slug.
- `.claude/skills/eval-model/` and `.claude/skills/deployment-readinessd/` are still empty-and-junk directories.

### 3. RL per-episode seed — **FIXED**
Both `train` (line 714–717) and `pretrain_from_smart` (line 629–632) now do:
```python
base_seed = self.env.seed
for ep in range(1, episodes + 1):
    self.env.seed = base_seed + ep - 1
    self.env.start()
```
Each episode now sees a different SUMO seed, so the agent isn't memorising one trajectory anymore. This is the most important fix from the previous review.

Two follow-ups still apply:
- `__import__("time").perf_counter()` at lines 716 and 743 should just be `import time` at the top of the file. Not a bug, just clutter.
- The fix is applied in `pretrain_from_smart` too — but pretraining is *imitation* of Smart's actions, and Smart is deterministic given an env state. Varying the seed across pretrain episodes is fine and helps cover more states.

### 4. Yellow-duration alignment — **PARTIALLY FIXED**
- `core/fixed_controller.py` PHASES now uses `duration=3.0` for yellows. ✓
- `core/smart_controller.py` already had `YELLOW_DURATION = 3.0`. ✓
- `simulation/intersection.net.xml` has `phase duration="3"` for yellows. ✓
- All three yellow durations match at 3 s. The safety-critical part of the bug is resolved.

But:
- README still says "Fixed (30 s / **5 s** cycle)" — line 18 and line 28. **Documentation is now wrong.** Update.
- `CYCLE_LENGTH = sum(p.duration for p in PHASES)` evaluates to **66 s** but the inline comment still says `# 70 s`. Stale.
- The green-duration mismatch (controller commands 30 s, network XML says 42 s) is still present in the network XML. In practice it's harmless because `setPhase()` resets SUMO's clock, but the network XML is now misleading documentation. Either rebuild the `.net.xml` from `.tll.xml` with 30 s greens, or accept that the network's static program is unused and document that.

### 5. Camera detector phantom-emergency fallback — **FIXED**
`core/camera_detector.py` line 480 now uses `result[f"fallback_emg_{lane_id}"] = "car"` — synthetic vehicle ID does not start with `"ems"`, and type is "car" not "emergency". `_is_emergency` returns False for these. Confirmed.

But:
- The block comment at line 471 still says *"ID is prefixed with 'ems_' so it passes the strict _is_emergency() check."* — that's the old behaviour, contradicts the actual code now. Update.
- The `_is_emergency` docstring at line 507 still mentions *"the fallback simulator uses ems_sim_<lane_id>"* — also stale.
- The detector still uses module-level `random.uniform` / `random.random` with no seed. Confidence and bbox jitter still vary between identical runs. Not fixed.

### 6. Vision-bridge no-yellow jump — **NOT ACTUALLY FIXED (looks fixed, isn't)**
`_start_override` now contains:
```python
if current_phase in _GREEN_PHASES and current_phase != target_green:
    yellow = (...)
    self.env.set_phase_at(tl_id, yellow)        # line 363
# ...
self.env.set_phase_at(tl_id, target_green)      # line 369
```

Both `set_phase_at` calls happen in the **same Python tick before the next `env.step()`**. SUMO will receive two phase commands back-to-back; only the last one (target green) takes effect when the simulation advances. So the yellow phase is held for **0 simulation seconds**. Vehicles still see an instant green→opposite-green flip, just the same as before. The fix changes the code but not the behaviour.

To actually insert a 3 s yellow on emergency override you need a state machine:
- New override state: `YELLOW_PENDING`
- On trigger: set yellow phase, set `_override_target_phase[tl_id] = target_green`, set `_override_yellow_started[tl_id] = sim_time`.
- In `_enforce_active_overrides`: if `(sim_time - yellow_started) < YELLOW_DURATION`, hold yellow; once elapsed, set target green and switch state to `GREEN_HOLD`.

The docstring at line 343–351 also still says *"Yellow transitions are bypassed intentionally — emergency clearance takes priority over the normal inter-green gap."* — that contradicts the code that ostensibly inserts a yellow. Decide which is correct, then make code and docstring agree.

### 7. CLI: `--episodes` semantics — **FIXED**
`main.py` `if __name__ == "__main__":` block now passes `episodes=args.episodes` for all non-rl-train/rl-pretrain modes. The previous `ep = args.episodes if args.mode == "hybrid" else 1` is gone. So `python main.py --mode smart --episodes 5` now actually runs 5 episodes.

But the default is still `100` — and for non-training inference modes, the typical user wants 1. Default should be `default=1` with a note that benchmarking studies should use ≥10. Right now `python main.py --mode fixed` with no args runs for ~50 minutes of wall-clock.

(Also: this fix lives in the truncated `main.py`, so it doesn't actually run until you restore the file.)

### 8. Hybrid mode requires `--qtable` — **PARTIALLY FIXED**
`run()` now warns when `data/qtable.pkl` doesn't exist for hybrid mode (lines 385–391). It's a `logger.warning`, not a `FileNotFoundError`. The hybrid run continues with an empty Q-table and produces a Smart-only run mislabelled as hybrid. Better than silent, but still wrong-labelled output. Make it a hard error or rename the output CSV to `results_smart_no_rl.csv` when the Q-table is missing.

`rl` mode (line 393–395) has no check at all. Still silently runs with empty Q-table.

### 9. Tests, training_log, evaluation_log — **NOT DONE**
- No `tests/` directory.
- No `data/training_log.csv` written by `train()`.
- No `evaluate()` method on RLController.
- No `docs/` directory (README image links still broken).
- No `pyproject.toml`.
- No CI workflow.

These were on the previous review's "priority order" list; none have been started.

### 10. Smart controller — **NOT TOUCHED**
- `_advance_reason` lines 383, 387 still compare `ew_p` (0–2) to `effective_max` (60–90 seconds). Dead branch. Not fixed.
- `_advance_reason` line 385 still has `ew_p >= SWITCH_RATIO` (single value vs ratio). Wrong. Not fixed.
- `_MaxTracker.max_count` and `.max_wait` still grow forever and never reset. Not fixed.
- `_emit_coordination` still overwrites wave hints rather than combining. Not fixed.

### 11. Stray junk files — **NOT REMOVED**
- `0.05`, `0.66`, `python` — still on disk (gitignored, but cluttering).
- `oracleJdk-26/` — still 373 MB in the working folder.

### 12. RL reward docstring vs code — **NOT FIXED**
Docstring (line 56) still says *"Normalised by dividing by 1000 → range roughly -100 … +100 per step"*; code (line 365) still does `reward /= 100.0`. Off by a factor of 10.

The reward docstring also still omits `W_QUEUE_PENALTY` and `W_SWITCH_PENALTY` from its term list.

### 13. SUMO config — **NOT TOUCHED**
- `device.rerouting.adaptation-steps` / `adaptation-interval` are still set without `--device.rerouting.probability` — flags are still dead.
- `--ignore-route-errors true` still hides bugs.
- `--time-to-teleport 300` still masks deadlocks.

### 14. Routes file — **NOT TOUCHED**
- `pedestrian_proxy` still travels on roads as a slow vehicle, blocks lanes.
- Still 3 accidents (2 in morning, 1 in evening).
- `ems_06` → `ems_07` interval (240 s) is still shorter than the override cooldown (300 s) — same-axis emergencies in succession still get suppressed.

### 15. Stale CSVs — **NOT TOUCHED**
`data/results_*.csv` are still from different dates (April 16 to April 27). Cross-controller comparisons across different commits remain unfair.

---

## Summary

| Area | Previous severity | Status |
|---|---|---|
| **Truncated source files** | (new) | **CRIT — files don't parse** |
| Line-ending churn | (new) | high — repo diff is unreviewable |
| RL per-episode seed | CRIT | fixed |
| Yellow duration alignment | CRIT | fixed in code; README docs stale |
| Camera fallback emergency | CRIT | fixed in code; comments stale |
| Vision-bridge yellow on override | CRIT | code edited, **behaviour unchanged** |
| `dashboard/intersection_diagram.py` untracked | CRIT | staged, not committed yet |
| `.claude/` markdown escapes | CRIT | skills fixed; CLAUDE.md and agent still escaped |
| `--qtable` missing for hybrid | CRIT | warns, doesn't error |
| `--episodes` semantics | BUG | fixed; default still 100 |
| Smart `_advance_reason` bugs | BUG | not touched |
| Smart running-max never resets | BUG | not touched |
| Reward docstring vs code | DOC | not touched |
| Tests / training_log / docs | ADD | not touched |
| Stray files / oracleJdk | NIT | not touched |
| README outdated table | DOC | now actively wrong (says 5 s yellow) |

---

## Priority order — what to do now

1. **Restore the truncated files immediately.** Without this, nothing else matters because nothing runs:
   ```bash
   git checkout -- main.py core/camera_detector.py core/fixed_controller.py \
                   core/rl_controller.py core/vision_bridge.py \
                   dashboard/pages/live_map.py
   ```
   Then re-apply the seed fix, the yellow=3 change, the camera fallback fix, the hybrid warning, and the `--episodes` change. They're small enough to redo from memory or from this review.

2. **Add a pre-commit hook** so this can't happen again:
   ```bash
   # .git/hooks/pre-commit
   #!/usr/bin/env bash
   python -m compileall -q core/ dashboard/ main.py || exit 1
   ```

3. **Add `.gitattributes`** with `* text=auto eol=crlf` (Windows host) and run `git add --renormalize .`. Future diffs will be readable.

4. **Fix the vision-bridge yellow properly** with a state machine — the current change is a placebo.

5. **Fix `.claude/CLAUDE.md` and `.claude/agents/safety-reviewer.md`** — same backslash-strip you did for the skill files.

6. **Update README.md** to reflect the actual current yellow duration (3 s, not 5 s) and re-run the controller benchmarks on the same git SHA so the table isn't comparing pre-fix to post-fix runs.

7. **Then resume the previous priority list** — tests, training_log, smart controller bugs, etc.
