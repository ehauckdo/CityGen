import random
import lib.mapelites.Individual as Individual
from lib.logger import log
import numpy as np
import math
from lib.mapelites.metrics import similarity_order, similarity_range

highest_e = 0

def normalize(value):
    return value/highest_e

def density_error(full_chrom, chrom_idx, neigh_idx, areas):
    errors = []

    def get_error(main, neighbors, minimum_error=0):
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
        density = full_chrom[c_idx]/areas[c_idx]
        neighbor_densities = [full_chrom[n_idx]/areas[c_idx] for n_idx in neigh_idx_list]
        error = get_error(density, neighbor_densities)
        errors.append(error)
        #print("Density: {}, neighbors: {}, error: {:.2f}".format(density,
        #                                        neighbor_densities, error))
    return sum(errors)

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

def initialize_pop_ME(chrom, chrom_idx, neigh_idx, areas, max_buildings, pop_range=10, max_per_cell=10):

    # gives a very rough approximation of the highest error
    def highest_error(chrom, chrom_idx, neigh_idx, areas, max_buildings):
        global highest_e
        archive = []
        for i in range(100000):
            new_chrom = [g for g in chrom]
            max_parcel = int(max_buildings/len(chrom))
            genes = [int(random.random()*max_parcel) for x in range(len(chrom))]
            for c_idx in chrom_idx: new_chrom[c_idx] = genes[c_idx]
            individual = Individual.Individual(new_chrom)
            individual.error = density_error(new_chrom, chrom_idx, neigh_idx, areas)
            archive.append(individual)
        highest_e = max([x.error for x in archive])
        return max([x.error for x in archive])
    def get_index(value, min, max, partitions=10):
        import bisect
        bisect_range = np.linspace(min, max, partitions+1)
        b_index = bisect.bisect(bisect_range, value)-1
        return b_index

    population = [[[] for i in range(pop_range)] for j in range(pop_range)]
    print("Total buildings: {}".format(sum([g for g in chrom])))
    print("Total parcels: {}".format(len(chrom_idx)))

    misses = 0
    archive = []
    # we will try to generate random candidates to fit each part of the range
    # between min and max_buildings (e.g 0-20, 21-40, 41-60 etc).
    # we don't have a good way of generating between the density error (0-1) so
    # we generate extra candidates (max_per_cell*n) to try and hit the max
    for a in range(max_per_cell*10):
        r = np.linspace(0, max_buildings, pop_range+1)

        for it in range(len(r)-1):
            # create a new chrom clone
            new_chrom = [g for g in chrom]

            # find min and max_buildings for this range (e.g. 0-20)
            min_limit, max_limit = r[it], r[it+1]
            # find randomly a maximum vector size to distribute max_buildings
            vector_limit = len(chrom_idx) if len(chrom_idx) < int(max_limit/2) else int(max_limit/2)
            # initialize a vector with size no bigger than vector_limit
            size_vector = random.randint(1, vector_limit)

            # draw a random number of buildings between min and max_limit
            # and distribute this number for each cell of the vector
            desired_buildings = random.randint(min_limit, max_limit)
            vector = [random.random() for x in range(size_vector)]
            generated_sum = sum(vector)
            for i in range(len(vector)):
                # because in this number vector generation we often loose
                # or gain by rounding, select to round up or down randomnly
                rounding = random.choice([math.ceil, int])
                vector[i] = rounding((vector[i]/generated_sum)*desired_buildings)

            # transfer the numbers from the vector into the new chrom
            rnd_idx = [i for i in range(len(chrom_idx))]
            random.shuffle(rnd_idx)
            for i in range(len(vector)):
                idx = rnd_idx[i]
                new_chrom[chrom_idx[idx]] = vector[i]

            ind = Individual.Individual(new_chrom)
            ind.error = density_error(new_chrom, chrom_idx, neigh_idx, areas)
            nbuildings = 0
            for idx in chrom_idx:
                nbuildings += new_chrom[idx]

            if nbuildings < min_limit or nbuildings > max_limit:
                misses += 1
                continue
            else:
                archive.append(ind)

    # what is the maximum acceptable error? We get the maximum error from the
    # initial generated candidates and set it as the max error threshold
    global highest_e
    highest_e = max([x.error for x in archive])
    print("highest_error: {}".format(highest_e))

    # after an initial archive of individuals was generated, distribute
    # them in the appropriate cells of MAP-Elites
    while len(archive) > 0:
        ind = archive.pop(0)
        nbuildings = 0
        for idx in chrom_idx:
            nbuildings += ind.chromosome[idx]

        ind.error = normalize(ind.error)
        d_idx = get_index(nbuildings, 0, max_buildings, pop_range)
        e_idx = get_index(ind.error, 0, 1, pop_range)
        if d_idx < 0 or d_idx >= pop_range: continue
        if e_idx < 0: continue
        if e_idx >= pop_range: continue

        if len(population[d_idx][e_idx]) < max_per_cell:
            population[d_idx][e_idx].append(ind)

    return population

def generation_ME(population, chrom_idx, neigh_idx, areas, max_buildings,
                    metric=similarity_range, generations=1000, pop_range=10):

    file1 = open("_log_mapelites","w")
    file1.write("gen,x,y,pop,min,max,avg,std\n")

    def get_pop_data(p):
        import numpy as np
        fitnesses = [x.error for x in p]
        mini = min(fitnesses)
        chrom = p[fitnesses.index(mini)].chromosome
        n_buildings = [chrom[idx] for idx in chrom_idx]
        maxi = max(fitnesses)
        avg = np.average(fitnesses)
        std = np.std(fitnesses)
        return sum(n_buildings), mini, maxi, avg, std
    def get_index(value, min, max, partitions=10):
        import bisect
        bisect_range = np.linspace(min, max, partitions+1)
        b_index = bisect.bisect(bisect_range, value)-1
        return b_index
    def downsize_diversity(population, similarity_limit=0.5):
        for i in range(len(population)):
            for j in range(len(population[i])):
                pop = population[i][j]
                for k in range(len(pop)-1, 0, -1):
                    for l in range(k-1, -1, -1):
                        sim = similarity_range(pop[k].chromosome, pop[l].chromosome, chrom_idx)
                        if sim > similarity_limit:
                            if pop[k].error < pop[l].error:
                                _temp = pop[k]
                                pop[k] = pop[l]
                                pop[l] = _temp
                            pop.pop(k)
                            break
    def steadystate(population, chrom_idx, max_buildings, neigh_idx, areas, pop_range):
        all_individuals = []
        for i in range(len(population)):
            for j in range(len(population[i])):
                for ind in population[i][j]:
                    all_individuals.append((i, j, ind))

        for i, j, ind in all_individuals:
            child = Individual.Individual(ind.chromosome)
            # the intensity of mutation is proportioinal to the current total no of buildings
            max_mut = math.ceil(max_buildings/len(chrom_idx))*(i+2)
            mutate_ME(child, chrom_idx, 0, max_mut, 0.1)
            child.error = density_error(child.chromosome, chrom_idx, neigh_idx, areas)
            child.error = normalize(child.error)
            nbuildings = 0
            for idx in chrom_idx:
                nbuildings += child.chromosome[idx]

            # get new indexes in the grid and place in the appropriate cell
            d_idx = get_index(nbuildings, 0, max_buildings, pop_range)
            e_idx = get_index(child.error, 0, 1, pop_range)

            if d_idx < 0 or d_idx >= pop_range: continue
            if e_idx < 0 or e_idx >= pop_range: continue

            if d_idx != i or e_idx != j:
                population[d_idx][e_idx].append(child)
            elif child.error < ind.error:
                population[i][j].remove(ind)
                population[i][j].append(child)

    for gen in range(generations):
        # log some data from pop every few generations
        if gen % 100 == 0:
            log("Generation: {}".format(gen))
            for i in range(len(population)):
                for j in range(len(population[i])):
                    pop = population[i][j]
                    # if there's no candidates initialize all stats as 0
                    if len(pop) == 0:
                        n_bui, mini, maxi, avg, std = 0,0,0,0,0
                    else:
                        n_bui, mini, maxi, avg, std = get_pop_data(pop)
                    file1.write("{},{},{},{},{:.2f},{:.2f},{:.2f},{:.2f}".format(gen,i,j,len(pop),mini,maxi,avg,std))
                    log("Population [{}][{}], Cap: {}, n_bui:{}, best:{:.2f}, worst:{:.2f}, "  \
                            "avg:{:.2f}, std:{:.2f}".format(i,j, len(pop), n_bui, mini, maxi, avg, std))
                    file1.write("\n")

        steadystate(population, chrom_idx, max_buildings, neigh_idx, areas, pop_range)
        downsize_diversity(population, 0.35)

    file1.close()

def top_individuals_ME(population, n_ind=1, pop_range=10):
    top_individuals = [[[] for i in range(pop_range)] for j in range(pop_range)]
    for i in range(len(population)):
        for j in range(len(population)):
            pop = population[i][j]
            if len(pop) == 0: continue
            best_ind = sorted(pop, key=lambda i: i.error)[:n_ind]
            top_individuals[i][j].extend(best_ind)
    return top_individuals
