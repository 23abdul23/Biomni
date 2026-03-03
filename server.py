from fastapi import FastAPI
import os
import sys
from types import *

from biomni.agent import A1
app = FastAPI()


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

    return agent 


@app.get("/")
async def root():
    return {"message": "Bimoni Agent Side Here"}

agent  = main()


@app.get("/prompt/{prompt}")
async def generate_responce(prompt: str):
    print("Running agent.go()... this may take a while depending on model latency.")
    log, answer = agent.go(prompt)

    print("\n=== Agent Answer ===\n")
    print(answer)
    return {"responce" : answer}
