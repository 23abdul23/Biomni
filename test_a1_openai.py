"""Quick test: run the A1 agent using an OpenAI Chat model.

This script requires `OPENAI_API_KEY` to be set in the environment (or in
`.env`). It instantiates `A1` with an OpenAI model name (auto-detected by
`biomni.llm.get_llm`) and runs `agent.go()` on a short question.

Run locally with:

    python tests/test_a1_openai.py

Or with the project's python environment activated.
"""
import os
import sys

from biomni.agent import A1


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set. Export your OpenAI key and retry.")
        sys.exit(2)

    # Ensure the agent will use OpenAI by supplying a model name that begins
    # with "gpt-". get_llm() will auto-detect the source as OpenAI.
    model = "gpt-4o-mini"

    print(f"Using model: {model} (OPENAI_API_KEY loaded: {'yes' if api_key else 'no'})")

    agent = A1(path="./data", llm=model)

    prompt = (
        # "Summarize in one paragraph how CRISPR screens can identify genes that regulate T cell exhaustion, and provide a short checklist of experimental controls to include."
        "Look fo indications suitable for B cell depletion based on CD19 and BCMA bispecific antibody or drug"
    )

    print("Running agent.go()... this may take a while depending on model latency.")
    log, answer = agent.go(prompt)

    print("\n=== Agent Answer ===\n")
    print(answer)


if __name__ == "__main__":
    main()
