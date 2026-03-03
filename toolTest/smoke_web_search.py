from biomni.config import default_config
from biomni.tool.literature import advanced_web_search_model


def main():
    print("Configured model:", default_config.llm)
    result = advanced_web_search_model(
        "CD19 BCMA bispecific antibody B cell depletion",
        max_searches=1,
        max_retries=1,
    )
    print(str(result)[:400])


if __name__ == "__main__":
    main()
