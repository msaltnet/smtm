from openai import OpenAI

from ..log_manager import LogManager
from .llm_client import LlmClient


class OpenAILlmClient(LlmClient):
    """OpenAI Chat Completions API client."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.6-luna",
        max_tokens: int = 4096,
    ):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        raise NotImplementedError
