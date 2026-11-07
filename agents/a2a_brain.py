from agents.a2a_orchestrator import A2AOrchestrator
from agents.a2a_registry import list_agents


class A2ABrain:
    def __init__(self, dispatcher=None):
        self.orchestrator = A2AOrchestrator()

    def run(self, data):
        action = data.get("action")
        if action == "ask":
            task = data.get("task", "")
            context = data.get("context", "")
            capability = data.get("capability", "chat")
            res = self.orchestrator.ask(task=task, context=context, capability=capability)
            return {
                "ok": res.ok,
                "agent": res.agent,
                "result": res.result,
                "error": res.error,
                "request_id": res.request_id,
            }
        if action == "agents":
            return {"ok": True, "agents": list_agents()}
        return {"ok": False, "error": "Aksi A2A tidak dikenali"}
