# SPEC-7 — Performance & Scale

| | |
|---|---|
| **Status** | Draft |
| **Depends on** | S1–S5 |
| **Blocks** | — |
| **Milestone** | M4 |

## 1. Goal

Ensure ingesting a **large document corpus** (thousands–tens of thousands of files) doesn't crash,
doesn't blow up RAM, and has good throughput. Optimization is a cross-cutting requirement; this
spec gathers the scale decisions in one place.

## 2. Scope

**In scope**: lazy/streaming, parallel batch, caching, benchmark & performance budget.
**Out of scope**: multi-machine distribution (future); here we focus on efficient single-machine.

## 3. Epics & Tasks

### E7.1 — Lazy / streaming
- **T7.1.1** Read large files page/sheet at a time, without loading everything into RAM.
- **T7.1.2** `load_batch` returns an iterator/generator (yields per file) instead of collecting all.
- **T7.1.3** Release engine resources (close handles, temp files) at the right time.

### E7.2 — Parallel batch
- **T7.2.1** Process/thread pool for many files (chosen by CPU-bound vs IO-bound).
- **T7.2.2** Backpressure & configurable concurrency limit.
- **T7.2.3** Error isolation: one failing file doesn't sink the whole batch (ties to S1 partial policy).

### E7.3 — Caching
- **T7.3.1** Cache by **content hash** → skip re-parsing unchanged files.
- **T7.3.2** Pluggable cache store (memory/disk); invalidation by pipeline version.

### E7.4 — Benchmark & budget
- **T7.4.1** Throughput benchmark (files/sec) + memory profiling per format.
- **T7.4.2** Set a **performance budget**; CI warns on regressions beyond threshold.
- **T7.4.3** Tuning guide (concurrency, OCR DPI vs speed).

## 4. Acceptance Criteria
- [ ] Parsing a large file (e.g. a few-hundred-page PDF) stays within the set RAM budget.
- [ ] `load_batch` processes thousands of files in streaming mode with stable RAM (not linear in
  file count).
- [ ] Cache hits correctly skip re-parsing (test with repeated files).
- [ ] Benchmarks have a baseline; CI detects performance regressions.

## 5. Design decisions
- **Streaming-first** for batch: iterator instead of list to keep RAM flat.
- Cache by content hash (not path) → safe across renames/moves.
- Configurable concurrency; safe default (don't saturate the user's machine).

## 6. Risks
- OCR is very CPU/time-intensive. *Mitigation:* dedicated concurrency for OCR, document the DPI
  trade-off.
- Some engines are not thread-safe. *Mitigation:* prefer a process pool for risky engines.
