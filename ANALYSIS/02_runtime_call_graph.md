# Phase 2: Function Call Backtracking and Runtime Trace

## 1) Primary Runtime Entry and Trace Scope

Primary trace starts from:
- `test_a1_openai.py:19` -> `main()` -> `A1(...)` -> `agent.go(prompt)`
- Equivalent server path: `server.py:31` (`A1(...)` in `main`) and `server.py:35` (`agent.go(prompt)` in route handler)

This trace documents the path for one user query through `A1`.

---

## 2) End-to-End Call Graph (Hierarchy Form)

```text
User Query
+- Entry Script / API Route
   +- test_a1_openai.main() OR server.generate_responce()
   +- A1.go(prompt)
      +- [optional] _prepare_resources_for_retrieval(prompt)
      ¦  +- gather tools from ToolRegistry
      ¦  +- scan data_lake directory
      ¦  +- gather libraries from env_desc dict
      ¦  +- gather know-how summaries from KnowHowLoader
      ¦  +- ToolRetriever.prompt_based_retrieval(prompt, resources, llm=self.llm)
      ¦     +- build giant selection prompt listing all resources
      ¦     +- llm.invoke(HumanMessage(selection_prompt))
      ¦     +- _parse_llm_response(...) -> selected indices
      +- [optional] update_system_prompt_with_selected_resources(selected)
      ¦  +- _generate_system_prompt(..., is_retrieval=True)
      +- build graph input
      ¦  +- {messages:[HumanMessage(prompt)], next_step:None}
      +- self.app.stream(inputs, stream_mode="values", config={recursion_limit:500, thread_id:42})
         +- LangGraph StateGraph loop
            +- generate(state)
            ¦  +- messages = [SystemMessage(self.system_prompt)] + state.messages
            ¦  +- self.llm.invoke(messages)
            ¦  +- parse response for <solution>/<execute>/<think>
            ¦  +- set state.next_step in {end, execute, generate}
            ¦  +- append AIMessage to state.messages
            +- routing_function(state)
            ¦  +- if next_step=="execute" -> execute
            ¦  +- if next_step=="generate" -> generate
            ¦  +- if next_step=="end" -> END (or self_critic node in self-critic mode)
            +- execute(state) [only if <execute>]
            ¦  +- extract code from <execute>...</execute>
            ¦  +- language branch:
            ¦  ¦  +- R: run_with_timeout(run_r_code)
            ¦  ¦  +- Bash/CLI: run_with_timeout(run_bash_script)
            ¦  ¦  +- Python: _clear_execution_plots -> _inject_custom_functions_to_repl -> run_with_timeout(run_python_repl)
            ¦  +- truncate result if >10k chars
            ¦  +- append execution metadata (_execution_results)
            ¦  +- append AIMessage(<observation>result</observation>)
            +- loop back to generate until END
```

---

## 3) Initialization Trace (Executed Before Any Query)

`A1.__init__` (`biomni/agent/a1.py:57`):

1. Resolve defaults from `default_config` (`biomni/config.py`).
2. Choose academic/commercial resource dict (`env_desc.py` vs `env_desc_cm.py`).
3. Create data folders under `path/biomni_data/{data_lake,benchmark}`.
4. If `expected_data_lake_files is None`:
   - `check_and_download_s3_files(...)` for data lake files.
   - benchmark folder integrity check and optional benchmark download.
5. `module2api = read_module2api()`:
   - imports 22 `tool_description` modules and loads 224 tool schemas.
6. `self.llm = get_llm(...)`:
   - provider auto-detected or forced by source.
7. If retriever enabled:
   - instantiate `ToolRegistry(module2api)`
   - instantiate `ToolRetriever()`
8. `KnowHowLoader()` loads local markdown know-how docs.
9. `configure()` compiles `StateGraph` app and sets `MemorySaver` checkpointer.

---

## 4) Exact Node-Level Behavior in Query Execution

### Node: `generate` (`a1.py:1381`)

Sequential steps:
1. Build runtime system prompt (`self.system_prompt`; extra OpenAI formatting reminder conditionally appended).
2. Invoke LLM synchronously: `self.llm.invoke(messages)`.
3. Normalize returned content (supports list-of-blocks responses).
4. Parse tags with regex:
   - `<solution>...</solution>` -> set `next_step = end`
   - `<execute>...</execute>` -> set `next_step = execute`
   - `<think>...</think>` only -> `next_step = generate`
5. Error branch:
   - if no valid tags, inject correction HumanMessage and retry.
   - after repeated parse failures, force terminate (`next_step=end`).

### Node: `execute` (`a1.py:1471`)

Sequential steps:
1. Regex extract code between `<execute>` tags.
2. Dispatch by prefix markers:
   - `#!R` -> `run_r_code` (via timeout wrapper)
   - `#!BASH` or `#!CLI` -> `run_bash_script` (via timeout wrapper)
   - default -> `run_python_repl` (persistent namespace)
3. Collect run output and optional plots.
4. Append `<observation>...</observation>` message to graph state.

### Router: `routing_function` (`a1.py:1555`)

Pure state-based branch on `next_step`; no parallelism.

---

## 5) Blocking Operations (Primary Path)

### In Initialization
- S3/data downloads (`check_and_download_s3_files`) are blocking network + file I/O loops.
- Module imports for all tool descriptions are blocking.

### In Query Handling
- Resource retrieval LLM call (`ToolRetriever.prompt_based_retrieval`) is blocking.
- Main reasoning call (`self.llm.invoke`) is blocking every cycle.
- Code execution is blocking (`thread.join(timeout)` in `run_with_timeout`).
- External tools called from executed Python are blocking unless manually parallelized by generated code.

### In Tool Layer (when invoked by executed code)
- `database.py` functions often do:
  - schema file read (`pickle.load`) +
  - `_query_llm_for_api(...)` +
  - outbound REST call(s), all sequential.

---

## 6) Async vs Sequential Behavior

- Main `A1` query path: **sequential**.
- LangGraph nodes execute one step at a time (generate -> execute -> generate ...).
- Tool execution from `execute`: **sequential** (single block per step).
- MCP wrappers use async internals but exposed as sync call wrappers (`asyncio.run` or task creation), so agent-level behavior remains effectively synchronous.

---

## 7) Runtime Trace Example (Step-by-Step)

For one standard query with retriever enabled:

1. `A1.go(prompt)` starts.
2. `_prepare_resources_for_retrieval(prompt)` runs and calls retriever LLM once.
3. `update_system_prompt_with_selected_resources(...)` regenerates system prompt.
4. Graph stream starts with `HumanMessage(prompt)`.
5. `generate` call #1:
   - LLM emits plan + `<execute>...</execute>`.
6. Router sends to `execute`.
7. `execute` runs code block (python/bash/R), appends `<observation>...`.
8. Back to `generate` call #2 with accumulated messages.
9. Repeat until LLM emits `<solution>...</solution>`.
10. Router ends graph.
11. `go()` returns `(self.log, last_message.content)`.

---

## 8) Critical Dynamic Branches

1. **Retriever branch** (`use_tool_retriever`):
   - `True` (default): extra LLM selection call + prompt regeneration each query.
   - `False`: skip retrieval stage.

2. **Execution language branch** in `execute`:
   - Python / R / Bash pathways diverge to different runners.

3. **Parse-recovery branch** in `generate`:
   - malformed model output loops with corrective human message.

4. **Self-critic mode branch** (`configure(self_critic=True)`):
   - injects additional critique rounds (`execute_self_critic`) with extra LLM calls.

---

## 9) Output Formatting Path

- Console/log formatting in core path: `pretty_print(message)` (`utils.py:440`).
- Returned answer in `go()`: raw final message content (often includes `<solution>` tags unless caller strips).
- Rich formatting (execution cards, parsed tags, PDF-friendly markdown) exists in Gradio and `save_conversation_history`, but not in bare `go()` return contract.
