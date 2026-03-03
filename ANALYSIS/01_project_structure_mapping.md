# Biomni Repository Structure Audit

## 1) Project Directory Tree (Root -> Subdirectories -> Key Files)

```text
Biomni/
+-- biomni/
¦   +-- __init__.py
¦   +-- version.py
¦   +-- config.py
¦   +-- llm.py
¦   +-- utils.py
¦   +-- env_desc.py
¦   +-- env_desc_cm.py
¦   +-- agent/
¦   ¦   +-- __init__.py
¦   ¦   +-- a1.py
¦   ¦   +-- react.py
¦   ¦   +-- qa_llm.py
¦   ¦   +-- function_generator.py
¦   ¦   +-- env_collection.py
¦   +-- model/
¦   ¦   +-- __init__.py
¦   ¦   +-- retriever.py
¦   +-- tool/
¦   ¦   +-- __init__.py
¦   ¦   +-- tool_registry.py
¦   ¦   +-- support_tools.py
¦   ¦   +-- literature.py
¦   ¦   +-- database.py
¦   ¦   +-- protocols.py
¦   ¦   +-- biochemistry.py
¦   ¦   +-- bioengineering.py
¦   ¦   +-- bioimaging.py
¦   ¦   +-- biophysics.py
¦   ¦   +-- cancer_biology.py
¦   ¦   +-- cell_biology.py
¦   ¦   +-- genetics.py
¦   ¦   +-- genomics.py
¦   ¦   +-- glycoengineering.py
¦   ¦   +-- immunology.py
¦   ¦   +-- lab_automation.py
¦   ¦   +-- microbiology.py
¦   ¦   +-- molecular_biology.py
¦   ¦   +-- pathology.py
¦   ¦   +-- pharmacology.py
¦   ¦   +-- physiology.py
¦   ¦   +-- synthetic_biology.py
¦   ¦   +-- systems_biology.py
¦   ¦   +-- protocols/
¦   ¦   ¦   +-- addgene/*.txt
¦   ¦   ¦   +-- thermofisher/*.txt
¦   ¦   +-- schema_db/*.pkl
¦   ¦   +-- example_mcp_tools/pubmed_mcp.py
¦   ¦   +-- tool_description/*.py
¦   +-- know_how/
¦   ¦   +-- loader.py
¦   ¦   +-- sgRNA_design_guide.md
¦   ¦   +-- single_cell_annotation.md
¦   ¦   +-- resource/
¦   ¦       +-- addgene_grna_sequences.csv
¦   ¦       +-- CRISPick_download_links.txt
¦   +-- eval/
¦   ¦   +-- __init__.py
¦   ¦   +-- biomni_eval1.py
¦   +-- task/
¦   ¦   +-- __init__.py
¦   ¦   +-- base_task.py
¦   ¦   +-- hle.py
¦   ¦   +-- lab_bench.py
¦   +-- biorxiv_scripts/
¦       +-- extract_biorxiv_tasks.py
¦       +-- generate_function.py
¦       +-- process_all_subjects.py
+-- biomni_env/
¦   +-- README.md
¦   +-- bio_env.yml
¦   +-- environment.yml
¦   +-- fixed_env.yml
¦   +-- req_bio_env.txt
¦   +-- install_cli_tools.sh
¦   +-- setup.sh
¦   +-- install_r_packages.R
¦   +-- cli_tools_config.json
+-- data/
¦   +-- biomni_data/
¦   ¦   +-- data_lake/
¦   ¦   +-- benchmark/
¦   +-- GSE14605/
+-- docs/
¦   +-- configuration.md
¦   +-- mcp_integration.md
¦   +-- known_conflicts.md
¦   +-- generate_api_docs.py
¦   +-- source/
¦       +-- conf.py
¦       +-- index.rst
+-- docker/
¦   +-- entrypoint.sh
+-- tutorials/
¦   +-- biomni_101.ipynb
¦   +-- examples/
¦       +-- add_mcp_server/
¦       +-- expose_biomni_server/
¦           +-- run_mcp_server.py
¦           +-- test_mcp_server.py
+-- toolTest/
¦   +-- smoke_web_search.py
¦   +-- pubmed_query_repro.py
¦   +-- clinicaltrials_string_indices_repro.py
+-- server.py
+-- test_a1_openai.py
+-- README.md
+-- DETAILS.md
+-- pyproject.toml
+-- Dockerfile
+-- docker-compose.yml
+-- .env / .env.example
```

## 2) Folder Purpose + Capability Classification

Legend:
- `Y`: primary responsibility in that folder
- `P`: present/partial (supporting role)
- `N`: not a meaningful responsibility there

| Folder | Purpose | Agent Logic | LLM Interaction | Tool Execution | Retrieval/RAG | Embeddings | API Interface | Data Processing | Prompt Construction | Memory | Evaluation | Configuration |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `biomni/agent` | Core agent orchestration (`A1`, loops, execution routing, MCP integration, UI hooks) | Y | Y | Y | Y | N | P | P | Y | P | N | P |
| `biomni/model` | Retrieval strategy implementation (`ToolRetriever`) | P | Y | N | Y | N | N | N | Y | N | N | N |
| `biomni/tool` | Domain tool functions (bio APIs, analyses, protocol retrieval, code execution helpers) | P | Y (in tool wrappers) | Y | P | P (genomics embedding funcs) | Y | Y | P | P (persistent REPL namespace) | N | P |
| `biomni/tool/tool_description` | Tool schema metadata used in prompts and registry | N | N | N | Y (resource selection corpus) | N | N | N | Y | N | N | P |
| `biomni/tool/schema_db` | Pickled API schemas for LLM-to-API mapping | N | P | N | P | N | N | Y | P | N | N | N |
| `biomni/know_how` | Best-practice/protocol markdown corpus + loader | P | N | N | Y | N | N | Y | Y (injected into prompt) | P | N | N |
| `biomni/eval` | Benchmark evaluation (`BiomniEval1`) | N | N | N | N | N | N | Y | N | N | Y | N |
| `biomni/task` | Task wrappers/datasets for benchmarks | N | N | N | N | N | N | Y | P | N | Y | N |
| `biomni/biorxiv_scripts` | Offline extraction pipelines from papers | P | Y | N | N | N | Y (HTTP PDF pulls) | Y | Y | N | N | N |
| `biomni_env` | Environment/bootstrap scripts and dependency manifests | N | N | N | N | N | N | N | N | N | N | Y |
| `docs` | Documentation and API-doc generator scripts | N | N | N | N | N | N | N | N | N | N | Y |
| `docker` | Container bootstrap | N | N | N | N | N | N | N | N | N | N | Y |
| `tutorials` | Usage notebooks and MCP examples | P | P | P | P | P | P | P | P | N | N | P |
| `toolTest` | Repro/debug scripts for specific tool behaviors | P | P | P | N | N | N | P | N | N | P | N |
| `data` | Runtime data lake + benchmarks cache | N | N | N | Y (retrieval resources) | P | N | Y | N | N | Y | N |

## 3) Key Files and Why They Matter

- `biomni/agent/a1.py`: canonical production agent (`A1`), graph workflow, execution routing, retrieval prep, prompt generation, result logging, Gradio integration.
- `biomni/llm.py`: provider dispatch layer (`OpenAI`, `Anthropic`, `AzureOpenAI`, `Gemini`, `Groq`, `Bedrock`, `Ollama`, `Custom`).
- `biomni/model/retriever.py`: prompt-based resource selector (LLM decides relevant tools/data/libraries/know-how).
- `biomni/utils.py`: runtime primitives (`read_module2api`, timeouts, code parsing helpers, S3 download, formatting).
- `biomni/tool/support_tools.py`: `run_python_repl` persistent execution namespace and plot capture.
- `biomni/tool/database.py`: largest tool module; many wrappers that use an LLM to translate NL -> REST/GraphQL endpoints.
- `biomni/config.py`: global config and env override semantics.
- `server.py`: FastAPI demo/service entry path with global `A1` instance.
- `test_a1_openai.py`: script-level entry path for OpenAI-backed execution testing.

## 4) Entry Points, Runtime Paths, CLI/Server Scripts, Env Usage

### Main Entry Points

1. `from biomni.agent import A1` then `agent = A1(...); agent.go(prompt)` (primary library entry).
2. `server.py` FastAPI app:
   - module import triggers `agent = main()` (instantiates `A1` once globally)
   - `/prompt/{prompt}` calls `agent.go(prompt)`
3. Script entry points:
   - `test_a1_openai.py`
   - `biomni/biorxiv_scripts/*.py`
   - `biomni/eval/biomni_eval1.py` (demo main)
   - `tutorials/examples/expose_biomni_server/run_mcp_server.py`

### Main Runtime Execution Path (primary)

`A1.__init__` -> data/bootstrap checks -> `read_module2api` -> `get_llm` -> optional `ToolRegistry` + `ToolRetriever` -> `KnowHowLoader` -> `configure` (build LangGraph app) -> `A1.go` (optional retrieval + prompt update + graph stream loop).

### CLI/Server Entry Scripts

- Server/API: `server.py` (FastAPI app; expected with `uvicorn server:app`).
- CLI-like scripts:
  - `biomni/biorxiv_scripts/extract_biorxiv_tasks.py`
  - `biomni/biorxiv_scripts/generate_function.py`
  - `biomni/biorxiv_scripts/process_all_subjects.py`
- MCP server exposure: `tutorials/examples/expose_biomni_server/run_mcp_server.py`

### Environment Variable Usage (Observed)

Core LLM/provider:
- `LLM_SOURCE`, `OPENAI_API_KEY`, `OPENAI_ENDPOINT`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `AWS_REGION`

Biomni config:
- `BIOMNI_PATH`, `BIOMNI_DATA_PATH`, `BIOMNI_TIMEOUT_SECONDS`, `BIOMNI_LLM`, `BIOMNI_LLM_MODEL`, `BIOMNI_USE_TOOL_RETRIEVER`, `BIOMNI_COMMERCIAL_MODE`, `BIOMNI_TEMPERATURE`, `BIOMNI_SOURCE`, `BIOMNI_CUSTOM_BASE_URL`, `BIOMNI_CUSTOM_API_KEY`

Tool-specific:
- `PROTOCOLS_IO_ACCESS_TOKEN`, `BIOMNI_PROTOCOLS_IO_ACCESS_TOKEN`, `SYNAPSE_AUTH_TOKEN`, `NCBI_EMAIL`

Container/setup-related:
- `BIOMNI_TOOLS_DIR`, `BIOMNI_AUTO_INSTALL`, proxy vars (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, lowercase variants)

## 5) Architecture-Significant Quantitative Facts

- Tool description modules: `22`
- Tool schemas exposed to agent (`tool_description/*.py`): `224`
- Approx size of full serialized tool dictionary injected into prompt (`textify_api_dict` style):
  - ~`141,387` chars (~`35,347` tokens)
- Data lake entries in `env_desc.py`: `76` (~`1,698` tokens formatted)
- Library entries in `env_desc.py`: `113` (~`3,351` tokens formatted)
- Know-how markdown content (2 docs, stripped approximation): ~`5,275` tokens
- Retrieval selection prompt (all resources enumerated before selection): ~`14,244` tokens

These sizes directly drive latency and cost in the main loop.
