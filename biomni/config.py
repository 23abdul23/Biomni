"""
Biomni Configuration Management

Simple configuration class for centralizing common settings.
Maintains full backward compatibility with existing code.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load .env file so API keys are available even outside the agent
load_dotenv(".env", override=False)


@dataclass
class BiomniConfig:
    """Central configuration for Biomni agent.

    All settings are optional and have sensible defaults.
    API keys are still read from environment variables to maintain
    compatibility with existing .env file structure.

    Usage:
        # Create config with defaults
        config = BiomniConfig()

        # Override specific settings
        config = BiomniConfig(llm="gpt-4o", timeout_seconds=1200)

        # Modify after creation
        config.path = "./custom_data"
    """

    # Data and execution settings
    path: str = "./data"
    timeout_seconds: int = 600

    # LLM settings (API keys still from environment)
    llm: str = "gpt-4o"
    temperature: float = 0.7

    # Tool settings
    use_tool_retriever: bool = True

    # Data licensing settings
    commercial_mode: bool = False  # If True, excludes non-commercial datasets

    # Custom model settings (for custom LLM serving)
    base_url: str | None = None
    api_key: str | None = None  # Only for custom models, not provider API keys

    # LLM source (auto-detected if None)
    source: str | None = None

    # Prompt budgeting settings
    prompt_token_budget: int = 12000
    max_tool_desc_tokens: int = 6000
    max_data_lake_tokens: int = 2000
    max_library_tokens: int = 1500
    max_knowhow_tokens: int = 2000
    compact_tool_descriptions: bool = True  # Use compact mode in textify_api_dict

    # Early-stop heuristics
    max_agent_steps: int = 15  # Logical iteration cap (not graph transitions)
    max_consecutive_errors: int = 3  # Stop after N identical consecutive errors
    stall_detection_window: int = 3  # Compare last N outputs for stall detection

    # Retrieval settings
    retrieval_compact_mode: bool = True  # Use compact metadata in retrieval prompt

    # Query categorization and user interaction settings
    enable_query_categorization: bool = True  # Enables automatic prompt classification
    categorization_confidence_threshold: float = 0.70  # Minimum confidence for categorizer
    require_execution_approval: bool = True  # Require user approval before expensive execution
    enable_user_pause_tag: bool = True  # Enables <ask_user> interaction mechanism

    # Third-party integrations
    protocols_io_access_token: str | None = None

    def __post_init__(self):
        """Load any environment variable overrides if they exist."""
        # Check for environment variable overrides (optional)
        # Support both old and new names for backwards compatibility
        if os.getenv("BIOMNI_PATH") or os.getenv("BIOMNI_DATA_PATH"):
            self.path = os.getenv("BIOMNI_PATH") or os.getenv("BIOMNI_DATA_PATH")
        if os.getenv("BIOMNI_TIMEOUT_SECONDS"):
            self.timeout_seconds = int(os.getenv("BIOMNI_TIMEOUT_SECONDS"))
        if os.getenv("BIOMNI_LLM") or os.getenv("BIOMNI_LLM_MODEL"):
            self.llm = os.getenv("BIOMNI_LLM") or os.getenv("BIOMNI_LLM_MODEL")
        if os.getenv("BIOMNI_USE_TOOL_RETRIEVER"):
            self.use_tool_retriever = os.getenv("BIOMNI_USE_TOOL_RETRIEVER").lower() == "true"
        if os.getenv("BIOMNI_COMMERCIAL_MODE"):
            self.commercial_mode = os.getenv("BIOMNI_COMMERCIAL_MODE").lower() == "true"
        if os.getenv("BIOMNI_TEMPERATURE"):
            self.temperature = float(os.getenv("BIOMNI_TEMPERATURE"))
        if os.getenv("BIOMNI_CUSTOM_BASE_URL"):
            self.base_url = os.getenv("BIOMNI_CUSTOM_BASE_URL")
        if os.getenv("BIOMNI_CUSTOM_API_KEY"):
            self.api_key = os.getenv("BIOMNI_CUSTOM_API_KEY")
        if os.getenv("BIOMNI_SOURCE"):
            self.source = os.getenv("BIOMNI_SOURCE")

        # Prompt budgeting overrides
        if os.getenv("BIOMNI_PROMPT_TOKEN_BUDGET"):
            self.prompt_token_budget = int(os.getenv("BIOMNI_PROMPT_TOKEN_BUDGET"))
        if os.getenv("BIOMNI_COMPACT_TOOL_DESCRIPTIONS"):
            self.compact_tool_descriptions = os.getenv("BIOMNI_COMPACT_TOOL_DESCRIPTIONS").lower() == "true"

        # Early-stop overrides
        if os.getenv("BIOMNI_MAX_AGENT_STEPS"):
            self.max_agent_steps = int(os.getenv("BIOMNI_MAX_AGENT_STEPS"))
        if os.getenv("BIOMNI_MAX_CONSECUTIVE_ERRORS"):
            self.max_consecutive_errors = int(os.getenv("BIOMNI_MAX_CONSECUTIVE_ERRORS"))

        # Retrieval overrides
        if os.getenv("BIOMNI_RETRIEVAL_COMPACT_MODE"):
            self.retrieval_compact_mode = os.getenv("BIOMNI_RETRIEVAL_COMPACT_MODE").lower() == "true"

        # Query categorization overrides
        if os.getenv("BIOMNI_ENABLE_QUERY_CATEGORIZATION"):
            self.enable_query_categorization = os.getenv("BIOMNI_ENABLE_QUERY_CATEGORIZATION").lower() == "true"
        if os.getenv("BIOMNI_CATEGORIZATION_CONFIDENCE_THRESHOLD"):
            self.categorization_confidence_threshold = float(os.getenv("BIOMNI_CATEGORIZATION_CONFIDENCE_THRESHOLD"))
        if os.getenv("BIOMNI_REQUIRE_EXECUTION_APPROVAL"):
            self.require_execution_approval = os.getenv("BIOMNI_REQUIRE_EXECUTION_APPROVAL").lower() == "true"
        if os.getenv("BIOMNI_ENABLE_USER_PAUSE_TAG"):
            self.enable_user_pause_tag = os.getenv("BIOMNI_ENABLE_USER_PAUSE_TAG").lower() == "true"

        # Protocols.io access token (prefer specific env vars)
        env_token = os.getenv("PROTOCOLS_IO_ACCESS_TOKEN") or os.getenv("BIOMNI_PROTOCOLS_IO_ACCESS_TOKEN")
        if env_token:
            self.protocols_io_access_token = env_token

    def to_dict(self) -> dict:
        """Convert config to dictionary for easy access."""
        return {
            "path": self.path,
            "timeout_seconds": self.timeout_seconds,
            "llm": self.llm,
            "temperature": self.temperature,
            "use_tool_retriever": self.use_tool_retriever,
            "commercial_mode": self.commercial_mode,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "source": self.source,
            "prompt_token_budget": self.prompt_token_budget,
            "compact_tool_descriptions": self.compact_tool_descriptions,
            "max_agent_steps": self.max_agent_steps,
            "max_consecutive_errors": self.max_consecutive_errors,
            "stall_detection_window": self.stall_detection_window,
            "retrieval_compact_mode": self.retrieval_compact_mode,
            "enable_query_categorization": self.enable_query_categorization,
            "categorization_confidence_threshold": self.categorization_confidence_threshold,
            "require_execution_approval": self.require_execution_approval,
            "enable_user_pause_tag": self.enable_user_pause_tag,
        }


# Global default config instance (optional, for convenience)
default_config = BiomniConfig()
