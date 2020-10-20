import random
import lib.Individual as Individual
from lib.logger import log

def initialize_pop(chrom_size, pop_size=10, min_range=0, max_range=10):
    population = []
    for i in range(pop_size):
        chromosome = [random.randint(min_range, max_range)
                        for c in range(chrom_size)]
        individual = Individual.Individual(chromosome)
        individual
        population.append(individual)
    return population

def mutate(individual, mut_rate=0.1, min_range=0, max_range=10):
    chromosome = individual.chromosome
    for i in range(len(chromosome)):
        if random.random() < mut_rate:
            chromosome[i] = random.randint(min_range, max_range)
    individual.chromosome = chromosome

def crossover(parent1, parent2, len_section=None):
    assert len(parent1.chromosome) == len(parent2.chromosome)

    child = Individual.Individual(parent1.chromosome)

    if len_section == None:
        len_section = int(len(parent1.chromosome)/2)

    start_index = random.randint(0, len(parent1.chromosome))
    c_len = len(parent1.chromosome)

    for i in range(start_index, start_index+len_section):
        child.chromosome[i%c_len] = parent2.chromosome[i%c_len]

    for j in range(i+1, i+1+len_section):
        child.chromosome[j%c_len] = parent1.chromosome[j%c_len]
    return child

def evaluate(individual):
    score = 0
    for i in range(len(individual.chromosome)):
        score += individual.chromosome[i]
    return score

def generation(population, generations=10000):

    def get_data(population):
        import numpy as np
        fitnesses = [x.fitness for x in population]
        mini = min(fitnesses)
        maxi = max(fitnesses)
        avg = np.average(fitnesses)
        std = np.std(fitnesses)
        return mini, maxi, avg, std

    for g in range(generations):
        new_population = []
        parents  = roullete(population, len(population))
        for p1_id, p2_id in parents:
            p1, p2 = population[p1_id], population[p2_id]
            child = crossover(p1, p2)
            mutate(child)
            new_population.append(child)
        population = new_population

        if g % 1000 == 0:
            # log some data from pop
            mini, maxi, avg, std = get_data(population)
            log("Generation {}: [min:{}, max:{}, avg:{}, std:{:.2f}]".format(
                                                    g, mini, maxi, avg, std))

def roullete(population, num_parents):

    def normalize(lst):
        s = sum(lst)
        return [float(x)/s for x in lst]
    def ac_fitness(fitnesses):
        ac_fitnesses = []
        for i in range(len(fitnesses)-1, -1, -1):
            ac_fitness = fitnesses[i]
            for j in range(0, i):
                ac_fitness += fitnesses[j]
            ac_fitnesses.insert(0, ac_fitness)
        return ac_fitnesses
    def roullete_selection(ac_fitnesses):
        rand = random.random()
        for i in range(len(ac_fitnesses)):
            if ac_fitnesses[i] > rand:
                return i

    #print([x.fitness for x in population])
    fitnesses = normalize([x.fitness for x in population])
    #print(fitnesses)
    ac_fitnesses = ac_fitness(fitnesses)
    #print(ac_fitnesses)

    parents = []
    for i in range(len(population)):
        parent1 = roullete_selection(ac_fitnesses)
        parent2 = roullete_selection(ac_fitnesses)
        parents.append((parent1, parent2))

    return parents
