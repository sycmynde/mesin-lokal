import time
import uuid


class A2ARequest:
    def __init__(self, sender: str, task: str, context: str = "", timeout: int = 30):
        self.id = str(uuid.uuid4())[:8]
        self.sender = sender
        self.task = task
        self.context = context
        self.timeout = timeout
        self.created_at = time.time()


class A2AResponse:
    def __init__(self, request_id: str, agent: str, ok: bool, result: str = "", error: str = ""):
        self.request_id = request_id
        self.agent = agent
        self.ok = ok
        self.result = result
        self.error = error
        self.created_at = time.time()


def to_dict_request(req: A2ARequest) -> dict:
    return {
        "id": req.id,
        "sender": req.sender,
        "task": req.task,
        "context": req.context,
        "timeout": req.timeout,
        "created_at": req.created_at,
    }


def to_dict_response(res: A2AResponse) -> dict:
    return {
        "request_id": res.request_id,
        "agent": res.agent,
        "ok": res.ok,
        "result": res.result,
        "error": res.error,
        "created_at": res.created_at,
    }
