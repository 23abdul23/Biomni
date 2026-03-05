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
import re
import sys
import traceback
from pathlib import Path

# Ensure repo root is importable when script is run as: python TESTING/run_biomni_prompt_suite.py
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_prompts(prompt_file: Path) -> list[str]:
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    raw = prompt_file.read_text(encoding="utf-8")
    chunks = [c.strip() for c in raw.split("\n\n")]
    prompts = [c for c in chunks if c]
    return prompts


def extract_solution(raw_text: str) -> str:
    if not raw_text:
        return ""
    match = re.search(r"<solution>(.*?)</solution>", raw_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw_text.strip()


def safe_name(index: int, prompt: str) -> str:
    short = "_".join(prompt.strip().split()[:8]).lower()
    short = re.sub(r"[^a-z0-9_]+", "", short)
    short = re.sub(r"_+", "_", short).strip("_")
    if not short:
        short = "prompt"
    return f"{index:02d}_{short}.txt"


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
    error: str | None,
) -> None:
    lines: list[str] = []
    lines.append("=" * 80)
    lines.append(f"PROMPT #{idx}")
    lines.append("=" * 80)
    lines.append(f"Started: {started_at}")
    lines.append(f"Ended:   {ended_at}")
    lines.append(f"Elapsed seconds: {elapsed_s:.2f}")
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

    print(f"Loaded {len(prompts)} prompts from: {prompt_file}")
    print(f"Saving results under: {run_dir}")

    agent = A1(
        path=args.data_path,
        llm=args.model,
        source=args.source,
        use_tool_retriever=(not args.disable_tool_retriever),
        timeout_seconds=args.timeout_seconds,
        expected_data_lake_files=[] if args.skip_data_download else None,
    )

    summary_lines: list[str] = []
    summary_lines.append("prompt_index\tstatus\toutput_file\terror")

    for i, prompt in enumerate(prompts, start=1):
        started = dt.datetime.now()
        started_s = started.isoformat(timespec="seconds")

        print(f"[{i}/{len(prompts)}] Running prompt...")

        logs: list[str] = []
        raw_answer = ""
        parsed_answer = ""
        error_text: str | None = None

        try:
            logs, raw_answer = agent.go(prompt)
            parsed_answer = extract_solution(raw_answer)
            status = "ok"
        except Exception:
            error_text = traceback.format_exc()
            status = "error"

        ended = dt.datetime.now()
        ended_s = ended.isoformat(timespec="seconds")
        elapsed = (ended - started).total_seconds()

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
            error=error_text,
        )

        summary_lines.append(f"{i}\t{status}\t{result_path.name}\t{(error_text.splitlines()[-1] if error_text else '')}")
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    exit_code = run_suite(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
