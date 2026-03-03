# Detailed Reasoning Lifecycle (Question -> Final Answer)

This file expands the operational lifecycle with concrete artifacts, control transitions, and failure paths.

## 1) Pre-Query Runtime State

Before first `go()` call, `A1.__init__` has already created:
- `self.module2api`: dictionary mapping 22 tool modules to 224 API schemas.
- `self.llm`: provider-adapted chat model from `get_llm`.
- `self.tool_registry` + `self.retriever` (if retriever enabled; default true).
- `self.know_how_loader.documents`: markdown docs loaded from `biomni/know_how`.
- `self.system_prompt`: generated via `_generate_system_prompt`.
- `self.app`: compiled LangGraph workflow with `generate` and `execute` nodes.

## 2) Query Intake

Input call:
- `A1.go(prompt: str)`

Immediate updates:
- `self.critic_count = 0`
- `self.user_task = prompt`

Artifacts created:
- `inputs = {"messages": [HumanMessage(prompt)], "next_step": None}`
- `config = {"recursion_limit": 500, "configurable": {"thread_id": 42}}`

## 3) Resource Retrieval Stage (Default Path)

Condition:
- runs only if `self.use_tool_retriever` is true.

### 3.1 Build Resource Universe

`_prepare_resources_for_retrieval(prompt)` builds:
- `tools`: full tool registry entries
- `data_lake`: scanned local filenames with descriptions
- `libraries`: env-described software catalog
- `know_how`: doc summaries from loader

### 3.2 Selection LLM Invocation

`ToolRetriever.prompt_based_retrieval` does:
1. Render one long prompt listing every resource with indices.
2. Call `llm.invoke([HumanMessage(prompt)])`.
3. Parse `TOOLS:[...] DATA_LAKE:[...] LIBRARIES:[...] KNOW_HOW:[...]`.
4. Return selected subsets.

### 3.3 Prompt Regeneration

`update_system_prompt_with_selected_resources(selected)`:
- rebuilds `tool_desc` grouped by module
- converts selected data/library items to descriptive lists
- injects selected know-how full content
- writes new `self.system_prompt`

Important: graph object is not recompiled; `generate` closes over `self`, so updated prompt is read dynamically each iteration.

## 4) LangGraph Execution Loop

`for s in self.app.stream(inputs, stream_mode="values", config=config):`
- Each iteration yields updated graph state.
- `message = s["messages"][-1]`
- `pretty_print(message)` appended to `self.log`.
- `final_state = s` retained.

### 4.1 `generate` Node Lifecycle

1. Build message stack:
   - `SystemMessage(self.system_prompt)` + prior conversation
2. LLM call:
   - `response = self.llm.invoke(messages)`
3. Content normalization:
   - supports string or block-list responses
4. Tag parse:
   - `<solution>` -> mark `next_step = end`
   - `<execute>` -> mark `next_step = execute`
   - `<think>` only -> continue generate
5. Parse error policy:
   - inject corrective HumanMessage if no tags
   - after repeated failures, terminate

Produced artifact:
- AIMessage containing model output (or repaired output) appended to state.

### 4.2 Router Transition

`routing_function(state)` returns one of:
- `execute`
- `generate`
- `end`

### 4.3 `execute` Node Lifecycle

1. Extract code from `<execute>` block.
2. Language dispatch:
   - starts with `#!R` -> run R
   - starts with `#!BASH`/`#!CLI` -> run Bash
   - default -> run Python REPL
3. Timeout wrapper:
   - `run_with_timeout(..., timeout=self.timeout_seconds)`
4. Python branch extras:
   - clear prior plot captures
   - inject custom functions into REPL namespace
5. Save execution metadata:
   - triggering message
   - captured images
   - timestamp
6. Append AI observation message:
   - `<observation>...</observation>`

Produced artifacts:
- execution output string
- optional image list
- `_execution_results` entry

### 4.4 Loop Continuation

Control returns to `generate` with appended observation in state.
This repeats until `generate` emits `<solution>`.

## 5) Finalization

After stream completes:
- `self._conversation_state = final_state`
- return `(self.log, message.content)`

`message.content` is the raw final content; downstream callers may parse `<solution>` or display raw.

## 6) Failure Paths and Recovery Behaviors

### Missing Tag Output
- Agent injects correction prompt and re-asks model.
- After repeated parse misses, force stop.

### Code Timeout
- `run_with_timeout` returns timeout error string in observation.
- Loop continues and model can retry with smaller steps.

### Tool Runtime Error
- Python exceptions become observation text (e.g., `Error: ...`).
- Model receives error and can revise strategy.

### Retrieval Failure
- In Gradio path, retrieval failure falls back to broad tool availability.
- In `go()`, retrieval exceptions propagate unless internally handled in called functions.

## 7) Intermediate Artifacts Checklist by Phase

### Input/Planning
- user prompt
- selected resource names (if retriever on)
- regenerated system prompt

### Iterative Reasoning
- AI reasoning text
- execute code blocks
- observations
- execution metadata/images

### Output
- final `<solution>` content
- pretty-printed transcript log
- final graph state

## 8) Why This Lifecycle Is Slow by Construction

1. Query may trigger **pre-loop retrieval LLM** + **multi-turn reasoning LLMs**.
2. Each reasoning turn sends large prompt context repeatedly.
3. Many tools (notably database wrappers) internally perform another LLM call to formulate API requests.
4. All stages are synchronous, serial, and history-accumulating.

This produces high latency even for modest queries and is the root of the observed sequential slowdown.
