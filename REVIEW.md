# AI-Traffic-Brain — Full Project Review

A file-by-file pass over every non-vendored file in the repo. Each section lists what's there, what's broken or sloppy, and what to add or change. Severity tags: **[CRIT]** = breaks something or hides bugs, **[BUG]** = wrong behaviour, **[DOC]** = misleading/outdated docs, **[REFACTOR]** = code health, **[ADD]** = missing thing, **[NIT]** = polish.

---

## 0. Top-level repo hygiene

### Stray files in working tree (gitignored, but still on disk)
- `0.05` (0 bytes), `0.66` (0 bytes), `python` (0 bytes) — accidental shell redirections (`> python` instead of running it). **[NIT]** Delete with `rm 0.05 0.66 python`.
- `oracleJdk-26/` — 373 MB JDK extracted into the project root. Not in git, but bloats your filesystem and confuses anyone browsing the folder. **[NIT]** Move outside the repo (e.g. `C:\Java\jdk-26`) and set `JAVA_HOME` to point there.

### Missing files
- **[ADD]** `pyproject.toml` — project metadata, Python version pin, optional dev dependencies, formatters, mypy config.
- **[ADD]** `tests/` — there are zero tests in the entire repo. For a project whose CLAUDE.md says "Safety first", that's the biggest single gap.
- **[ADD]** `docs/screenshots/dashboard.png` and `docs/screenshots/live_map.png` — referenced by README but the `docs/` folder doesn't exist. The README image links are broken on GitHub.
- **[ADD]** `LICENSE` — README badges claim "Academic" license but no LICENSE file. Pick one (MIT for academic code is common) and commit it.
- **[ADD]** `CHANGELOG.md` — the rl_controller.py docstring already mentions v3/v5/v6 state encodings; tracking those externally helps reviewers.
- **[ADD]** `CONTRIBUTING.md` and a CI config (`.github/workflows/ci.yml`) — at minimum run `python -m py_compile` on every push and `python main.py --mode fixed --episodes 1` as a smoke test.

### Untracked file that should be committed
- `dashboard/intersection_diagram.py` — imported by `dashboard/app.py` line 18, but **not in git**. Anyone who clones the repo and runs the dashboard gets `ImportError`. **[CRIT]** `git add dashboard/intersection_diagram.py`.

### `.gitignore`
The file works (the JDK and stray files aren't tracked), but it's messy: rules are duplicated (`*.pkl` appears twice, `__pycache__/` appears twice, `.env` AND `.env.*`, etc.). It also ignores `.claude/` entirely — meaning you're not version-controlling your own custom skills. That's a choice, but if you want others to use them, drop the `.claude/` line and ignore only `.claude/cache/` or similar. **[REFACTOR]** Deduplicate; decide policy on `.claude/`.

### `requirements.txt`
- All dependencies use `>=` floors with no upper bounds. A future breaking release of `streamlit` or `traci` will silently break the project. **[REFACTOR]** Use `package==X.Y.Z` for top-level pins and let pip resolve the rest, or use `uv`/`poetry`.
- Missing dev dependencies: `pytest`, `pytest-cov`, `ruff` or `black`, `mypy`. Put them in a `[project.optional-dependencies]` block once you adopt `pyproject.toml`.
- Missing runtime deps: `pandas` is implicitly required by streamlit/plotly internals; `matplotlib` is *not* in the file but is commonly added when plotting RL curves later. Decide.
- Missing: a comment block warning that `traci`/`sumolib` Python packages won't work without SUMO itself installed and `SUMO_HOME` set.

### `skills-lock.json`
Contains hashes for `frontend-design` and `supabase-postgres-best-practices` — neither is used in this codebase. **[NIT]** Either remove (and drop `.agents/skills/`) or document why they're here.

---

## 1. `.claude/` — Claude Code config

### **[CRIT] Every `.md` file in `.claude/` has its Markdown ESCAPED.**
Every heading marker, list bullet, frontmatter delimiter, and numbered-list dot is prefixed with a literal backslash. Example from `.claude/skills/rl-diagnosis/SKILL.md`:

```
\---
name: rl-diagnosis
\---
```

The `\---` should be `---`. The same problem affects:
- `.claude/CLAUDE.md`
- `.claude/agents/safety-reviewer.md`
- `.claude/skills/controller-comparison/SKILL.md`
- `.claude/skills/deployment-readiness/SKILL.md`
- `.claude/skills/env-debug/SKILL.md`
- `.claude/skills/map-codebase/SKILL.md`
- `.claude/skills/review-traffic-logic/SKILL.md`
- `.claude/skills/rl-diagnosis/SKILL.md`
- `.claude/skills/simulation-vs-reality/SKILL.md`
- `.claude/skills/spec-feature/SKILL.md`

**Effect:** Claude Code's skill loader reads YAML frontmatter delimited by `---`. With `\---`, the frontmatter is unreadable, so none of these skills are auto-discoverable. The body also renders as plain text with literal `#`, `-`, and `1\.` characters instead of headings/lists.

**Fix:** Open each file and remove every leading `\` that escapes a Markdown character. Or run a one-liner: `sed -i 's/^\\-/-/g; s/^\\#/#/g; s/^\\\([0-9]\)\\\./\1./g'` on each file (test on a copy first). Do this on a Linux mount or Git Bash; Windows PowerShell needs a different syntax.

### **[BUG]** `.claude/skills/spec-feature/SKILL.md` declares `name: eval-model`
The directory is `spec-feature/` but the skill name field says `eval-model`. Either rename the directory or fix the name field. Pick one purpose for this skill — right now its body talks about evaluating models, which contradicts the directory name.

### **[CRIT]** Empty / typo skill directories
- `.claude/skills/eval-model/` — empty directory, no `SKILL.md`. Probably the original target for `spec-feature/`. Delete.
- `.claude/skills/deployment-readinessd/` — typo of `deployment-readiness`. Empty. Delete.

### **[REFACTOR]** Skills are too thin to be useful
Every skill is 5–15 lines: a title and a bullet list. They tell Claude *what topic* to think about but not *how to think about it*. Compare this to a useful skill (e.g. anthropic-skills/pdf), which explains exactly which scripts to run, which fallbacks exist, and what the common failure modes are.

For example, `rl-diagnosis/SKILL.md` should say things like:
- "First read `core/rl_controller.py` for `_encode_state`, `_compute_reward`, `pretrain_from_smart`, `train`."
- "Check that `random.seed` is varied across episodes. Currently it isn't — that's a known bug."
- "Before claiming RL improved, plot episode_reward across training episodes from `data/training_log.csv`."

A skill that just lists "Inspect: state encoding, action space, reward function" doesn't teach Claude anything new; the skill should encode *project-specific* context that's hard to derive from the code.

### `.claude/CLAUDE.md`
Same backslash-escape problem. Even after fixing it, the content is too thin:

```
## Rules
- Safety first
- Explain before coding
- Small changes only
- Clean architecture
```

These are slogans, not actionable rules. Replace with concrete, project-specific constraints, e.g.:
- Never modify `simulation/intersection.net.xml` directly — regenerate from `.nod.xml`/`.edg.xml`/`.con.xml` via `netconvert`.
- Always run `python main.py --mode fixed --episodes 1` after touching any controller — it's a 30-second smoke test.
- Yellow duration must match between `core/fixed_controller.py` and `simulation/intersection.net.xml`.
- Q-table is at `data/qtable.pkl` and is gitignored. Never commit it.
- New metric columns go in both `core/main.py` `CSV_FIELDS` and the dashboard's parser.
- All time units are seconds; speeds are m/s; counts are integers. Never mix.

### `.claude/settings.local.json` — overly permissive
```json
"Bash(rm:*)",
"Bash(python:*)"
```
`rm:*` means "allow any rm command" and `python:*` means "allow any Python script." For a project that says "Safety first" in its rules, that's wide open. Tighten to specific paths: `Bash(rm data/qtable.tmp)` etc., or remove and rely on per-call confirmation.

### `.claude/agents/safety-reviewer.md`
Same backslash-escape issue. Body is too vague to be a useful sub-agent. After fixing the escapes, expand it to specify:
- Inputs: which files to read first.
- Specific failure modes to look for: phase flicker, yellow truncation, deadlock detection, MIN_GREEN bypass, emergency clearance failure.
- Expected output format: a JSON or markdown report with risk level + line numbers.

---

## 2. `core/traffic_env.py`

### **[CRIT]** Race condition on SUMO startup
```python
self._sumo_proc = subprocess.Popen(cmd, ...)
time.sleep(1.0)
traci.init(port=self.port)
```
A 1-second sleep is a guess. On a slow machine or under load, SUMO won't be listening yet → `traci.init` fails. On a fast machine you waste a second per episode. Fix: use `traci.start([cmd])` which forks SUMO itself and waits for the handshake, OR poll `traci.init` with retry-on-`FatalTraCIError`. Removing the sleep alone speeds RL training substantially (50 episodes × 1 s = 50 s saved).

### **[BUG]** Single fixed port collides under parallelism
`TRACI_PORT = 8813` is a module constant. If you ever run two simulations in parallel (e.g. for parallel RL training), they'll both try the same port. The constructor already accepts `port`, but no auto-allocation. Add `port=0` → "let OS pick" support, then read the actual port back.

### **[BUG]** Silent exception swallowing
```python
def set_phase(self, phase_index):
    for tl_id in TL_IDS:
        try:
            traci.trafficlight.setPhase(tl_id, phase_index)
        except traci.exceptions.TraCIException:
            pass
```
This hides typos in `tl_id`, missing programs on terminal junctions, and SUMO state errors. At minimum log at WARNING the first time it fails per `tl_id`. Better: query `traci.trafficlight.getAllProgramLogics(tl_id)` once at start and only call `setPhase` for valid indices.

### **[BUG]** `is_done` corner case
```python
return (
    traci.simulation.getMinExpectedNumber() == 0
    and traci.simulation.getDepartedNumber() > 0
)
```
If your routes have a long ramp-up (no vehicle has departed yet), and SUMO ends due to `--end 3600`, `getMinExpectedNumber()` returns 0 but `getDepartedNumber()` may also be 0 depending on timing. Episode never terminates from this check. Use `traci.simulation.getTime() >= self.sim_end` as a fallback.

### **[DOC]** Header docstring claims int_B is a "roundabout" elsewhere (rl_controller.py line 31) but the network is a 4-way crossroads. Pick one term and use it consistently. `intersection.nod.xml` shows `type="traffic_light"`, not a roundabout.

### **[REFACTOR]** Backward-compatibility shims on `NetworkState`
The `north_in`/`south_in`/`east_in`/`west_in`/`phase_index`/`phase_duration`/`lanes` properties on `NetworkState` only return data for `int_B`. They exist for old single-intersection code, but they're confusing now that the system is 3-intersection. Either:
- delete them and update `main.py`'s `_build_row` to read `state.intersections["int_B"]` directly, OR
- rename them to `b_north_in` etc. so the int_B-specific scope is obvious.

### **[BUG]** Mean speed is unweighted
`_approach_summary` averages lane mean speeds with equal weight. A 1-vehicle lane and a 50-vehicle lane count the same. Weight by `vehicle_count` (or use halting-based metrics) for a meaningful approach-level speed.

### **[ADD]** No teardown safeguard on `__exit__`
The `__exit__` method calls `self.close()` without a try/except. If close raises (network already disconnected), the original exception propagating out of `with TrafficEnv(...) as env:` gets clobbered.

### **[ADD]** `--waiting-time-memory 3600` accumulates over the full hour
With memory of 3600 s, a vehicle stuck at a light at sim_time=3600 has *all* its waiting time integrated. The pressure normalisation then keeps growing forever. Either match memory to your inter-decision window, or normalise differently.

### **[NIT]** `EMERGENCY_TYPE = "emergency"` is duplicated as a string in three files. Make it an importable constant from `traffic_env.py` and import everywhere.

---

## 3. `core/fixed_controller.py`

### **[CRIT]** Yellow duration mismatch with the network
`PHASES` declares `NS_YELLOW = 5.0 s`. But `simulation/intersection.net.xml` declares all yellow phases as `duration="3"`. The controller's `setPhase()` only changes which phase is active — it does NOT extend the yellow's duration. SUMO will still tick the yellow at 3 s and advance internally; you'll then re-issue a duplicate phase command. Effect: chaotic behaviour, the timing actually run is the network's 42/3, not the controller's 30/5. The README "30 s / 5 s baseline" is *not what's actually being benchmarked*.

**Fix options (pick one):**
1. Use `traci.trafficlight.setPhaseDuration(tl_id, duration)` after each `setPhase` to enforce 30/5 — this is what the controller pretends to do.
2. Change `PHASES` to match the network: 42/3.
3. Rebuild the network with 30/5 yellows.

Whichever you pick, **the README's baseline numbers need re-running** because the current "fixed" controller is fighting the network and producing a noise mix.

### **[REFACTOR]** Doesn't read `state` but accepts it
`update(state)` ignores `state` except for filling in three info-only columns. That's fine for a fixed controller, but you could log a WARNING when `state.intersections[tl_id].phase_index != self._phase_idx` — that mismatch is exactly the bug above and would surface immediately.

### **[NIT]** `_phase_changes` increments on every phase advance, including yellows. That's 4 changes per cycle. Document or only count green→yellow transitions.

---

## 4. `core/smart_controller.py`

### **[BUG]** `_advance_reason` compares pressure to seconds
```python
if old_state == _State.NS_GREEN:
    if ew_p >= effective_max:    # ew_p is 0..2 (normalised), effective_max is 60..90 (seconds)
        return "congestion_max"...
    return "wave_bias" if ew_p >= SWITCH_RATIO else "pressure_ew"
```
`effective_max` is in seconds; `ew_p` is a normalised pressure in [0, 2]. The first branch can never fire. The "congestion_max" reason is dead. Fix: compare `elapsed >= effective_max` (which is what the actual switch decision uses earlier).

### **[BUG]** "wave_bias" reason check is wrong
```python
return "wave_bias" if ew_p >= SWITCH_RATIO else "pressure_ew"
```
Should be `(ew_p / max(ns_p, 1e-6)) >= SWITCH_RATIO`. As written, you're comparing a single pressure to a ratio — meaningless.

### **[BUG]** Running max never resets
`_MaxTracker.max_count` and `.max_wait` only grow. Once you hit a 50-car peak in episode 1, episode 5's normalised pressure is permanently lower for the same traffic. Comparing controllers across episodes becomes unfair. Either reset on `reset()`, or use a sliding-window max (e.g. last 600 s).

### **[BUG]** `WAVE_TRIGGER_DELAY` and `TRAVEL_TIME` overlap
`WAVE_TRIGGER_DELAY = 10` (delay before forcing int_B to switch when int_A goes EW) and `TRAVEL_TIME = 29` (estimated platoon arrival) are independent, but they should be derived from the same edge length / speed. Edge AB is 400 m, max speed 13.9 m/s, so travel time ≈ 28.8 s. The 10 s delay lets cars build up at int_B before switching. Document the relationship; ideally compute both from `(edge_length / max_speed)` read from the network XML.

### **[BUG]** `_emit_coordination` overwrites wave hints without combining
If int_A and int_C both enter EW_GREEN within a few seconds, both will set `int_B.wave_hint`. The second call overwrites the first. Use a list, or take the closer ETA.

### **[REFACTOR]** Magic numbers everywhere
14 tunable constants at the top of the file. Move into a `@dataclass` config and accept it as a constructor argument. Lets you A/B-test parameter sets without code changes.

### **[REFACTOR]** `_apply_phase` fallback is a guess
```python
try:
    self.env.set_phase_at(ns.tl_id, phase_idx)
except Exception:
    try:
        self.env.set_phase_at(ns.tl_id, phase_idx % 2)
    except Exception:
        pass
```
`% 2` happens to map (2 → 0, 3 → 1) which is reasonable for terminal T-junctions whose programs only have 2 indices, but it's a coincidence not a design. Build a per-node phase mapping from the network XML at startup.

### **[NIT]** `MIN_GREEN` (8.0) is also defined in `rl_controller.py`. Single source of truth.

---

## 5. `core/rl_controller.py`

### **[CRIT]** Every training episode uses the same SUMO seed
`TrafficEnv.__init__` accepts `seed`, defaults to 42. `RLController.train()` calls `self.env.start()` 50 times — same env, same seed. SUMO replays the *same* trajectory every episode. The agent isn't learning to handle traffic; it's memorising one specific episode.

**Symptom:** Q-table grows but generalisation is zero. Tabular Q-learning is supposed to generalise across similar states, but if every episode hits the same state sequence, you're effectively in a deterministic environment with no need for Q-learning.

**Fix:** Vary the seed per episode in `train()`:
```python
for ep in range(1, episodes + 1):
    self.env.seed = (self.env.seed + ep * 7919) % 2**31
    self.env.start()
```
Or expose `env.set_seed(s)` and call it per episode. Same fix applies to `pretrain_from_smart`.

### **[CRIT]** Reward scaling docstring contradicts code
Docstring (line 56): `Normalised by dividing by 1000 → range roughly -100 … +100 per step.`
Code (line 365): `reward /= 100.0`
Fix one of them. The actual weights × typical magnitudes give a reward of order ±100 raw, so `/100.0` puts it in ±1 range, not ±10 as the inline comment claims.

### **[BUG]** `_apply_min_green` bypasses yellow timing
When the current phase is a yellow (NS_YELLOW or EW_YELLOW), the function rewrites the action to keep moving toward the next green. But yellow has a fixed duration (3 s in the network); cutting it short would be unsafe. The current code doesn't actually call `setPhase` during yellow (because `_apply_action` only acts when current is green), so the bug is dormant — but the logic is fragile. Add an explicit "if in yellow, action is locked, don't change" guard.

### **[BUG]** Compare-decision touches private state
`compare_decision` reads `smart_controller._nodes` directly. If `SmartController` ever renames it, hybrid mode silently breaks. Add a `SmartController.get_node_states() -> dict[str, _State]` public accessor.

### **[BUG]** Q-table version stamp missing
`_load_qtable` does a shape check (state-tuple length = 11) but no explicit version field. When you change reward/encoding, the load might pass the shape check but be semantically wrong. Save `{"version": "v6", "table": data}` and refuse to load mismatched versions.

### **[BUG]** Pretraining seeding strategy can be gamed
First-visit `+5`, revisit `+0.5`, capped at `+20`. A state visited 30 times gets +20; a state visited once gets +5. Then real Q-learning uses ALPHA=0.1 against rewards in ±1 range. The pretrain seed dominates for many episodes. Either lower PRETRAIN_INIT, raise ALPHA, or run more training episodes. Document the convergence assumption: "after N episodes the Bellman update should be larger than the pretrain seed."

### **[ADD]** No training metrics file
`train()` only logs to stdout. After a 50-episode run you have no reward curve, no Q-table growth chart, no exploration trace. Write `data/training_log.csv` per episode: `episode, steps, reward, switches, eps, qtable_entries, wall_seconds, wait_total`.

### **[ADD]** No held-out evaluation step
`train` ends and you assume the policy is good. Add `evaluate(n_seeds=5)` that runs the policy with `epsilon=0` against fresh seeds (not the training seeds) and reports mean/std waiting time. Without this, all RL claims are unfalsifiable.

### **[ADD]** No replay or batch updates
Tabular Q-learning here is purely online. For your scale (186 K entries), occasional offline sweeps over a recent buffer would stabilise convergence. Optional but worth experimenting.

### **[REFACTOR]** Inline `__import__("time")` calls (lines 713, 739)
Just `import time` at the top.

### **[REFACTOR]** `traci` imported inside functions for lazy loading
Acceptable — but document the pattern. Right now `_compute_reward` does `import traci as _traci`, `pretrain_from_smart` does `import traci`, etc. Consolidate.

### **[NIT]** `_PHASE_TO_ACTION` is a global derived from `_ACTION_PHASE`. Compute lazily or at module import; both are fine, but currently it's eagerly built and that's fine.

### **[DOC]** Docstring section "Reward (v4 — scaled for stability)" lists the wrong term: it omits `W_QUEUE_PENALTY` and `W_SWITCH_PENALTY` which are in the actual code.

---

## 6. `core/vision_bridge.py`

### **[CRIT]** Direct phase jump on emergency override skips yellow
```python
self.env.set_phase_at(tl_id, target_green)
```
called even when current phase is the *opposite* green. SUMO accepts mid-cycle phase changes, but skipping the yellow violates real-world traffic engineering and causes simulated rear-end risk (vehicles entering on green won't get warning before opposing flow gets green). For a project labelled "Safety first" this is the most concerning bug.

**Fix:** When current is the opposite green, first set the corresponding yellow for `YELLOW_DURATION` seconds, then set target green. Track the transition state in `_override_axis` or a new `_override_phase` field.

### **[BUG]** Lane-prefix detection is fragile
`_NS_LANE_PREFIXES` and `_EW_LANE_PREFIXES` are hardcoded. Any new intersection breaks emergency axis detection silently. Pull from `NETWORK_APPROACHES` in `traffic_env.py`.

### **[BUG]** Phase flicker possible with Smart re-applying
Order in `update`:
1. Process triggers (may apply override phase).
2. Smart's update (may apply its own phase).
3. Enforce active overrides (re-applies override phase).

Within one TraCI step you can have 3 phase commands. The CSV logs the last-read phase. There's no guaranteed order vs SUMO's internal state — should be OK because SUMO processes commands in batch, but it's worth a comment in the code.

### **[BUG]** Night-mode extension only fires when the phase already matches
`_apply_night_extension` does nothing when current phase ≠ target green and silently logs at DEBUG. So a confirmed emergency in night mode on the wrong axis produces no action and no visible warning. Either trigger the same yellow→target-green transition as full override, or log at INFO and increment a "missed_night_extension" counter.

### **[ADD]** No success metric for emergency clearance
The session summary tracks `vision_emg_overrides` (count of triggers) but not whether the emergency vehicle actually cleared. Add a counter for "emergency arrived at int_C exit" and report ratio.

### **[NIT]** `EMG_CONFIRM_FRAMES = 3` at 1-second steps means a 3-second confirmation latency. For a fire truck doing 22 m/s, that's 66 m of travel before any green is given. Document this trade-off.

---

## 7. `core/camera_detector.py`

### **[BUG]** `random.uniform` and `random.random` are not seeded
The detector's confidence and bbox jitter use the unseeded global `random` module, so detection output varies between runs even with the same SUMO seed. For controller-to-controller comparison you want deterministic camera output. Either seed in `__init__(self, seed=42)` or accept seed via `set_traci`.

### **[BUG]** Fallback estimation can fabricate emergencies
`_fetch_vehicle_types` falls through to estimation when TraCI fails. The fallback fakes IDs `f"ems_sim_{lane_id}"` that pass the strict emergency check — so a transient TraCI hiccup during a frame produces a fake high-confidence emergency report. **VisionBridgeController will then start an override based on a phantom.** Fix: in fallback mode, always set `is_emergency=False`, regardless of `has_emergency` flag.

### **[REFACTOR]** Frame rendering is dead code
`render_frame` produces an OpenCV image but nothing in the codebase calls it. Either:
- Wire it up: write `data/frames/{tl_id}/{sim_time:06.0f}.png` every N seconds when `--vision --record-frames` is passed.
- Delete it.

### **[REFACTOR]** 511 lines for fake YOLO
Most of it is bbox geometry. Rename file to `simulated_camera.py` so future-you doesn't expect a real CV pipeline. Document the top of the file: "This is a simulated detector. To swap in a real YOLOv8: implement `analyze_frame(rgb_image)`."

### **[NIT]** `_BBOX_SIZE`, `_BGR`, `_CONF_RANGES` could be one dataclass per vehicle type instead of three parallel dicts.

---

## 8. `main.py`

### **[CRIT]** `--qtable` not validated for hybrid/rl modes
If you invoke `--mode hybrid` and `data/qtable.pkl` doesn't exist (or is empty), the run starts and uses an empty Q-table — meaning RL never overrides Smart, and you silently get a "Smart-only" run mislabelled as "hybrid". Add an explicit check:
```python
if mode in ("rl", "hybrid") and not Path(qtable_path).exists():
    raise FileNotFoundError(f"--mode {mode} requires {qtable_path}; run rl-pretrain or rl-train first")
```

### **[BUG]** `--episodes` semantics differ per mode
- `rl-train`: training episodes (clear).
- `hybrid`: test episodes (clear-ish).
- `fixed`/`smart`/`vision`/`rl`: silently forced to 1 (line 622 `ep = args.episodes if args.mode == "hybrid" else 1`).

So `python main.py --mode smart --episodes 10` runs *one* episode, with no warning. Either:
- Log a WARNING when episodes is overridden.
- Honour the flag in all modes (probably what users expect for benchmarking).

### **[BUG]** `--episodes 100` default for hybrid is enormous
A single hybrid episode at 3600 s with TraCI overhead takes ~30–60 s. Default 100 = up to 100 minutes. Make the default 5; mention in `--help` that benchmarking studies should use ≥30.

### **[BUG]** `_emergency_count` counts approach groups, not vehicles
The function name and CSV column name imply vehicle count. The implementation counts approaches with at least one emergency. A single ambulance at int_B that touches one lane in the north approach gives count=1, but it's the same ambulance not "one emergency event". Either rename the column to `emergency_approaches` or change the implementation.

### **[REFACTOR]** `HybridController` belongs in `core/`
85 lines of controller logic in `main.py`. Move to `core/hybrid_controller.py`. `main.py` should be a thin CLI dispatcher.

### **[REFACTOR]** `_build_row` belongs in `core/metrics.py`
Same reasoning. Plus you'll want a unit test for it (given a mock NetworkState, do the columns come out right?), which is awkward to import from `main.py`.

### **[BUG]** Logger config is global and uninstrumented
`logging.basicConfig(level=INFO)` writes to stderr only. Long RL training runs lose their logs when the terminal closes. Add a rotating `FileHandler` writing to `data/logs/run_{mode}_{timestamp}.log`.

### **[ADD]** No final waiting-time-by-percentile in summary
The summary prints `avg_total_waiting_time` but no p50/p95/p99. Two controllers with identical averages can have wildly different tails. Compute percentiles from `tripinfo.xml` post-run (it's already enabled in sumocfg).

### **[ADD]** No per-controller smoke test
`python main.py --mode all --quick` doesn't exist. Add a `--mode all` that runs each controller for 1 short episode (e.g. 600 s) and prints a one-line summary. Useful for catching regressions.

### **[NIT]** `os.environ["PYTHONIOENCODING"] = "utf-8"` (line 26) is fine but should be set before `import logging` to be safe on Windows console. Currently it's after, which usually works but isn't guaranteed.

### **[NIT]** `time.perf_counter()` vs `time.time()` choice — currently uses perf_counter, which is correct for elapsed-time measurement.

---

## 9. `simulation/`

### **[CRIT]** Network yellow durations don't match controllers
Already covered in §3. The `.net.xml` declares 42 / 3 / 42 / 3. Decide your single source of truth and align everything to it.

### **[BUG]** Rerouting flags are dead config
`simulation.sumocfg` has:
```xml
<device.rerouting.adaptation-steps    value="18"/>
<device.rerouting.adaptation-interval value="10"/>
```
But no flow declares `<param key="has.rerouting.device" value="true"/>`, and the cfg has no `--device.rerouting.probability`. So no vehicle has the rerouting device and these flags do nothing. Either:
- Add `--device.rerouting.probability="0.3"` to the cfg, OR
- Remove the dead flags.

If you do enable rerouting, your traffic patterns become more realistic (cars route around accidents) and the controllers' jobs change.

### **[BUG]** `--ignore-route-errors true` hides real bugs
During development, set this to `false`. SUMO will fail loudly when a route references a non-existent edge instead of silently dropping vehicles. Re-enable on release benchmarks if needed.

### **[BUG]** `--time-to-teleport 300` masks deadlocks
A vehicle stuck for 300 s teleports past the obstacle. For RL training, that artificially inflates throughput and reduces the "queue improvement" reward. Lower to 60 s for training validation.

### **[BUG]** `pedestrian_proxy` vehicles run on roads, not crossings
`vType id="pedestrian_proxy"` has length=1 m, maxSpeed=1.8 m/s, and is dispatched as a *vehicle* on a road edge. So it occupies a lane and blocks traffic at 1.8 m/s. That's not how pedestrians work. Either:
- Rename to `slow_obstacle` and own that it's a proxy, OR
- Use SUMO's actual pedestrian model with `<person>` elements and crossings.

### **[BUG]** Only one accident per peak (3 total)
Three obstacle events at t=400, 1100, 2200 — only one is in the evening peak. The morning peak has 2. For balanced controller stress, place evening accidents symmetrically. This is a benchmarking-fairness issue.

### **[BUG]** Emergency vehicle interval (240 s) is shorter than override cooldown (300 s)
`ems_06` at t=1260 and `ems_07` at t=1500 are 240 s apart. `vision_bridge.EMG_COOLDOWN_S = 300`. So emergencies arriving within the cooldown of the same intersection get *silently ignored*. Either:
- Stagger emergencies more (300 s+).
- Make the cooldown per-axis instead of per-intersection.
- Document that consecutive same-route emergencies are intentionally suppressed.

### **[ADD]** No detector loops, no induction loops
Real-world traffic counters use loop detectors (E1) or area detectors (E2/E3) for ground truth. SUMO supports these via `<inductionLoop>` elements. Add them to the network and have FixedController etc. read from them — closer to real deployment.

### **[ADD]** No `intersection.tll.xml` separately
Traffic-light logic is inlined into `intersection.net.xml`. Standard SUMO practice is a separate `.tll.xml` file you can hot-swap. Refactor on a rainy day.

### **[REFACTOR]** Hand-edit the `.net.xml`?
The `.net.xml` is the *generated* file from `.nod`/`.edg`/`.con`. If you modify the generated `.net.xml` directly, the next `netconvert` run blows away your changes. Add a `simulation/build_network.sh` script:
```bash
netconvert --node-files=intersection.nod.xml \
           --edge-files=intersection.edg.xml \
           --connection-files=intersection.con.xml \
           --tllogic-files=intersection.tll.xml \
           --output-file=intersection.net.xml
```

### **[NIT]** `routes.rou.xml`: vehicle type `obstacle` has `decel=10.0` but `emergencyDecel` is not set; SUMO will warn. Set `emergencyDecel="10.0"` explicitly.

---

## 10. `data/`

### **[BUG]** Stale CSVs from older controllers
Files dated April 16 to April 27 sit alongside each other. The `results_hybrid.csv` is from April 16; the `results_rl.csv` is from April 22. The controllers have changed since then. Comparing them across dates = comparing apples to old-apples. Either:
- Re-run all five modes with the *current* code in one batch, OR
- Embed a `controller_version` column in each CSV (e.g. git short SHA at run time).

### **[ADD]** No `training_log.csv`
See §5 above.

### **[ADD]** No `evaluation_log.csv` for held-out test runs
See §5 above.

### **[NIT]** `qtable.bak` is committed-style filename but actually gitignored. Filename suggests "backup" — keep, but document the rotation policy in `rl_controller._save_qtable`'s docstring.

---

## 11. `dashboard/app.py` (1458 lines)

### **[REFACTOR]** Monolithic file
1458 lines is too much for one Streamlit app. Split by concern:
- `dashboard/data_loader.py` — CSV reading, caching.
- `dashboard/charts.py` — Plotly figure builders.
- `dashboard/components/kpi_cards.py`, `…/comparison_table.py`, etc.
- `dashboard/theme.py` — palette, fonts, plotly base config.
- `dashboard/app.py` — wires it all together; should be < 200 lines.

### **[BUG]** No `@st.cache_data` on CSV reads
CSV files are read on every render. With ~400 KB CSVs that's not painful, but with 1.5 MB hybrid CSV it adds up. Wrap `_load_csv(path) -> pd.DataFrame` with `@st.cache_data(ttl=60)` (after migrating to pandas — currently you use the stdlib `csv` module manually).

### **[BUG]** Hardcoded colour palette
20+ hex codes scattered across the file. Move to `theme.py`. When the user wants a light-mode toggle, it'll be a one-file change.

### **[ADD]** No comparison-percentile chart
Currently the dashboard probably plots averages. Add a CDF / box plot of waiting times across the run. That's where controller differences actually appear.

### **[NIT]** No version display
The dashboard doesn't print the git SHA or controller version it's reading. Add a footer: `Data from {csv.last_modified} | Code: {git_sha}`.

---

## 12. `dashboard/intersection_diagram.py` (254 lines)

Already noted: **[CRIT] Untracked, not in git.** First action: commit it.

Beyond that:
- **[NIT]** Pure inline SVG injection via `st.html`. Works but doesn't react to data updates without a full page rerun. If you want live phase changes during a SUMO run, you'll need `st.experimental_rerun` or `streamlit_autorefresh`. Document.
- **[ADD]** No tests. A pure rendering function is easy to snapshot-test. Use `pytest` + `syrupy` to guard against accidental visual regressions.

---

## 13. `dashboard/map_view.py` (578 lines)

- **[BUG]** `_find_root` walks up 3 levels looking for a `data/` dir. If you ever rename `data/` or run from inside a subdir, this returns the wrong root. Better: read the env var `AI_TRAFFIC_BRAIN_ROOT` or use a sentinel file (e.g. `.project_root`).
- **[REFACTOR]** Folium map config is inline. Move into `dashboard/map_config.py`.
- **[ADD]** Casablanca-specific lat/lon hardcoded. Document or parametrise so users in other cities can re-skin.
- **[NIT]** `HeatMap` import is used; make sure folium >= 0.18 includes it (it does).

---

## 14. `dashboard/pages/live_map.py` (1495 lines)

### **[CRIT]** "Live" is a lie — it's all mock data
The file's docstring even admits it:
```
* In DEMO mode that dict is populated with mock values generated in JS.
* To connect real simulation data: replace the INJECT_DATA section…
```

The README markets this as "Animated live schematic map" alongside the dashboard. There's no Streamlit ↔ SUMO bridge. Either:
- Wire it up: have the streamlit page poll `data/results_*.csv` (or a live fifo from `main.py`) and inject the latest row into the JS via Streamlit's component API.
- Rename the page to "Demo Schematic" and remove "live" from the README.

### **[REFACTOR]** 1500 lines of inline HTML/CSS/JS in a Python file
Move the HTML to `dashboard/templates/live_map.html` and the JS to `dashboard/static/live_map.js`, load with `pathlib.Path.read_text` and inject. Easier to lint and edit.

---

## 15. `README.md`

### **[CRIT]** Broken image links
```markdown
![dashboard](docs/screenshots/dashboard.png)
![live map](docs/screenshots/live_map.png)
```
The `docs/` folder doesn't exist. On GitHub these render as broken images. Either create the folder + images, or remove the section.

### **[BUG]** Performance table is unverifiable
| Controller | Avg Waiting Time | vs Fixed |
| Fixed | 241 s | baseline |
| Smart | 213 s | −12 % |
| RL | 183 s | −24 % |

Three problems:
1. No mention of how many episodes / which seed / which date the numbers come from.
2. No standard deviation. A 28-second improvement (Fixed → Smart) means nothing without ±. A single-run comparison on a stochastic env is anecdotal.
3. No tail metrics (p95, max queue).

Replace with a generated `benchmarks/results.md` written by a `make benchmark` target. Include git SHA, seed list, and re-run instructions.

### **[BUG]** Missing modes from the table
The table lists Fixed/Smart/Vision/RL/RL-Pretrain/Hybrid but the *Key Results* section has only Fixed/Smart/RL. Add Vision, Hybrid, and RL-Pretrain rows once you have honest numbers.

### **[BUG]** "Project Structure" section is incomplete
- No mention of `dashboard/intersection_diagram.py`.
- Lists `simulation.sumocfg` but not `intersection.{nod,edg,con,net}.xml` or `routes.rou.xml`.
- Says `data/ Generated CSVs and Q-table (gitignored)` — accurate.
- No `.claude/` mention even though it's a meaningful piece of the project (after fixing the escapes).

### **[ADD]** Missing sections
- **Architecture** — a diagram showing TrafficEnv ↔ Controllers ↔ SUMO/TraCI, and how the dashboard reads CSVs. ASCII art is fine.
- **How to evaluate fairly** — protocol for running a benchmark: which seeds, how many episodes, which CSV columns to compare, how to compute p95.
- **Known limitations** — pedestrian proxy, single-day cycle, no weather, no real cameras, no rerouting, etc. Honesty here saves you defending it later.
- **Roadmap** — what comes after tabular Q-learning (linear features, DQN, multi-agent).

### **[NIT]** Author block at the bottom is fine but missing affiliations email / contact.

---

## 16. CLAUDE.md (the project one, after escape fix)

After you fix the escapes, add the items I listed in §1 (CLAUDE.md section). Concrete project rules > slogans.

---

# Priority order — what to fix first

1. **Untrack-fix `dashboard/intersection_diagram.py`.** Anyone who clones can't run the dashboard. (5 minutes.)
2. **Fix the backslash-escape on every `.md` file in `.claude/`.** Skills and CLAUDE.md become readable again. (15 minutes.)
3. **Fix the per-episode SUMO seed in `RLController.train` and `pretrain_from_smart`.** Right now the agent is memorising one trajectory. (30 minutes.)
4. **Reconcile yellow durations between FixedController (5 s), SmartController (3 s), and the network (3 s).** Pick one; the README baseline depends on it. (1 hour incl. re-running benchmarks.)
5. **Fix the camera_detector.py phantom-emergency fallback.** Vision can spuriously trigger overrides. (30 minutes.)
6. **Add `tests/`** — start with `test_traffic_env.py` (round-trip a NetworkState), `test_smart_controller.py` (FSM transitions on synthetic states), `test_rl_controller.py` (encode_state determinism, q_update math). Even 10 tests would catch most regressions. (Half a day.)
7. **Add `data/training_log.csv` and a held-out evaluation function.** Without these you can't honestly claim RL improves things. (Half a day.)
8. **Re-run all five controller benchmarks on the same git SHA, with N≥10 episodes, and update the README table with mean ± std + p95.** (1 day incl. compute time.)

Everything else (refactors, docstring fixes, theme module, dashboard split) is polish that can wait until after items 1–8 are done.
