# Performance review — 12 September 2026

Neon Horizon's setup tools are fast on the measured M5 Max. The remaining performance uncertainty is the continuously rendered wallpaper. Its small download does not establish a small rendering cost. This review found one reproducible setup-deadline defect, unnecessary work in the mouse-movement handler, and several rendering candidates that need profiling before changing the artwork.

Reviewed source: `1626cd787b8486bef1da3611b5a77b5bf182bcaa`. No production behavior or Mac preferences were changed by this review. The added benchmark runs isolated builds or explicitly requested read-only previews. Findings below remain open unless marked as an accepted cost.

## Scope and measurement conditions

- M5 Max, 18 CPU cores, 48 GiB RAM, macOS 27.0 beta build 26A428. Python 3.12.14, Pillow 12.3.0, NumPy 2.3.5; Lua 5.4.8 for control checks.
- A live workstation, with other applications running. The initial one-minute load average was 7.07. No apps were stopped to improve results. These are local observations, not controlled hardware benchmarks or an M5 Pro certification.
- Five timed fresh processes after one discarded warmup for each operation. OS caches were not flushed. Operations ran sequentially. Reported ranges are observed minimum–maximum, not confidence intervals.
- A separate 30.31-second process observation used seven snapshots of cumulative CPU time and resident memory. CPU percentages use **one CPU core as 100%**; they are not percentages of the whole 18-core processor. A process named WebKit.GPU still reports CPU time here, not GPU utilization.
- Native preview measurements read preferences and aggregate app metadata; no private app names or usage history are included here. Apply/undo were tested with fixtures, not timed against live settings.
- The installed HTML and all three installed control modules matched the reviewed files. HTML SHA-256: `061679fed401cbb755c1d40b63ee4507312f2e3fb00300673bb873b96f9267ec`. File equality does not confirm the selected Plash site.
- The earlier browser access restriction prevented live wallpaper inspection. No alternate browser, renderer, live HTTP route or capture was used to bypass it. **Frame times, dropped frames, compositor layers, GPU memory/utilization, energy and visual smoothness remain unmeasured.**

## Measured tools and builds

| Operation | Median operation time | Observed range | Median fresh-worker wall time | Peak Python RSS, median |
|---|---:|---:|---:|---:|
| Assemble HTML from prepared assets | 12.19 ms | 11.62–12.81 ms | 52.16 ms | 31.72 MiB |
| Prepare all images, grade and encode | 3.078 s | 3.014–3.269 s | 3.160 s | 275.44 MiB |
| Preview all 39 preferences | 60.99 ms | 59.56–65.36 ms | 103.11 ms | 23.78 MiB |
| Preview existing Dock pins | 515.90 ms | 512.21–525.66 ms | 553.76 ms | 24.70 MiB |
| Preview Dock with app discovery | 1.493 s | 1.475–1.518 s | 1.532 s | 25.19 MiB |

Operation time excludes interpreter/import startup, fixture preparation, result printing and post-operation assertions. Fresh-worker time includes those. Native previews call the planning functions directly; these are not timings of the interactive launcher or an apply. RSS is the Python process peak for the whole worker, not its incremental operation allocation, not native subprocess peaks, and not wallpaper GPU memory.

The image profile's separate run took 2.884 seconds; WebP encoding consumed 2.469 seconds, about 86%. Grading took 143 ms and static-preview bloom 47 ms. This is build-time work: the desktop does not execute Python image grading or encoding each frame. Changing encoders, quality or adding GPU dependencies is not justified by a three-second optional rebuild.

A separate instrumented Dock run made 13 metadata calls for existing pins and 37 with discovery. Those calls consumed 500 of 520 ms and 1,341 of 1,374 ms respectively. Metadata lookup, rather than sorting, accounts for nearly all preview latency. These diagnostic runs are distinct from the five-run medians above.

An isolated host serving **789,976 synthetic bytes**, using a temporary file and ephemeral loopback port, completed 50 sequential GET requests at a median 0.433 ms (0.252–1.039 ms), and HEAD at 0.202 ms (0.162–0.639 ms), after one warmup each. Each request opened a new connection and checked status, length and body. This measures the repository handler with a fixture, not the installed legacy host, browser load, parsing or first paint.

## Current Mac observations

| Process observed | Average CPU, one-core basis | Observed RSS range |
|---|---:|---:|
| Plash application | 5.58% | 68.20–68.25 MiB |
| Hammerspoon application | 0.56% | 60.88–60.88 MiB |
| Existing wallpaper Python host | 0.03% | 1.64–1.64 MiB |
| WindowServer, shared by the desktop | 78.42% | 201.02–201.17 MiB |
| Active WebKit GPU process, attribution unconfirmed | 15.44% | 199.56–203.55 MiB |
| Active WebKit web-content process, attribution unconfirmed | 19.89% | 122.80–122.95 MiB |

These rows must not be summed into a wallpaper cost. No process-to-page attribution or active-versus-paused comparison was available. WindowServer serves the whole desktop; Hammerspoon's total includes native event handling and any loaded configuration. No assistant UI actions occurred during the sample, but user activity and other applications were not controlled. Thirty seconds cannot establish long-session stability or rule out leaks.

The data volume had about 1.0 TiB available. Swap usage was about 3.36 GiB, but a later ten-second observation recorded **zero new swap-ins, swap-outs or page-outs**. `memory_pressure -Q` reported 72% system-wide free percentage, a macOS diagnostic metric rather than a literal unused-RAM count. The thermal query reported no recorded thermal or performance warning and no CPU power status. These observations do not demonstrate active memory thrashing or a thermal bottleneck; they also do not establish clock residency, temperatures or sustained GPU headroom.

## Findings and priorities

### 1. High priority: establish a real wallpaper performance budget

The wallpaper has 193 HTML elements and 167 animation targets: 159 elements plus eight pseudo-elements, carrying **171 CSS animation instances across 36 keyframe definitions** in the default mode. There are 71 explicit `will-change` targets, 25 filter-bearing nodes, 22 mask-bearing nodes and 18 non-normal blend nodes. These are source counts, not measured compositor-layer counts. The filters themselves are static; animated descendants or surrounding composition can still require work.

The positive design choices are an offline, self-contained page, declarative animation, no recurring JavaScript rendering/timer loop, shared embedded assets, visibility pausing and Reduce Motion support. WebKit recommends declarative animation and minimizing continuously active work; actual compositing and paint costs still require measurement. See [WebKit's power guidance](https://webkit.org/blog/8970/how-web-content-can-affect-power-usage/) and [its distinction between DOM elements and compositing layers](https://webkit.org/blog/8262/visualizing-layers-in-web-inspector/).

**Next:** obtain an authorized live-render trace before approving a performance claim or deleting effects. Compare normal, calm, static/paused, background and Reduce Motion states at identical dimensions and refresh settings. Record frame-time distribution, missed presentation deadlines, paint/style work, CPU, GPU/energy and layer memory. Repeat on M5 Pro and a high-resolution external display. A 60 Hz interval is 16.67 ms and a 120 Hz interval 8.33 ms; neither refresh mode was measured here. Calm changes speed, not a documented frame cap, and has no demonstrated energy saving.

### 2. Rendering candidate: the inherited storm parameter

In [scene.py](../wallpaper/build/scene.py), `--storm` is registered with inheritance and animated on `.storm-wrap`; its four lighting and haze descendants consume it. Far/mid/near rain have a separate wrapper-opacity animation; warm rain has its own gust/squall animations. Of the 171 animation instances, 170 animate transform and/or opacity and one animates this inherited custom property. A slow 433-second cycle still changes a value throughout the cycle. Additional style work within this wrapper is a hypothesis worth testing, not a measured defect in this WebKit version.

**Smallest experiment:** freeze the storm value in a temporary profiling variant, retaining every other effect. If style/paint work falls materially, localize the modulation to its actual consumers while preserving their phase and Reduce Motion baselines. Do not replace the renderer merely because the property is inherited.

### 3. Rendering candidate: oversized rain and full-scene effects

Rain uses three broad depth planes plus a narrow warm plane. Four embedded SVG tiles contain 410 source drops expanded to 1,071 rectangle instances; these are image primitives, not 1,071 extra DOM animations. Rain overscan, the masked near painting, screen-blended bloom, reflection masks and atmospheric layers are the first surfaces to inspect.

For an **illustrative**, unmeasured 1920 × 1200 CSS viewport at DPR 2, the world is 1836 × 1224 CSS pixels. A hypothetical full-world RGBA8 backing is 34.29 MiB. Each broad mid/near rain pseudo-element has a 2540.24 × 3220 CSS-pixel rectangular extent, 3.64 times the world area, equivalent to 124.81 MiB **if** fully rasterized at DPR 2. Clipping, tiling, caching, backing format and browser-selected raster scale can change actual allocation substantially. Do not multiply these estimates by animation counts or call them measured memory.

**Next:** inspect actual layer extents, raster scale, paint invalidation and overdraw. If these bounds survive compositing, first tighten only the near-rain gutters while preserving texture phase and checking visual seams, then test bloom and the near-plane separately. Far/mid masks depend on their parent geometry, so a global gutter reduction could change the rain's appearance. A static precomputed glow is worth considering only if profiling identifies live filtering as material; compare multiple sizes because the current scaled blur has a CSS-pixel radius rather than a fixed source-image radius. Preserve the reflection and boat composition until a measured comparison supports a change.

One source comment beside `.chrome` still claims that any blend mode forces a full-viewport flatten every frame. That universal cost claim lacks engine evidence; it should describe the intended normal compositing instead. This is a wording finding, not proof of a rendering regression.

### 4. Confirmed extra work: display lookup on every mouse move

[edge_dwell.lua](../controls/edge_dwell.lua) handles mouse events without idle polling. It maintains at most one one-shot dwell timer, does not consume input, cancels on conflicting input/display/sleep events, and releases timers/watchers on stop. Nine shortcuts register once and run only when pressed. These are good defaults.

On a valid single display, `zone()` calls `allScreens`, `find(UUID)` and `fullFrame` on every move, even in the center. Hammerspoon 1.1.1's wrappers expand this into three enumerations, two UUID reads, one name read and two raw-frame reads. This matches the installed wrapper source and the upstream [find](https://github.com/Hammerspoon/hammerspoon/blob/1.1.1/extensions/screen/screen.lua#L73) and [fullFrame](https://github.com/Hammerspoon/hammerspoon/blob/1.1.1/extensions/screen/screen.lua#L191) implementations.

An offline probe compared the current module with a temporary direct-screen variant. Over 10,000 moves, using the sole already-enumerated screen reduced enumerations from 30,000 to 20,000, UUID reads from 20,000 to 10,000, and name reads from 10,000 to zero. Simulated cancellation/rearm produced the same two strokes, eight timers and zero retained resources after stop. These are **call-count reductions**, not measured native speedups; the variant was not shipped or installed.

**Smallest change to consider:** use the sole screen already returned by `allScreens`, retain fresh geometry and UUID validation, then run the existing scenarios plus native movement profiling. Avoid throttling mouse events: missing a brief edge exit could violate continuous two-second dwell. Additional candidates are removing per-move geometry string construction and skipping input probes only while already latched; each needs its own equivalence check. Timers execute on Hammerspoon's run loop, so a two-second delay is not a hard real-time delivery guarantee. [Timer documentation](https://www.hammerspoon.org/docs/hs.timer.html)

### 5. Reproduced defect: host readiness can overrun five seconds

[host.py](../wallpaper/host.py) checks the readiness deadline between attempts, but `loaded_job()` does not time-limit `launchctl print`. A successful HTTP response can also be accepted after the deadline; a socket timeout is not a total operation budget.

Two fake-clock probes exercised the real readiness path with all I/O mocked. A six-second service inspection returned success despite the five-second deadline. A six-second successful response read did the same. The actual subprocess wrapper supplied no timeout. No native command, network connection or real sleep was used in these probes. This proves the deadline-control gap, not that the installed host has experienced such a stall.

**Repair plan:** pass remaining time into service inspection and network operations, reject overdue success, and test delayed service inspection, delayed/chunked response delivery and ordinary successful startup. Keep identity checks, bounded body reads and cleanup. Other installer commands without timeouts should receive a separate failure-path review; no normal hang was observed.

### 6. Scaling concern: serial Dock metadata

[dock.py](../dock.py) requests metadata separately for each eligible app, with a three-second timeout each. Discovery caps additions at three after querying all candidates. With `N` queried apps, repeated metadata timeouts can contribute roughly `3N` seconds, plus other work; a large installation can therefore have a slow preview despite a small final Dock.

**Disposition:** keep the simple serial implementation for now. Measured previews were 0.52–1.49 seconds. If repeated real-world previews become slow, first add an overall metadata budget with an explicit incomplete-data message; only then consider a small bounded worker pool. Preserve stable ordering and missing-metadata behavior. Sorting, persistent caches and a background usage tracker are not justified by these measurements. There is no ongoing Dock-ranking process.

### 7. Accepted setup costs: durability, image encoding and tiny HTTP reads

When all 39 native settings differ, the source performs 164 subprocess calls including preview/version detection, plus 78 journal synchronizations. Each changed key is checked before journaling, after journaling and after writing. An already-matching full-preset CLI path uses eight native calls and no journal write. These counts are source accounting, not a measured live-apply duration. Removing the checks for speed would lose protection against later user edits and partial failure.

The optional host reads the entire 0.75 MiB page even for HEAD, and GET allocates per-request payload bytes. The fixture's 0.20 ms HEAD and 0.43 ms GET medians do not justify a cache. File-descriptor `fstat` could avoid the HEAD read if request volume ever matters; it is irrelevant to animation frame cost. The installed legacy host's separate 0.03% CPU observation also gives no reason to replace it for speed.

Keep the reference image encoder and current small build. Source images total about 3.64 MiB; the static PNG is 2.51 MiB and HTML 0.753 MiB. The package includes authoring assets, while the page embeds only the prepared artwork. A larger source painting would affect decode/build memory and startup, and displayed pixel area scales approximately with DPR squared; it should be measured as a separate change rather than assumed cheap on every supported Mac.

The remaining utilities add no recurring custom workload: `Start.command` waits for a selection and launches one tool; the folder-icon generator draws four fixed 1024-pixel PNGs and exits; the Terminal profile is configuration without an embedded shell command. Their native UI rendering, Finder folder loading and macOS clipboard retention were not individually profiled. No claim is made that cosmetic preferences accelerate the operating system or unrelated apps.

## Ordered follow-up and completion record

1. Fix the reproduced host deadline with focused fake-clock regressions.
2. Apply the direct-screen lookup simplification and verify all dwell guards; measure native event handling before claiming an input-latency gain.
3. Resolve authorized live-render access, establish the comparison above, and test storm modulation and rain/bloom surfaces one change at a time.
4. Change Dock metadata scheduling only after a real slow-preview case. Keep setup durability, the existing host, reference encoding and declarative renderer at the measured scale.

This delivery completes **one improvement**: a documented performance baseline with a repeatable benchmark. It does not count findings as completed repairs. Publish this smaller remainder under the repository delivery cadence.

Validation on the reviewed implementation: full portable checks 12.111 s, Dock checks 0.157 s, edge scenarios 0.006 s, shortcut scenarios 0.004 s; all passed with no skips. These are single suite timings, not statistical benchmarks. Build reproducibility, failure preservation, native-setting fixtures and mocked animation lifecycle checks do not substitute for a live frame trace. The GitHub checks for the reviewed `1626cd7` also passed.

## Reproduce the portable timing baseline

Run with the reference Python/image dependencies already described in [README](../README.md):

```sh
python3 tests/benchmark.py assembly
python3 tests/benchmark.py images
# Explicit read-only native previews, on the receiving Mac:
python3 tests/benchmark.py preferences
python3 tests/benchmark.py dock
python3 tests/benchmark.py discover
```

The [benchmark](../tests/benchmark.py) prints raw samples, warmup, medians, ranges, Python version and wallpaper hash as JSON. Each child has a five-minute outer timeout; `--runs 1` through `--runs 20` adjusts repetition. Builds use temporary output directories and validate the generated result. No services are installed and no native settings are applied. Keep local diagnostic receipts outside the shareable package; comparisons across machines should record OS, power state, display configuration, other workloads and dependency versions.
