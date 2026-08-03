from fastapi.testclient import TestClient

from app.core.dependencies import get_llm
from app.llm.base import LLMProvider
from app.main import app


class DummyLLMProvider(LLMProvider):
    async def chat(self, prompt: str) -> str:
        return f"Echo: {prompt}"


def test_chat_returns_response() -> None:
    app.dependency_overrides[get_llm] = lambda: DummyLLMProvider()
    client = TestClient(app)

    response = client.post("/chat", json={"message": "Hello"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"response": "Echo: Hello"}
