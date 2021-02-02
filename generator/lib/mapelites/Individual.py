import lib.mapelites.evolution as evo

class Individual():

    def __init__(self, chromosome):
        self.chromosome = [x for x in chromosome]
        self.fitness = -1

    def __repr__(self):
        return "{:02f}, {}".format(self.fitness, self.chromosome)
