import json


class ProjectState:

    def __init__(self):
        self.file = "data/project.json"


    def load(self):

        try:
            with open(
                self.file,
                "r",
                encoding="utf-8"
            ) as f:
                return json.load(f)

        except:
            return {}


    def build_context(self):

        p = self.load()

        if not p:
            return ""

        return f"""
STATUS PROYEK MESIN AI:

Nama:
{p.get('name')}

Versi:
{p.get('version')}

Platform:
{p.get('platform')}

Yang sudah selesai:
{', '.join(p.get('completed', []))}

Tujuan sekarang:
{p.get('current_goal')}

Langkah berikutnya:
{p.get('next_step')}
"""
