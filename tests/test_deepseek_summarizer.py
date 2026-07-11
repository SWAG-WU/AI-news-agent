from src.summarizer import LLMSummarizer
from src.config import Config


class _Config:
    deepseek_api_key = "test-key"
    deepseek_base_url = "https://api.deepseek.com"
    deepseek_model = "deepseek-v4-flash"


def test_summarizer_builds_deepseek_chat_payload():
    summarizer = LLMSummarizer(_Config())

    payload = summarizer._build_chat_payload("content to summarize")

    assert payload["model"] == "deepseek-v4-flash"
    assert payload["temperature"] == 0.3
    assert payload["max_tokens"] == 200
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1] == {
        "role": "user",
        "content": "content to summarize",
    }


def test_deepseek_config_falls_back_when_optional_env_values_are_empty():
    config = Config.__new__(Config)
    config._env = type(
        "Env",
        (),
        {
            "deepseek_base_url": "",
            "deepseek_model": "",
        },
    )()

    assert config.deepseek_base_url == "https://api.deepseek.com"
    assert config.deepseek_model == "deepseek-v4-flash"
