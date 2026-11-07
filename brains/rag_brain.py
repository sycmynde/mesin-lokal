from tools.rag_coordinator import execute_rag


class RAGBrain:

    def run(self, data):

        text = data.get("text", "")

        if len(text.split()) <= 2:
            return ""

        return execute_rag(text)
