import requests
from agents.a2a_protocol import A2ARequest, A2AResponse, to_dict_request, to_dict_response
from agents.a2a_registry import get_agent, resolve_agent


DEFAULT_TIMEOUT = 30


class A2AOrchestrator:
    def __init__(self, default_agent: str = "local-llm"):
        self.default_agent = default_agent

    def send(self, agent_name: str, task: str, context: str = "", timeout: int = DEFAULT_TIMEOUT) -> A2AResponse:
        agent = get_agent(agent_name)
        if not agent:
            return A2AResponse(request_id="", agent=agent_name, ok=False, error="Agent tidak ditemukan")

        req = A2ARequest(sender="mesin-local", task=task, context=context, timeout=timeout)
        req_dict = to_dict_request(req)

        try:
            if agent.get("provider") == "openai-compat":
                messages = []
                if req.context:
                    messages.append({"role": "system", "content": req.context})
                messages.append({"role": "user", "content": req.task})
                payload = {
                    "model": agent.get("model", ""),
                    "messages": messages,
                    "stream": False,
                    "max_tokens": int(agent.get("max_tokens", 256)),
                }
                r = requests.post(agent["base_url"], json=payload, timeout=timeout)
                r.raise_for_status()
                data = r.json()
                content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
                return A2AResponse(request_id=req.id, agent=agent_name, ok=True, result=content)

            return A2AResponse(request_id=req.id, agent=agent_name, ok=False, error="Provider tidak didukung")
        except requests.exceptions.Timeout:
            return A2AResponse(request_id=req.id, agent=agent_name, ok=False, error="Timeout")
        except Exception as e:
            return A2AResponse(request_id=req.id, agent=agent_name, ok=False, error=str(e))

    def ask(self, task: str, context: str = "", capability: str = "chat") -> A2AResponse:
        agent = resolve_agent(capability) or get_agent(self.default_agent)
        if not agent:
            return A2AResponse(request_id="", agent="", ok=False, error="Tidak ada agent tersedia")
        return self.send(agent_name=agent["name"], task=task, context=context, timeout=agent.get("timeout", DEFAULT_TIMEOUT))
