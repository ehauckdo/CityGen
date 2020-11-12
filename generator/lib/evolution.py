import random
import lib.Individual as Individual
from lib.logger import log
import numpy as np
import math

def initialize_pop(chrom, chrom_idx, neigh_idx, pop_size=10, min_range=0, max_range=10):
    population = []
    editable_chrom_size = len(chrom_idx)
    for i in range(pop_size):
        new_chrom = [g for g in chrom]
        for idx in chrom_idx:
            rand_gene = random.randint(min_range, max_range)
            new_chrom[idx] = rand_gene

        #chromosome = [random.randint(min_range, max_range)
        #                for c in range(editable_chrom_size)]
        individual = Individual.Individual(new_chrom)
        individual.fitness = fitness(new_chrom, chrom_idx, neigh_idx)
        population.append(individual)
    return population

def fitness(full_chrom, chrom_idx, neigh_idx):
    errors = []

    def get_error(main, neighbors, minimum_error=10):
        # error returns how far the current density is from being within
        # 80% ~ 120% of the neighbouring maximum density value
        maximum = max(neighbors)
        if maximum == 0:
            if main == 0:
                error = minimum_error
            else:
                error = 0
        else:
            min_range, max_range = maximum*0.8, maximum*1.2
            error = abs(main-min_range) if main <= min_range else abs(main-max_range) if main >= max_range else 0.0
        return error

    for c_idx, neigh_idx_list in zip(chrom_idx, neigh_idx):
        density = full_chrom[c_idx]
        neighbor_densities = [full_chrom[n_idx] for n_idx in neigh_idx_list]
        error = get_error(density, neighbor_densities)
        errors.append(error)
        #print("Density: {}, neighbors: {}, error: {:.2f}".format(density,
        #                                        neighbor_densities, error))
    return sum(errors)

def mutate(individual, chrom_idx, min_range=0, max_range=10, mut_rate=0.1):
    chrom = individual.chromosome
    for idx in chrom_idx:
    #for i in range(len(chrom)):
        if random.random() < mut_rate:
            chrom[idx] = random.randint(min_range, max_range)
    individual.chromosome = chrom

def crossover(parent1, parent2, chrom_idx, len_section=None):
    assert len(parent1.chromosome) == len(parent2.chromosome)

    child = Individual.Individual(parent1.chromosome)

    if len_section == None:
        len_section = int(len(chrom_idx)/2)

    start_index = random.randint(0, len(chrom_idx))
    c_len = len(chrom_idx)

    for i in range(start_index, start_index+len_section):
        idx = chrom_idx[i%c_len]
        child.chromosome[idx] = parent2.chromosome[idx]

    for j in range(i+1, i+1+len_section):
        idx = chrom_idx[j%c_len]
        child.chromosome[idx] = parent1.chromosome[idx]
    return child

def generation(population, chrom_idx, neigh_idx, min_range, max_range, generations=1000):

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
        # Using regular crossover/mutation
        elites_size = 2
        elites = sorted(population, key=lambda i: i.fitness)[:elites_size]
        new_population.extend(elites)
        parents  = roullete(population, len(population)-elites_size)
        for p1_id, p2_id in parents:
            p1, p2 = population[p1_id], population[p2_id]
            child = crossover(p1, p2, chrom_idx)
            #parent = random.choice([p1,p2])
            #child = Individual.Individual(parent.chromosome)
            mutate(child, chrom_idx, min_range, max_range)
            child.fitness = fitness(child.chromosome, chrom_idx, neigh_idx)
            new_population.append(child)

        # ## Using 1-2
        # for ind in population:
        #     child = Individual.Individual(ind.chromosome)
        #     mutate(child, chrom_idx, min_range, max_range, 0.2)
        #     child.fitness = fitness(child.chromosome, chrom_idx, neigh_idx)
        #     if child.fitness < ind.fitness:
        #         new_population.append(child)
        #     else:
        #         new_population.append(ind)

        population = new_population

        if g % 1000 == 0:
            # log some data from pop
            mini, maxi, avg, std = get_data(population)
            log("Generation {}: [min:{:.2f}, max:{:.2f}, "  \
                    "avg:{:.2f}, std:{:.2f}".format(g, mini, maxi, avg, std))

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

    fitnesses = [x.fitness for x in population]
    maximum_fitness = max(fitnesses)
    minimization_fitnesses = [f - maximum_fitness for f in fitnesses]
    fitnesses = normalize(minimization_fitnesses)
    ac_fitnesses = ac_fitness(fitnesses)

    parents = []
    for i in range(num_parents):
        parent1 = roullete_selection(ac_fitnesses)
        parent2 = roullete_selection(ac_fitnesses)
        parents.append((parent1, parent2))

    return parents

##############
# MAP ELITES
##############

def mutate_ME(individual, chrom_idx, min_range=0, max_range=10, mut_rate=0.1):
    chrom = individual.chromosome
    for idx in chrom_idx:
    #for i in range(len(chrom)):
        if random.random() < mut_rate:
            chrom[idx] += random.randint(-max_range, max_range)
            chrom[idx] = 0 if chrom[idx] < 0 else chrom[idx]
    individual.chromosome = chrom

def initialize_pop_ME(chrom, chrom_idx, neigh_idx, pop_size=10, min_range=0, max_range=10):
    population = [[] for x in range(10)]
    max_buildings = len(chrom_idx)*max_range
    print("max_buildings: {}".format(max_buildings))
    print("min_range={}, max_range={}".format(min_range, max_range))
    divisor = int(max_buildings/10)
    print("partitions={}".format([x for x in range(0, max_buildings+1, divisor)]))

    def get_index(n_buildings, max_buildings):
        import bisect
        bisect_range = [int((max_buildings/10)*i) for i in range(10+1)]
        bisect_range[-1] = max_buildings # compensate if rounding is not good
        b_index = bisect.bisect(bisect_range, n_buildings)-1
        return b_index

    def get_nbuildings(individual, chrom_idx):
        nbuildings = sum([individual.chromosome[idx] for idx in chrom_idx])
        # for idx in chrom_idx:
        #     nbuildings += individual.chromosome[idx]
        return nbuildings

    for i in range(pop_size):
        divisor = int(max_buildings/10)

        # very ugly hack to ensure that all partitions are full
        # fix this eventually
        flag = True
        while flag:
            for i in range(10):
                min_r = int((max_buildings/10)*i)
                max_r = int((max_buildings/10)*(i+1))
                size = min_r + int((max_r-min_r)/2)
                print("min_r:{}, max_r:{}".format(min_r, max_r))
                new_chrom = [g for g in chrom]

                genes = [random.random() for x in range(len(chrom_idx))]
                generated_sum = sum(genes)
                for i in range(len(genes)):
                    genes[i] = int((genes[i]/generated_sum)*size)

                for c_idx, gene in zip(chrom_idx, genes):
                    new_chrom[c_idx] = gene

                individual = Individual.Individual(new_chrom)
                individual.fitness = fitness(new_chrom, chrom_idx, neigh_idx)

                nbuildings = get_nbuildings(individual,chrom_idx)
                idx = get_index(nbuildings, max_buildings)
                if len(population[idx]) < 10:
                    population[idx].append(individual)

            flag = False
            for pop in population:
                if len(pop) < 10:
                    flag = True
                    break

    # for i in range(len(population)):
    #     print("Population {}: {}".format(i, len(population[i])))
    #     nb = ""
    #     for ind in population[i]:
    #         nb += "{:.2f}, ".format(sum(ind.chromosome[idx] for idx in chrom_idx))
    #     print(nb)
    return population

def generation_ME(population, chrom_idx, neigh_idx, min_range, max_range, generations=1000):
    max_buildings = len(chrom_idx)*max_range
    max_range = max_range/10 # decrease so mutation variation is not so brutal
    file1 = open("experiment_result","w")

    def get_data(p):
        import numpy as np
        fitnesses = [x.fitness for x in p]
        mini = min(fitnesses)
        chrom = p[fitnesses.index(mini)].chromosome
        n_buildings = [chrom[idx] for idx in chrom_idx]
        maxi = max(fitnesses)
        avg = np.average(fitnesses)
        std = np.std(fitnesses)
        return sum(n_buildings), mini, maxi, avg, std

    def get_index(n_buildings, max_buildings):
        import bisect
        bisect_range = [x for x in range(0,max_buildings,int(max_buildings/10))]
        bisect_range[-1] = max_buildings # compensate if rounding is not good
        b_index = bisect.bisect(bisect_range, n_buildings)-1
        return b_index

    def downsize(population, limit=10):
        for i in range(len(population)):
            population[i] = sorted(population[i], key=lambda x: x.fitness)[:limit]
            #print("Total individuals at {}: {}".format(i, len(population[i])))

    for i in range(generations):
        all_individuals = []
        for p in population: all_individuals.extend(p)

        for ind in all_individuals:
            child = Individual.Individual(ind.chromosome)
            mutate_ME(child, chrom_idx, min_range, max_range, 0.2)
            child.fitness = fitness(child.chromosome, chrom_idx, neigh_idx)
            n_buildings = sum([child.chromosome[idx] for idx in chrom_idx])
            idx = get_index(n_buildings, max_buildings)
            if n_buildings < max_buildings:
                population[idx].append(child)

        downsize(population)

        if i % 100 == 0:
            # log some data from pop
            log("Generation: {}".format(i))
            for pop in population:
                if len(pop) == 0:
                    n_bui, mini, maxi, avg, std = 0, 0, 0, 0, 0
                else:
                    n_bui, mini, maxi, avg, std = get_data(pop)
                file1.write("{:.2f} ".format(mini))
                log("Range {}, Pop: {} n_bui:{}, min:{:.2f}, max:{:.2f}, "  \
                        "avg:{:.2f}, std:{:.2f}".format(i, len(pop), n_bui, mini, maxi, avg, std))
            file1.write("\n")
    file1.close()

def top_individuals_ME(population, n_ind=1):
    top_individuals = [[] for x in range(10)]
    for i in range(len(population)):
        pop = population[i]
        best_ind = sorted(pop, key=lambda i: i.fitness)[:n_ind]
        top_individuals[i].extend(best_ind)
    return top_individuals
