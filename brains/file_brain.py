from tools.file_manager import handle_file_action


class FileBrain:

    def run(self, data):

        return handle_file_action(
            data["action"],
            data["path"],
            data.get("content", ""),
            data.get("line_spec"),
        )
