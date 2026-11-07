class BrainRegistry:

    def __init__(self):
        self.brains = {}


    def register(self, name, brain):

        self.brains[name] = brain


    def get(self, name):

        return self.brains.get(name)


    def list(self):

        return list(self.brains.keys())


    def execute(self, name, data):

        brain = self.get(name)

        if not brain:
            return "Brain tidak ditemukan"

        return brain.run(data)
