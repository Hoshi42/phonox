"""Regression tests for the chat agent's model configuration."""

from unittest.mock import MagicMock, PropertyMock, patch

import anthropic
import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.agent.chat_agent import _compile_graph


@pytest.mark.parametrize(
    "model_name",
    ["claude-haiku-4-5-20251001", "claude-haiku-5-5"],
)
def test_chat_omits_temperature_from_provider_request(model_name, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_CHAT_MODEL", model_name)
    requests = []

    def create_message(**payload):
        requests.append(payload)
        if "temperature" in payload or "temperature" in payload.get("extra_body", {}):
            raise AssertionError(
                "temperature: Extra inputs are not permitted"
            )
        return anthropic.types.Message(
            id="msg_chat_regression",
            type="message",
            role="assistant",
            model=model_name,
            content=[{"type": "text", "text": "Hallo!"}],
            stop_reason="end_turn",
            stop_sequence=None,
            usage={"input_tokens": 10, "output_tokens": 3},
        )

    client = MagicMock()
    client.messages.create.side_effect = create_message

    def create_raw_message(**payload):
        response = MagicMock()
        response.parse.return_value = create_message(**payload)
        return response

    client.messages.with_raw_response.create.side_effect = create_raw_message
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch.object(ChatAnthropic, "_client", new_callable=PropertyMock) as mock_client:
        mock_client.return_value = client
        graph = _compile_graph(None)
        result = graph.invoke(
            {"messages": [HumanMessage(content="hallo")]},
            config={"recursion_limit": 6},
        )

    assert result["messages"][-1].content == "Hallo!"
    assert len(requests) == 1
    assert requests[0]["model"] == model_name
    assert requests[0]["max_tokens"] == 800
    assert requests[0]["tools"]
    assert "temperature" not in requests[0]
    assert "temperature" not in requests[0].get("extra_body", {})
