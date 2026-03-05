## A1 Interactive Approval + Query Categorization (Core `go()`)

### Summary

Introduce a **pre-execution query categorization system** and a **pause/resume user-interaction flow** in `A1.go()` so the agent can intelligently decide how to proceed with a request.

The agent should:

* **Run autonomously** when a request is fully actionable.
* **Ask the user for input or approval** in natural language when required.
* **Pause execution** and wait until the user responds before continuing.

This change addresses the current failure mode where **strategy-style prompts lead to empty `<execute>` loops and cause the agent to stall.**

---

# Areas To Modify

### 1. Core Control Loop and Parser

File: `a1.py`

Responsibilities:

* Integrate query categorization
* Handle `<ask_user>` tag parsing
* Support pause/resume execution flow
* Manage pending user interaction state

---

### 2. Configuration and Environment Support

File: `config.py`

Add configuration knobs to control categorization and approval behavior.

---

### 3. Rendering and Parsing Support

File: `utils.py`

Add formatting and parsing utilities for the new `<ask_user>` tag so conversation logs and exported outputs (Markdown/PDF) render pause requests clearly.

---

# Public API / Interface Changes

### `A1.go(prompt)`

**Signature remains unchanged:**

```
(log, answer)
```

No breaking API changes.

### Behavior Changes

The returned `answer` may now include:

```
<ask_user>...</ask_user>
```

This indicates the agent requires **user input or approval before continuing.**

### Resumable Execution

If the agent pauses:

* The **next call to `go(user_reply)` resumes the same task context.**
* The agent continues execution from the paused state.

---

# New Internal State

Extend **AgentState / session memory** with fields to track pending interactions.

Example:

```
pending_interaction: bool
pending_prompt_context: str
pending_category: str
pending_execution_plan: Optional[str]
```

This enables the agent to **resume work after receiving the user’s reply.**

---

# New Configuration Fields

Add to `BiomniConfig`:

| Field                                 | Default | Purpose                                                   |
| ------------------------------------- | ------- | --------------------------------------------------------- |
| `enable_query_categorization`         | `True`  | Enables automatic prompt classification                   |
| `categorization_confidence_threshold` | `0.70`  | Minimum confidence required for categorizer               |
| `require_execution_approval`          | `True`  | Require explicit user approval before expensive execution |
| `enable_user_pause_tag`               | `True`  | Enables `<ask_user>` interaction mechanism                |

Ensure these fields are exposed in:

```
BiomniConfig.to_dict()
```

---

# Prompt Contract Changes

Introduce a **third valid output tag** in the agent response format.

### Supported Tags

| Tag          | Purpose                         |
| ------------ | ------------------------------- |
| `<execute>`  | Run toolchain / execution graph |
| `<solution>` | Provide final answer            |
| `<ask_user>` | Pause and request user input    |

### System Prompt Update (in `a1.py`)

The model must produce **exactly one** of these tags.

Instructions to the model:

* Use `<execute>` when tools or workflows must run.
* Use `<solution>` when the answer can be given directly.
* Use `<ask_user>` when:

  * Inputs are missing
  * Multiple strategies exist
  * Execution requires approval
  * Clarification is needed

---

# Parser Updates (`a1.py`)

Extend the existing tag parser to support `<ask_user>`.

### Behavior

1. Detect `<ask_user>` tags.
2. Auto-close malformed tags if necessary (same recovery logic used for `<execute>`).
3. When `<ask_user>` appears:

```
next_step = "end"
```

This creates a **pause boundary.**

---

### Update “No Tag” Recovery

When the model returns no valid tag, the reminder message should now reference:

```
<execute>
<solution>
<ask_user>
```

---

# Preflight Query Categorization

Add a **categorization stage before execution**.

### Hybrid Approach

1️⃣ **Rule-based detection**

Fast deterministic checks for obvious cases:

Examples:

| Pattern                                | Category                   |
| -------------------------------------- | -------------------------- |
| Missing identifiers (e.g., protein ID) | `needs_user_input`         |
| Strategy or explanation prompt         | `direct_answer_no_execute` |
| Clear execution request                | `autonomous_execute`       |

---

2️⃣ **LLM Fallback**

If rules cannot determine category, ask the LLM to classify:

Possible outputs:

```
autonomous_execute
direct_answer_no_execute
needs_user_input
```

---

### Confidence Handling

If classification confidence < threshold:

```
categorization_confidence_threshold
```

Default to:

```
needs_user_input
```

---

# Approval Gate

Before the **first execution step**, enforce approval if configured.

Condition:

```
require_execution_approval = True
```

Applicable when:

* The plan is expensive
* Multiple strategy options exist
* Execution modifies state or external resources

Agent response:

```
<ask_user>
This request requires running an analysis pipeline.  
Do you want me to proceed?
</ask_user>
```

Execution pauses until approval.

---

# Resumable Interaction Flow

Inside `go()`:

### Case 1 — Pending Interaction Exists

Treat incoming prompt as **user reply**.

Interpret reply intent:

| Reply                   | Action           |
| ----------------------- | ---------------- |
| yes / approve / proceed | Resume execution |
| no / cancel             | Abort            |
| unclear                 | Ask again        |

Example response:

```
<ask_user>
Please confirm whether I should proceed with execution.
</ask_user>
```

---

### Case 2 — No Pending Interaction

Run categorizer and route accordingly.

---

# Direct Answer Path (Skip Execution Graph)

For **strategy-only or explanation queries**:

1. Run a single LLM call.
2. Constrain output to:

```
<solution>
...
</solution>
```

3. Skip graph execution entirely.

---

# Stall Detection Update

Current stall logic counts repeated `<execute>` loops.

New rule:

```
Only <execute> contributes to stall counters.
```

`<ask_user>` responses **must not increment stall counters**.

---

# Formatting Support (`utils.py`)

Add rendering for `<ask_user>` blocks.

Example Markdown output:

```
🔹 USER INPUT REQUIRED

<content>
```

Ensure exported logs clearly show:

* pause points
* user questions
* resume points

---

# Execution Data Flow

### Entry

```
go(prompt)
```

---

### Step 1 — Resume Check

If pending session exists:

```
process user reply
```

---

### Step 2 — Categorization

```
categorize(prompt)
```

Possible results:

* `needs_user_input`
* `direct_answer_no_execute`
* `autonomous_execute`

---

### Step 3 — Routing

#### Case: needs_user_input

```
return <ask_user>
persist pending state
```

---

#### Case: direct_answer_no_execute

```
return <solution>
skip execution graph
```

---

#### Case: autonomous_execute

If approval required:

```
return <ask_user>
```

Otherwise:

```
start execution graph
```

---

### Step 4 — Graph Loop

Graph may output:

```
<execute>
<ask_user>
<solution>
```

Handling:

| Tag          | Behavior                |
| ------------ | ----------------------- |
| `<execute>`  | Continue execution      |
| `<ask_user>` | Pause and persist state |
| `<solution>` | Finish and clear state  |

---

# Test Scenarios

### 1️⃣ Strategy-Only Prompt

Example: protein analysis strategy request.

Expected:

```
<ask_user>
Please provide the protein sequence or UniProt ID.
</ask_user>
```

No `<execute>` loop.

---

### 2️⃣ Missing Critical Input

Agent pauses and waits.

Next call:

```
go("UniProt ID: P12345")
```

Execution resumes.

---

### 3️⃣ Approval Required

Before execution:

```
<ask_user>
Do you want me to proceed with the analysis pipeline?
</ask_user>
```

User replies:

```
yes proceed
```

Execution resumes.

---

### 4️⃣ Fully Actionable Prompt

Agent executes automatically and returns:

```
<solution>
...
</solution>
```

---

### 5️⃣ Ambiguous Prompt

Low classification confidence → ask user to choose.

---

### 6️⃣ Backward Compatibility

Existing consumers still receive:

```
(log, answer)
```

No API breakage.

---

# Outcome

After this change the agent will:

* Avoid **no-op execution loops**
* Handle **missing inputs intelligently**
* Support **human-in-the-loop decisions**
* Provide **deterministic pause/resume behavior**
* Maintain **full backward compatibility**

---
