"""Run a Biomni prompt suite and persist prompt + logs + answers per prompt.

Usage:
    python TESTING/run_biomni_prompt_suite.py
    python TESTING/run_biomni_prompt_suite.py --model gpt-4o-mini --outdir TESTING/results

Notes:
- Expects LLM credentials in environment/.env as required by Biomni.
- Reads prompts from TESTING/prompts_biomni_usecases.txt.
- Writes one .txt result file per prompt.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Default agent output directory (change here or via --agent-output-dir CLI).
# All files the agent produces (CSVs, PDFs, images, …) are saved under
# <AGENT_OUTPUT_DIR>/<run_timestamp>/.
# ---------------------------------------------------------------------------
DEFAULT_AGENT_OUTPUT_DIR = "AGENT_OUTPUT"

# Ensure repo root is importable when script is run as: python TESTING/run_biomni_prompt_suite.py
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _normalize_windows_paths(text: str) -> str:
    """Replace Windows backslash paths with forward slashes.

    This prevents the LLM from generating Python code where ``\\U``,
    ``\\G``, etc. are mis-interpreted as escape sequences.
    """
    def _replace(m: re.Match) -> str:
        return m.group(0).replace("\\", "/")

    # Match quoted Windows-style absolute paths (e.g. "C:\Users\...")
    return re.sub(
        r'["\']?[A-Za-z]:\\[^"\'<>\n]+["\']?',
        _replace,
        text,
    )


def load_prompts(prompt_file: Path) -> list[str]:
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    raw = prompt_file.read_text(encoding="utf-8")
    chunks = [c.strip() for c in raw.split("\n\n")]
    prompts = [_normalize_windows_paths(c) for c in chunks if c]
    return prompts


def extract_solution(raw_text: str) -> str:
    if not raw_text:
        return ""
    match = re.search(r"<solution>(.*?)</solution>", raw_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw_text.strip()


def extract_tagged_content(raw_text: str) -> tuple[str, str]:
    """Extract primary tagged content from agent output.

    Returns:
        (tag, content) where tag is one of: "solution", "ask_user", or "raw".
    """
    if not raw_text:
        return "raw", ""

    solution_match = re.search(r"<solution>(.*?)</solution>", raw_text, re.DOTALL | re.IGNORECASE)
    if solution_match:
        return "solution", solution_match.group(1).strip()

    ask_user_match = re.search(r"<ask_user>(.*?)</ask_user>", raw_text, re.DOTALL | re.IGNORECASE)
    if ask_user_match:
        return "ask_user", ask_user_match.group(1).strip()

    return "raw", raw_text.strip()


def is_approval_request(ask_user_text: str) -> bool:
    text = ask_user_text.lower()
    approval_markers = [
        "do you want me to proceed",
        "should i proceed",
        "confirm",
        "approval",
        "go ahead",
        "proceed with execution",
        "proceed with the analysis",
    ]
    return any(marker in text for marker in approval_markers)


def safe_name(index: int, prompt: str) -> str:
    short = "_".join(prompt.strip().split()[:8]).lower()
    short = re.sub(r"[^a-z0-9_]+", "", short)
    short = re.sub(r"_+", "_", short).strip("_")
    if not short:
        short = "prompt"
    return f"{index:02d}_{short}.txt"


def collect_agent_files(
    agent_run_dir: Path,
    *,
    exclude_extensions: set[str] | None = None,
) -> list[Path]:
    """Return a sorted list of files the agent produced in *agent_run_dir*.

    Walks the directory recursively.  Hidden files (starting with '.') and
    files matching *exclude_extensions* are skipped.
    """
    if exclude_extensions is None:
        exclude_extensions = set()
    found: list[Path] = []
    if not agent_run_dir.exists():
        return found
    for p in sorted(agent_run_dir.rglob("*")):
        if p.is_file() and not p.name.startswith(".") and p.suffix.lower() not in exclude_extensions:
            found.append(p)
    return found


def write_result_file(
    output_path: Path,
    *,
    idx: int,
    prompt: str,
    started_at: str,
    ended_at: str,
    elapsed_s: float,
    logs: list[str],
    raw_answer: str,
    parsed_answer: str,
    final_tag: str,
    status: str,
    turns: int,
    error: str | None,
    agent_files: list[Path] | None = None,
) -> None:
    lines: list[str] = []
    lines.append("=" * 80)
    lines.append(f"PROMPT #{idx}")
    lines.append("=" * 80)
    lines.append(f"Started: {started_at}")
    lines.append(f"Ended:   {ended_at}")
    lines.append(f"Elapsed seconds: {elapsed_s:.2f}")
    lines.append(f"Status:  {status}")
    lines.append(f"Final tag: {final_tag}")
    lines.append(f"Turns: {turns}")
    lines.append("")

    lines.append("PROMPT")
    lines.append("-" * 80)
    lines.append(prompt)
    lines.append("")

    if error:
        lines.append("ERROR")
        lines.append("-" * 80)
        lines.append(error)
        lines.append("")

    lines.append("AGENT LOGS")
    lines.append("-" * 80)
    if logs:
        lines.extend(str(item) for item in logs)
    else:
        lines.append("(No logs captured)")
    lines.append("")

    lines.append("RAW FINAL OUTPUT")
    lines.append("-" * 80)
    lines.append(raw_answer if raw_answer else "(Empty)")
    lines.append("")

    lines.append("PARSED ANSWER")
    lines.append("-" * 80)
    lines.append(parsed_answer if parsed_answer else "(Empty)")
    lines.append("")

    lines.append("AGENT OUTPUT FILES")
    lines.append("-" * 80)
    if agent_files:
        for af in agent_files:
            lines.append(str(af))
    else:
        lines.append("(No files produced)")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_suite(args: argparse.Namespace) -> int:
    try:
        from biomni.agent import A1
    except ModuleNotFoundError as e:
        print(f"Missing dependency while importing Biomni: {e}")
        print("Use your Biomni environment (with required packages) to run this script.")
        return 3

    prompt_file = Path(args.prompt_file)
    prompts = load_prompts(prompt_file)

    if len(prompts) == 0:
        print(f"No prompts found in {prompt_file}")
        return 2

    outdir = Path(args.outdir)
    run_ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = outdir / f"run_{run_ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # --- Agent output directory (for CSVs, PDFs, images, etc.) ---------------
    agent_output_base = Path(args.agent_output_dir).resolve()
    agent_run_dir = agent_output_base / f"run_{run_ts}"
    agent_run_dir.mkdir(parents=True, exist_ok=True)
    original_cwd = Path.cwd()

    print(f"Loaded {len(prompts)} prompts from: {prompt_file}")
    print(f"Saving results under: {run_dir}")
    print(f"Agent output files:   {agent_run_dir}")

    # Resolve data_path to absolute *before* any chdir.
    abs_data_path = str(Path(args.data_path).resolve())

    agent = A1(
        path=abs_data_path,
        llm=args.model,
        source=args.source,
        use_tool_retriever=(not args.disable_tool_retriever),
        timeout_seconds=args.timeout_seconds,
        expected_data_lake_files=[] if args.skip_data_download else None,
    )

    summary_lines: list[str] = []
    summary_lines.append("prompt_index\tstatus\tfinal_tag\tturns\toutput_file\terror")

    for i, prompt in enumerate(prompts, start=1):
        started = dt.datetime.now()
        started_s = started.isoformat(timespec="seconds")

        print(f"[{i}/{len(prompts)}] Running prompt...")

        logs: list[str] = []
        raw_answer = ""
        parsed_answer = ""
        final_tag = "raw"
        turns = 0
        error_text: str | None = None

        try:
            # Change into the agent output directory so any files the LLM
            # code writes (e.g. df.to_csv, plt.savefig) land there.
            os.chdir(agent_run_dir)

            aggregated_logs: list[str] = []
            current_input = prompt
            status = "incomplete"

            for turn in range(1, args.max_turns + 1):
                step_logs, raw_answer = agent.go(current_input)
                turns = turn

                if step_logs:
                    aggregated_logs.extend(step_logs)
                else:
                    aggregated_logs.append("(No logs captured for this turn)")

                final_tag, tagged_content = extract_tagged_content(raw_answer)
                parsed_answer = tagged_content

                if final_tag == "solution":
                    status = "ok"
                    break

                if final_tag == "ask_user":
                    if args.auto_approve and is_approval_request(tagged_content):
                        current_input = args.approval_reply
                        continue
                    if args.interactive:
                        print(f"\n\U0001f916 Agent asks:\n{tagged_content}")
                        print("(Type your reply, or 'skip' to move to the next prompt)")
                        user_reply = input("> ").strip()
                        if user_reply.lower() == "skip":
                            status = "skipped"
                            break
                        current_input = user_reply
                        continue
                    status = "pending_user_input"
                    break

                status = "incomplete"
                break

            if status == "incomplete" and final_tag == "ask_user":
                status = "pending_user_input"

            # Avoid pending-state leakage across prompts when unresolved
            # Only cancel if we are NOT in interactive mode (interactive mode
            # already resolved the ask_user via stdin or explicit 'skip').
            if (
                status == "pending_user_input"
                and not args.interactive
                and getattr(agent, "_pending_interaction", False)
            ):
                try:
                    agent.go("cancel")
                except Exception:
                    pass

            logs = aggregated_logs
        except Exception:
            error_text = traceback.format_exc()
            status = "error"
        finally:
            # Always restore working directory so log-file writes and the
            # next prompt iteration start from the original location.
            os.chdir(original_cwd)

        ended = dt.datetime.now()
        ended_s = ended.isoformat(timespec="seconds")
        elapsed = (ended - started).total_seconds()

        # Collect every file the agent produced during this prompt.
        agent_files = collect_agent_files(agent_run_dir)

        filename = safe_name(i, prompt)
        result_path = run_dir / filename

        write_result_file(
            result_path,
            idx=i,
            prompt=prompt,
            started_at=started_s,
            ended_at=ended_s,
            elapsed_s=elapsed,
            logs=logs,
            raw_answer=raw_answer,
            parsed_answer=parsed_answer,
            final_tag=final_tag,
            status=status,
            turns=turns,
            error=error_text,
            agent_files=agent_files,
        )

        summary_lines.append(
            f"{i}\t{status}\t{final_tag}\t{turns}\t{result_path.name}\t{(error_text.splitlines()[-1] if error_text else '')}"
        )
        if agent_files:
            print(f"    📂 {len(agent_files)} output file(s) in {agent_run_dir}")
        print(f"[{i}/{len(prompts)}] {status.upper()} -> {result_path.name}")

    summary_path = run_dir / "summary.tsv"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"Run summary saved: {summary_path}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Biomni against a suite of prompts and persist logs/answers.")
    parser.add_argument(
        "--prompt-file",
        default="TESTING/prompts_biomni_usecases.txt",
        help="Path to prompts file (blank-line separated prompts).",
    )
    parser.add_argument(
        "--outdir",
        default="TESTING/results",
        help="Base output directory. A timestamped run folder is created inside.",
    )
    parser.add_argument("--model", default=None, help="LLM model for Biomni (defaults to Biomni config).")
    parser.add_argument("--source", default=None, help="Optional provider source override.")
    parser.add_argument("--data-path", default="./data", help="Biomni data path.")
    parser.add_argument("--timeout-seconds", type=int, default=1200, help="Per execution timeout passed to Biomni.")
    parser.add_argument(
        "--disable-tool-retriever",
        action="store_true",
        help="Disable Biomni tool retrieval to reduce run overhead.",
    )
    parser.add_argument(
        "--skip-data-download",
        action="store_true",
        default=True,
        help="Skip datalake auto-download in A1 init (default: enabled).",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=3,
        help="Maximum go() turns per prompt (for ask_user pause/resume flow).",
    )
    parser.add_argument(
        "--auto-approve",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Auto-reply to approval-style <ask_user> prompts (default: true).",
    )
    parser.add_argument(
        "--approval-reply",
        default="yes proceed",
        help="Reply text sent when --auto-approve handles approval prompts.",
    )
    parser.add_argument(
        "--interactive",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Prompt for user input when the agent asks a non-approval question "
        "(default: true). Use --no-interactive for fully unattended runs.",
    )
    parser.add_argument(
        "--agent-output-dir",
        default=DEFAULT_AGENT_OUTPUT_DIR,
        help=f"Base directory for agent-produced files (CSVs, PDFs, images, …). "
        f"A timestamped sub-folder is created per run. (default: {DEFAULT_AGENT_OUTPUT_DIR})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    exit_code = run_suite(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
