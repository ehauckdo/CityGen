import lib.evolution as evo

class Individual():

    def __init__(self, chromosome=[0]):
        self.chromosome = chromosome
        self.fitness = evo.evaluate(self)

    def __repr__(self):
        return "{:02d}, {}".format(self.fitness, self.chromosome)
