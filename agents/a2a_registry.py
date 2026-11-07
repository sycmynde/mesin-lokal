from typing import Optional


AGENTS = {
    "local-llm": {
        "name": "local-llm",
        "base_url": "http://127.0.0.1:8080/v1/chat/completions",
        "capabilities": ["chat", "summarize", "code", "file"],
        "provider": "openai-compat",
        "model": "Qwen3.8-2B-Uncensored-Q4_K_M",
        "timeout": 60,
        "max_tokens": 512,
    }
}


def list_agents():
    return [{"name": k, **v} for k, v in AGENTS.items()]


def get_agent(name: str) -> Optional[dict]:
    return AGENTS.get(name)


def resolve_agent(capability: str) -> Optional[dict]:
    for agent in AGENTS.values():
        if capability in agent.get("capabilities", []):
            return agent
    return None
