from unittest.mock import patch

from smtm.llm.openai_llm_client import OpenAILlmClient


@patch("smtm.llm.openai_llm_client.OpenAI")
def test_constructor_uses_api_key_and_default_model(mock_openai):
    client = OpenAILlmClient(api_key="test-key")

    mock_openai.assert_called_once_with(api_key="test-key")
    assert client.model == "gpt-5.6-luna"
    assert client.max_tokens == 4096
