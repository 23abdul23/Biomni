# Quick Wins vs Deep Refactors

## Quick Wins (High ROI, Low/Medium Effort)

## Q1) Cache API Schemas in `database.py`
- Change: add module-level `lru_cache` for schema loads.
- Effort: low.
- Risk: low.
- Benefit: removes repeated disk I/O in heavy API tooling.

## Q2) Cap Prompt Size with Budgeted Builder
- Change: enforce token ceiling and prioritized section inclusion.
- Effort: medium.
- Risk: medium (must validate quality impact).
- Benefit: immediate LLM latency and cost reduction.

## Q3) Add Query Router Fast Path
- Change: classify requests into simple/direct/full-agent categories.
- Effort: medium.
- Risk: medium (misrouting risk).
- Benefit: large speedups for straightforward requests.

## Q4) Retrieval Prompt Compression
- Change: short descriptors + top-K prefilter before LLM selection.
- Effort: medium.
- Risk: low/medium.
- Benefit: cuts pre-loop retrieval overhead.

## Q5) Early-Exit Heuristics in Loop
- Change: stop on low-progress patterns and repeated failures.
- Effort: low.
- Risk: low.
- Benefit: prevents runaway turn count.

## Q6) Make Server Lazy-Init Agent
- Change: defer `A1()` construction until first request or startup task.
- Effort: low.
- Risk: low.
- Benefit: improved API cold start behavior.

---

## Deep Refactors (High Impact, Higher Risk)

## R1) Planner-Executor-Critic Architecture
- Replace monolithic generate/execute loop with structured phases.
- Gain: better controllability, fewer redundant turns, easier policy tuning.
- Risk: behavior regression if planning quality drops.

## R2) Direct Tool Invocation Engine
- Introduce deterministic tool dispatch for structured intents.
- Gain: bypass code generation for many tasks.
- Risk: requires robust intent and argument extraction.

## R3) Full Prompt System Redesign
- Separate immutable context from per-query context.
- Gain: dramatic token reduction and better cacheability.
- Risk: initial complexity and migration effort.

## R4) Async Tool Runtime with Parallel I/O
- Convert high-latency tool modules to async with bounded concurrency.
- Gain: major speedup for multi-endpoint queries.
- Risk: error handling and ordering complexity.

## R5) Modularization of `a1.py`
- Split into planner/executor/retrieval/prompt/state modules.
- Gain: maintainability, profiling clarity, easier team development.
- Risk: medium migration effort.

---

## Proposed Execution Sequence

1. Implement all Quick Wins first (Q1-Q6).
2. Measure baseline and post-change metrics:
   - query latency p50/p95
   - tokens per query
   - turns per query
   - tool calls per query
3. Start deep refactors in this order:
   - R5 (modularization foundation)
   - R1 (planner-executor)
   - R2 (direct tool path)
   - R4 (async parallelism)
   - R3 (prompt architecture finalization)

---

## KPI Targets for Production-Grade Readiness

- p50 latency for simple queries: < 5s
- p95 latency for simple queries: < 12s
- average prompt input tokens per turn: < 8k
- average turns per successful query: <= 3
- repeated-query cache hit rate: >= 40%
- tool schema cache hit rate: >= 95%

---

## Risk Controls During Refactor

- Keep current `A1` path behind feature flag (`AGENT_MODE=legacy|optimized`).
- Add golden query set and compare answer quality + tool traces.
- Introduce observability hooks before refactor (timers per stage, token accounting, tool call counters).
- Roll out incrementally with A/B routing.
