"""Reproduce the log error: Error: string indices must be integers.

This script mirrors the execute block seen in run.log.
"""

from biomni.tool.database import query_clinicaltrials


def main():
    # Query copied from run.log
    trial_results = query_clinicaltrials("B cell depletion CD19 BCMA bispecific antibody")

    # The function returns a dict like {"success": True, "result": {...}}
    if not trial_results.get("success"):
        print("Query failed:", trial_results.get("error", "Unknown error"))
        return

    # ClinicalTrials.gov API v2 returns studies under result["studies"]
    studies = trial_results.get("result", {}).get("studies", [])

    # Each study is a nested dict with protocolSection, conditionsModule, etc.
    b_cell_depletion_trials = []
    for trial in studies:
        conditions = trial.get("protocolSection", {}).get("conditionsModule", {}).get("conditions", [])
        title = trial.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle", "")
        combined_text = (" ".join(conditions) + " " + title).lower()
        if "b cell depletion" in combined_text:
            b_cell_depletion_trials.append(trial)

    print(f"Found {len(studies)} studies, {len(b_cell_depletion_trials)} matched 'B cell depletion'")
    for t in b_cell_depletion_trials:
        nct_id = t.get("protocolSection", {}).get("identificationModule", {}).get("nctId", "N/A")
        title = t.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle", "N/A")
        print(f"  {nct_id}: {title}")


if __name__ == "__main__":
    main()
