# Phase 3: Agent Architecture Analysis

## 1) Framework and Agent Pattern

### Framework Stack
- Orchestration: `langgraph` (`StateGraph`, `START`, `END`, compiled app stream)
- Messaging/prompts: `langchain_core` messages and prompts
- Model adapters: provider-specific LangChain chat wrappers in `biomni/llm.py`
- Execution: custom code execution loop (`<execute>` tags + Python/R/Bash runners)

### Agent Style
- **Custom iterative tool-use loop** (not OpenAI function-calling in the main `A1` path).
- Behavior resembles ReAct, but tools are called indirectly by executing generated code blocks in a REPL, not direct tool-calling APIs.

---

## 2) Text Architecture Diagram

```text
                           +-----------------------------------+
User / API Route ----------> Entry Script / Endpoint           |
                           | (test_a1_openai.py, server.py)   |
                           +----------------+------------------+
                                            |
                                            v
                           +-----------------------------------+
                           | A1 Agent (biomni/agent/a1.py)     |
                           |-----------------------------------|
                           | Init:                             |
                           | - config/env resolve              |
                           | - data lake/benchmark bootstrap   |
                           | - tool schema load (module2api)   |
                           | - LLM binding                     |
                           | - know-how load                   |
                           | - LangGraph compile               |
                           +----------------+------------------+
                                            |
                                  go(prompt)|
                                            v
                           +-----------------------------------+
                           | Retrieval Gate (optional)         |
                           | ToolRetriever.prompt_based...     |
                           | - LLM selects tools/data/libs/docs|
                           | - system prompt regenerated       |
                           +----------------+------------------+
                                            |
                                            v
                           +-----------------------------------+
                           | LangGraph Loop                    |
                           |-----------------------------------|
                           | generate -> router -> execute     |
                           |   ^                         |      |
                           |   +-------------------------+      |
                           +----------------+------------------+
                                            |
                 +--------------------------+--------------------------+
                 |                                                     |
                 v                                                     v
+-----------------------------------+                     +-----------------------------+
| generate node                     |                     | execute node                |
| - LLM invoke (full prompt+history)|                     | - parse <execute> code      |
| - parse tags                      |                     | - python/r/bash dispatch    |
| - choose next_step                |                     | - run_with_timeout          |
+----------------+------------------+                     | - append <observation>      |
                 |                                        +-------------+---------------+
                 |                                                      |
                 +----------------------------> back to generate <------+
                                            |
                                            v
                           +-----------------------------------+
                           | END when <solution> appears       |
                           | return (log, last_message.content)|
                           +-----------------------------------+
```

---

## 3) Reasoning Lifecycle (Question -> Final Answer)

1. **Query intake**
   - `A1.go(prompt)` sets task fields (`critic_count`, `user_task`).

2. **Resource narrowing (default enabled)**
   - Build resource inventory from:
     - 224 tool schemas
     - data lake files + descriptions
     - 113 library descriptions
     - know-how doc summaries
   - Ask LLM to select relevant indices.
   - Regenerate runtime system prompt with selected resources.

3. **Iterative reasoning loop**
   - `generate`: model produces either executable code or final answer.
   - `execute`: if code, run in environment and append observation.
   - Continue until `generate` emits `<solution>`.

4. **Output finalization**
   - `go()` logs pretty-printed messages and returns final message content.

---

## 4) Intermediate Artifacts Produced During One Query

- `selected_resources_names` dict with chosen tool/data/library/know-how.
- `self.system_prompt` string (large, regenerated).
- `state["messages"]` graph transcript:
  - Human task
  - AI reasoning+execute blocks
  - Observation blocks
  - Final solution block
- `self.log` pretty-printed render list.
- `self._conversation_state` final LangGraph state snapshot.
- `self._execution_results` entries with execution metadata + captured images.

---

## 5) Tool Decision Logic (Where/How)

Tool choice is made in two layers:

1. **Pre-selection layer**: `ToolRetriever.prompt_based_retrieval` selects candidate resources (LLM-based index selection).
2. **In-loop layer**: reasoning model decides what code to emit in `<execute>`; that code imports/calls tools.

So the main planner does not call `tool.invoke(...)` directly; it writes code that calls Python functions.

---

## 6) Memory Model

- Conversation context in-graph: carried in `messages` state.
- Runtime log memory: `self.log` and `_conversation_state` retained after call.
- Execution memory: persistent Python namespace in `run_python_repl` (`_persistent_namespace`) survives across code executions and queries.
- Checkpointing: `MemorySaver` is attached post-compile; runtime uses fixed `thread_id=42` in config. Intended session memory exists, but behavior is non-standard vs compile-time checkpointer injection.

Net result: **partially stateful** (especially REPL variable persistence), not purely stateless.

---

## 7) Stop Conditions

Loop exits when `generate` sets `next_step = end`, primarily on detection of `<solution>` tag.

Secondary forced stop:
- repeated malformed responses (missing required tags) trigger termination after correction attempts.

Additional hard cap:
- graph stream config uses `recursion_limit=500`.

---

## 8) Sequential vs Parallel Analysis

- Main lifecycle is sequential.
- No parallel tool scheduling in agent core.
- No concurrent API fan-out in retrieval/tool selection.
- Only async surfaces are MCP internals; agent-facing flow still waits synchronously.

---

## 9) Architectural Risks Observed During Trace

1. Prompt-heavy design: large static context inserted repeatedly.
2. Double-LLM pattern for many tool calls:
   - one LLM for agent reasoning
   - additional LLM inside many database tools for endpoint generation.
3. Coupling:
   - prompt construction, planning policy, execution dispatch, visualization, and persistence all concentrated in `a1.py`.
4. Hidden state in persistent REPL can leak across tasks.

These risks feed directly into performance bottlenecks documented in the next phase.
