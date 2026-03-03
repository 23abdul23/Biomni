"""Recreate the PubMed tool query from run.log.

This call did not show a Python exception in the log, but is included to reproduce
what the agent executed before the parser-level failure.
"""

from biomni.tool.literature import query_pubmed


def main():
    pubmed_results = query_pubmed("CD19 BCMA bispecific antibody B cell depletion", max_papers=10)
    print("Result type:", type(pubmed_results).__name__)
    print("Result preview:", str(pubmed_results)[:1000])


if __name__ == "__main__":
    main()
