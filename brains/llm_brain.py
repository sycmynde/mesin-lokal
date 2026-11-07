class LLMBrain:

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def run(self, data):
        return self.dispatcher.ask(
            messages=data["messages"],
            system_prompt=data.get("system_prompt", ""),
            rag_context=data.get("rag_context", ""),
            tier=data.get("tier")
        )
