class BrainRouter:

    def __init__(self):
        pass


    def choose(self, route_result):

        brain_type = route_result.get("type")


        if brain_type == "math":
            return "math"


        if brain_type == "file":
            return "file"


        if brain_type == "memory":
            return "memory"

        if brain_type == "project":
            return "project"


        if brain_type == "rag":
            return "rag"

        if brain_type == "termux":
            return "termux"

        if brain_type == "shell":
            return "shell"

        if brain_type == "web":
            return "web"

        if brain_type == "code":
            return "code"

        if brain_type == "tts":
            return "tts"

        if brain_type == "stt":
            return "stt"

        if brain_type == "plugin":
            return "plugin"

        if brain_type == "musik":
            return "musik"

        if brain_type == "tool":
            return "musik"

        return "llm"
