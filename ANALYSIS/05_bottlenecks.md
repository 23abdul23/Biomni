# Phase 4: Performance Diagnosis (Sequential Bottlenecks and Cost Drivers)

## Issue Framing

Observed complaint: small queries feel slow because the system performs broad sequential analysis.

Code trace confirms this. Latency is dominated by repeated large-context LLM calls, serial execution, and tool wrappers that themselves invoke LLMs.

---

## Bottleneck Inventory

## 1) Oversized System Prompt Construction

- Where:
  - `A1._generate_system_prompt` (`biomni/agent/a1.py`)
  - tool dictionary from `textify_api_dict` over 224 tools
  - data lake + software lists + know-how docs
- Why slow:
  - every generation turn includes large static context.
- Cost impact estimate:
  - full tool dictionary alone ~35k tokens; with other sections can exceed ~45k tokens before conversation history.
  - if 5 turns: 200k+ repeated input tokens.
- Type: **Architectural** (prompt design) + implementation detail (no compression/caching).

## 2) Retrieval Pre-Call Uses a Huge Prompt

- Where:
  - `ToolRetriever.prompt_based_retrieval` (`biomni/model/retriever.py`)
- Why slow:
  - query-time LLM call enumerates all tools/data/libraries/know-how (~14k token prompt) before main reasoning even begins.
- Cost impact estimate:
  - +1 heavyweight LLM round trip per query; often seconds added even for trivial tasks.
- Type: **Architectural**.

## 3) Multi-Turn ReAct-Style Loop Is Fully Serial

- Where:
  - LangGraph `generate -> execute -> generate` in `a1.py`
- Why slow:
  - no parallel branch execution; each step waits for prior LLM or execution result.
- Cost impact estimate:
  - linear growth with number of turns; 6 turns roughly doubles/triples wall time vs 2 turns.
- Type: **Architectural**.

## 4) Planner Policy Forces Verbose Step Logging

- Where:
  - system prompt instructions mandate plan checklist update every turn.
- Why slow:
  - extra output tokens each iteration; bloats history and next-turn input.
- Cost impact estimate:
  - +100 to +500 tokens/turn depending answer style.
- Type: **Architectural** (prompt policy).

## 5) Tool Layer Frequently Adds Another LLM Call

- Where:
  - `biomni/tool/database.py`: many `query_*` functions call `_query_llm_for_api(...)` first.
- Why slow:
  - one agent call to a tool can become LLM->API chain; nested latency stack.
- Cost impact estimate:
  - per tool invocation: +1 LLM latency + API latency.
  - multi-tool queries become LLM-heavy quickly.
- Type: **Architectural**.

## 6) Repeated Schema File Loads in Tool Calls

- Where:
  - many `query_*` functions do `open(schema_path)` + `pickle.load` every call.
- Why slow:
  - redundant disk I/O and parse overhead for immutable schema data.
- Cost impact estimate:
  - small per call (ms-100ms), significant at scale/high tool-call counts.
- Type: **Implementation-level**.

## 7) No Tool/Response Caching

- Where:
  - no memoization for retrieval output, tool schema loads, or repeated API queries.
- Why slow:
  - repeated identical operations across user sessions/turns.
- Cost impact estimate:
  - repeated calls pay full cost each time.
- Type: **Architectural + Implementation**.

## 8) Blocking Execution Runtime

- Where:
  - `run_with_timeout` uses thread join; tool calls and subprocess operations are blocking.
- Why slow:
  - graph cannot progress while execution runs.
- Cost impact estimate:
  - long tool calls fully stall pipeline.
- Type: **Implementation-level** (execution model).

## 9) Synchronous External HTTP Calls Everywhere

- Where:
  - `requests.get/post` in tools (database/literature/protocols), mostly serial loops.
- Why slow:
  - no async I/O batching; endpoint fan-outs are sequential.
- Cost impact estimate:
  - N API calls => approximately sum of N latencies (instead of max + overhead).
- Type: **Implementation-level**.

## 10) Startup Bootstrap Can Be Massive

- Where:
  - `A1.__init__` checks/downloads data lake + benchmark; up to ~11GB first run.
- Why slow:
  - network + decompression + filesystem I/O before first query.
- Cost impact estimate:
  - minutes to hours depending bandwidth/storage.
- Type: **Architectural** (bootstrap strategy).

## 11) Server Instantiates Agent at Import Time

- Where:
  - `server.py`: global `agent = main()`.
- Why slow:
  - API startup blocked by full agent initialization and possible data checks/downloads.
- Cost impact estimate:
  - cold-start spikes and deployment fragility.
- Type: **Implementation-level** with architectural consequences.

## 12) Large Recursion Limit Without Early-Exit Heuristics

- Where:
  - `go()` uses `recursion_limit=500`.
- Why slow:
  - safeguards are permissive; loops can run many costly turns before stopping.
- Cost impact estimate:
  - worst-case runaway cost/time on malformed trajectories.
- Type: **Architectural policy**.

## 13) Prompt Selection Policy Is Intentionally Over-Inclusive

- Where:
  - retriever instructions: "be generous", "always prioritize many database tools".
- Why slow:
  - selected resource set remains broad, reducing retrieval narrowing effectiveness.
- Cost impact estimate:
  - larger runtime prompt, slower reasoning, higher token spend.
- Type: **Architectural**.

## 14) Potential Provider Adapter Bug

- Where:
  - `biomni/llm.py:38` references `config.llm_model` while config uses `llm`.
- Why it matters:
  - not primary latency cause, but increases runtime risk and fallback complexity.
- Cost impact estimate:
  - indirect (error handling/retries, instability).
- Type: **Implementation-level defect**.

---

## Summary by Severity (for latency)

Highest impact:
1. Massive prompt footprint per turn.
2. Extra retrieval LLM call per query.
3. Serial ReAct loop and serial I/O.
4. Nested LLM-in-tool wrappers.

Moderate impact:
5. No caching.
6. Repeated schema loads.
7. Verbose forced reasoning/checklist output.

Startup/cold-path impact:
8. Data lake bootstrap and eager server init.
