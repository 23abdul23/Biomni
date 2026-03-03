# Phase 5: Optimization Strategy and Ranked Roadmap

## Impact Ranking (Highest First)

1. **Prompt footprint reduction + context budgeting**
2. **Two-stage query router (fast path vs full agent path)**
3. **Cache immutable and repeated operations (retrieval, schemas, tool outputs)**
4. **Remove nested LLM calls in database tools where possible**
5. **Async/parallel external API fan-out**
6. **Planner-executor refactor with strict early stopping**

---

## A) Architectural Improvements

## A1) Query Classification Router (Fast Path)

### Problem
Everything goes through heavy ReAct pipeline.

### Solution
Add a lightweight classifier before `A1.go` to route:
- `direct_tool_call`
- `short_answer_no_code`
- `full_agent_loop`

### Implementation Sketch

```python
mode = classify_query(prompt)  # cheap model or rules
if mode == "short_answer_no_code":
    return small_llm_answer(prompt)
elif mode == "direct_tool_call":
    return deterministic_tool_path(prompt)
else:
    return a1_full_loop(prompt)
```

### Expected Improvement
- Typical lightweight queries: **2x to 6x** faster.

---

## A2) Prompt Budgeting + Section Gating

### Problem
Large static sections are always injected.

### Solution
Build prompt as composable sections with hard token budgets and drop-order.

### Implementation Sketch

```python
sections = [core_instructions, selected_tools, selected_data, selected_libs, selected_knowhow]
prompt = build_until_budget(sections, max_tokens=8000, priority_order=[core, tools, data, knowhow])
```

### Expected Improvement
- LLM latency and cost drop: **30% to 70%** depending query.

---

## A3) Early-Stopping Policy

### Problem
Loop can run many turns (`recursion_limit=500`) without aggressive convergence checks.

### Solution
Add convergence detector:
- stop when no new entities/tools touched for N steps
- stop when last 2 observations are semantically unchanged
- max execute steps by task class

### Expected Improvement
- Multi-turn tasks: **20% to 50%** fewer turns.

---

## A4) Lazy Data Bootstrap

### Problem
Potentially large data initialization on startup.

### Solution
Do not check/download full data lake in `__init__` by default; fetch-on-first-tool-use.

### Expected Improvement
- Cold start: from minutes to seconds for non-data-lake tasks.

---

## B) LLM Usage Optimization

## B1) Retrieval Call Compression

### Problem
Resource selection prompt is very large.

### Solution
Use compact metadata for retrieval (name + 1 short tag) instead of full descriptions.

### Expected Improvement
- retrieval call input size down ~50% to 80%; call latency down **1.5x to 3x**.

---

## B2) Model Tiering

### Strategy
- cheap model: query classification + resource retrieval + schema mapping
- strong model: final multi-step reasoning only when needed

### Expected Improvement
- blended cost reduction **30% to 70%**, speedup **1.3x to 2.5x**.

---

## B3) Structured Output Everywhere Feasible

### Problem
Tag parsing retries add turns.

### Solution
Use strict structured responses (`mode={plan|execute|solution}` payload) where provider supports it.

### Expected Improvement
- parse-error retries near zero, **10% to 25%** faster on unstable prompts.

---

## B4) Reduce Chain Depth in Tools

### Problem
Tool wrappers invoke LLM to form API endpoints.

### Solution
For common APIs, replace NL->endpoint LLM with deterministic mappers/templates.

### Expected Improvement
- per tool call latency reduction: **1 LLM round-trip removed**.

---

## C) Retrieval & Embedding Optimization

## C1) Pre-Indexed Resource Catalog

### Problem
Selection prompt enumerates large textual catalogs each query.

### Solution
Precompute vector index for tools/data/libraries/know-how using short descriptions.
Retrieve top-K candidates first, then optionally run tiny reranker LLM.

### Expected Improvement
- retrieval stage speedup **2x to 10x**.

---

## C2) Top-K Narrowing by Domain Tags

### Problem
Over-inclusive retrieval policy keeps too many tools.

### Solution
Introduce domain tags and hard caps:
- e.g., `database<=12`, `literature<=4`, `genomics<=8` unless explicitly expanded.

### Expected Improvement
- runtime prompt size down **30% to 60%**.

---

## C3) Embedding Reuse for Repeated Queries

### Problem
No cache for semantically similar query routing.

### Solution
Cache nearest-neighbor retrieval outputs by query embedding hash.

### Expected Improvement
- repeated workloads: retrieval stage near-instant.

---

## D) Execution Optimization

## D1) Cache Schema Loads in `database.py`

### Problem
Repeated `pickle.load(schema)` every query function call.

### Solution
Module-level LRU cache.

### Pseudocode

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def load_schema(name):
    with open(path(name), "rb") as f:
        return pickle.load(f)
```

### Expected Improvement
- Tool-call throughput improvement **5% to 20%** in schema-heavy flows.

---

## D2) Async HTTP Clients for Fan-Out Calls

### Problem
Sequential `requests` calls for multi-endpoint workflows.

### Solution
Use `httpx.AsyncClient` with bounded concurrency.

### Expected Improvement
- multi-call endpoints: **2x to 5x** latency reduction.

---

## D3) Memoize Tool Outputs by Normalized Args

### Problem
Identical tool requests recompute each time.

### Solution
Hash `(tool_name, normalized_args)` with TTL cache.

### Expected Improvement
- repeated user interactions: near-zero repeated latency.

---

## D4) Short-Circuit Execution on Deterministic Errors

### Problem
Loop may keep retrying on permanent failures (missing token/package).

### Solution
Classify errors into transient/permanent; immediately produce remediation summary for permanent class.

### Expected Improvement
- failed trajectories shortened by **30% to 80%**.

---

## E) Refactor Recommendations

## E1) Split `a1.py` into Components

Suggested modules:
- `planner.py` (LLM planning + step policy)
- `executor.py` (python/r/bash runtime and safety)
- `resource_selector.py` (retrieval/indexing)
- `prompt_builder.py` (budgeted prompt assembly)
- `session_store.py` (state and execution artifacts)

Benefits:
- testability, profiling granularity, easier incremental optimization.

---

## E2) Planner-Executor Pattern (Replace monolithic loop)

### Current
Single model does planning + coding + adaptation every turn.

### Proposed
1. Planner produces compact executable step plan.
2. Executor runs step and records structured observation.
3. Critic decides continue/stop.

### Pseudocode

```python
plan = planner.make_plan(query, resources)
for step in plan:
    obs = executor.run(step)
    verdict = critic.evaluate(step, obs)
    if verdict.stop:
        break
    if verdict.replan:
        plan = planner.replan(plan, obs)
```

### Expected Improvement
- fewer unnecessary turns, better controllability, **1.5x to 3x** speedup on complex tasks.

---

## E3) Direct Tool Invocation Path for Structured Tasks

### Problem
Code-generation indirection is expensive when direct invocation is enough.

### Solution
When intent maps cleanly to known tool signatures, bypass REPL code generation and call tool directly.

### Expected Improvement
- single-tool tasks often **2x to 8x** faster.

---

## Recommended Rollout Plan

## Wave 1 (1-2 weeks, low risk)
1. Schema caching in `database.py`.
2. Prompt budgeting and section gating.
3. Early-stop heuristics.
4. Retrieval compact metadata mode.

## Wave 2 (2-4 weeks, medium risk)
1. Query router fast-path.
2. Model tiering.
3. Tool output memoization.
4. Async API fan-out in high-traffic tools.

## Wave 3 (4-8+ weeks, high impact)
1. Planner-executor refactor.
2. Direct invocation path for deterministic tool intents.
3. Full modularization of `a1.py`.

---

## Expected End-State Performance Envelope

If Waves 1-3 are implemented together:
- small/simple queries: **3x to 10x faster**
- typical mixed queries: **2x to 5x faster**
- token spend per query: **40% to 80% lower** depending mode mix
- cold start responsiveness: drastically improved with lazy bootstrap
