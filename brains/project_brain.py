class ProjectBrain:

    def __init__(self, project):
        self.project = project

    def run(self, data):

        p = self.project.load()

        return (
            f"Nama: {p.get('name')}\n"
            f"Versi: {p.get('version')}\n"
            f"Platform: {p.get('platform')}\n"
            f"Yang sudah selesai: {', '.join(p.get('completed', []))}\n"
            f"Tujuan sekarang: {p.get('current_goal')}\n"
            f"Langkah berikutnya: {p.get('next_step')}"
        )
