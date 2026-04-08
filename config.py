from dataclasses import dataclass


@dataclass
class AIConfig:
    provider: str  # "openai_compatible" or "claude"
    api_url: str
    api_key: str
    model_name: str
