import random
import lib.Individual as Individual
from lib.logger import log
import numpy as np
import math

highest_e = 0

def normalize(value):
    return value/highest_e

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

def fitness_density(full_chrom, chrom_idx, neigh_idx, areas):
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

def similarity(chrom1, chrom2, chrom_idx):

    def density_order(chrom):
        # obtain an array of indexes by by ascending order
        _chrom = sorted(range(len(chrom)), key=lambda k: chrom[k])
        #print("chrom indexes: {}".format(_chrom))
        order = [0 for i in range(len(_chrom))]
        idx = 0
        previous = chrom[_chrom[0]]
        for i in range(len(_chrom)):
            if chrom[_chrom[i]] != previous:
                idx +=1
                previous = chrom[_chrom[i]]
            order[_chrom[i]] = idx
        return order
    def difference(order1, order2):
        equals = 0
        for o1, o2 in zip(order1, order2):
            equals = equals+1 if o1==o2 else equals
        return equals/len(order1)

    # extract part of the chromosome that is editable
    _chrom1 = [chrom1[idx] for idx in chrom_idx]
    _chrom2 = [chrom2[idx] for idx in chrom_idx]

    # get their density orders and compute similarity
    chrom1_density_order = density_order(_chrom1)
    chrom2_density_order = density_order(_chrom2)
    diff = difference(chrom1_density_order, chrom2_density_order)
    # print("chrom1: {}".format(_chrom1))
    # print("chrom1 order: {}".format(chrom1_density_order))
    # print("chrom2: {}".format(_chrom2))
    # print("chrom2 order: {}".format(chrom2_density_order))
    # print("difference: {}".format(diff))

    return diff

def similarity_new(chrom1, chrom2, chrom_idx, range=0.8):

    _chrom1 = [chrom1[idx] for idx in chrom_idx]
    _chrom2 = [chrom2[idx] for idx in chrom_idx]

    equals = 0
    for g1, g2 in zip(_chrom1, _chrom2):
        bigger = g1 if g1 > g2 else g2
        smaller = g1 if g2 == bigger else g2
        if smaller >= int(bigger*range):
            equals += 1
    return equals/len(_chrom1)

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

def get_highest_error(chrom, chrom_idx, neigh_idx, max_buildings, areas, top=0.2):
    # maybe this is not needed - I can just initialize many random candidates,
    # get the highest error and set it as the maximum
    chrom_test = [c for c in chrom]
    neigh_len = [len(neigh_idx[i]) for i in range(len(neigh_idx))]
    for i in range(len(neigh_idx)):
        print("{}: {} - {}".format(i, neigh_len[i], neigh_idx[i]))
    _neigh_idx = sorted(range(len(neigh_len)), key=lambda k: neigh_len[k], reverse=True)
    print(_neigh_idx)
    for i in range(math.ceil(len(neigh_len)*top)):
        idx = _neigh_idx[i]
        print("{} - n{} - c{}".format(idx, neigh_idx[idx], chrom[idx]))
        chrom_test[idx] = int(max_buildings/math.ceil(len(neigh_len)*top))
    print("chrom: {}".format(chrom))
    print("chrom_test: {}".format(chrom_test))
    print("Fitness: {}".format(fitness(chrom, chrom_idx, neigh_idx)))
    print("Fitness Density: {}".format(fitness_density(chrom, chrom_idx, neigh_idx, areas)))

def initialize_pop_ME(chrom, chrom_idx, neigh_idx, areas, max_buildings, pop_size=10):

    def highest_error(chrom, chrom_idx, neigh_idx, areas, max_buildings):
        # gives a very rough approximation of the highest error
        global highest_e
        archive = []
        for i in range(100000):
            new_chrom = [g for g in chrom]
            max_parcel = int(max_buildings/len(chrom))
            genes = [int(random.random()*max_parcel) for x in range(len(chrom))]
            for c_idx in chrom_idx: new_chrom[c_idx] = genes[c_idx]
            individual = Individual.Individual(new_chrom)
            individual.fitness = fitness_density(new_chrom, chrom_idx, neigh_idx, areas)
            archive.append(individual)
        highest_e = max([x.fitness for x in archive])
        return max([x.fitness for x in archive])
    def get_index(value, min, max, partitions=10):
        import bisect
        bisect_range = np.linspace(min, max, partitions+1)
        b_index = bisect.bisect(bisect_range, value)-1
        return b_index

    pop_range = 10
    population = [[[] for i in range(pop_range)] for j in range(pop_range)]
    print("Total buildings: {}".format(sum([g for g in chrom])))
    print("Total parcels: {}".format(len(chrom_idx)))

    misses = 0
    archive = []
    for a in range(pop_size):
        r = np.linspace(0, max_buildings, pop_range+1)

        # we will generate random candidates to fit each part of the range
        # between min and max_buildings (e.g 0-20, 21-40, 41-60 etc)
        for it in range(len(r)-1):
            # create a new chrom clone
            new_chrom = [g for g in chrom]

            min_limit, max_limit = r[it], r[it+1]
            #print(min_limit, max_limit)
            # find a vector size appropriate to distribute max_buiildings
            vector_limit = len(chrom_idx) if len(chrom_idx) < int(max_limit/2) else int(max_limit/2)
            size_vector = random.randint(1, vector_limit)
            desired_buildings = random.randint(min_limit, max_limit)
            #print("limits: ", vector_limit, max_limit)
            #print("values: ", size_vector, desired_buildings)

            vector = [random.random() for x in range(size_vector)]
            generated_sum = sum(vector)
            for i in range(len(vector)):
                # because in this number vector generation we often loose
                # or gain by rounding, select to round up or down randomnly
                rounding = random.choice([math.ceil, int])
                vector[i] = rounding((vector[i]/generated_sum)*desired_buildings)

            rnd_idx = [i for i in range(len(chrom_idx))]
            random.shuffle(rnd_idx)
            for i in range(len(vector)):
                idx = rnd_idx[i]
                new_chrom[chrom_idx[idx]] = vector[i]

            ind = Individual.Individual(new_chrom)
            ind.fitness = fitness_density(new_chrom, chrom_idx, neigh_idx, areas)
            nbuildings = 0
            for idx in chrom_idx:
                nbuildings += new_chrom[idx]
            if nbuildings < min_limit or nbuildings > max_limit:
                misses += 1
                continue
            else:
                archive.append(ind)
                if len(archive) >= pop_size:
                    break
        if len(archive) >= pop_size:
            break

    global highest_e
    highest_e = max([x.fitness for x in archive])
    print("highest_error in init pop: {}".format(highest_e))

    while len(archive) > 0:
        ind = archive.pop(0)
        nbuildings = 0
        for idx in chrom_idx:
            nbuildings += ind.chromosome[idx]
        #print("b{}, f{}, nf{}".format(summ, ind.fitness, normalize(ind.fitness)))
        ind.fitness = normalize(ind.fitness)
        d_idx = get_index(nbuildings, 0, max_buildings, pop_range)
        e_idx = get_index(ind.fitness, 0, 1, pop_range)
        #print(d_idx, e_idx)
        if d_idx < 0 or d_idx >= pop_range: continue
        if e_idx < 0: continue
        if e_idx >= pop_range: continue

        population[d_idx][e_idx].append(ind)

    return population

def generation_ME(population, chrom_idx, neigh_idx, areas, max_buildings, generations=1000):

    pop_range = 10
    file1 = open("exp_evostats.txt","w")
    file1.write("gen,x,y,pop,min,max,avg,std")

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
    def get_index(value, min, max, partitions=10):
        import bisect
        bisect_range = np.linspace(min, max, partitions+1)
        b_index = bisect.bisect(bisect_range, value)-1
        return b_index
    def downsize(population, limit=10):
        for i in range(len(population)):
            for j in range(len(population[i])):
                population[i][j] = sorted(population[i][j], key=lambda x: x.fitness)[:limit]
    def downsize_diversity(population, similarity_limit=0.5):
        for i in range(len(population)):
            for j in range(len(population[i])):
                pop = population[i][j]
                for k in range(len(pop)-1, 0, -1):
                    for l in range(k-1, -1, -1):
                        sim = similarity_new(pop[k].chromosome, pop[l].chromosome, chrom_idx)
                        if sim > similarity_limit:
                            if pop[k].fitness < pop[l].fitness:
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
            #max_mut = 10
            max_mut = math.ceil(max_buildings/len(chrom_idx))*(i+2)
            mutate_ME(child, chrom_idx, 0, max_mut, 0.1)
            child.fitness = fitness_density(child.chromosome, chrom_idx, neigh_idx, areas)
            child.fitness = normalize(child.fitness)
            nbuildings = 0
            for idx in chrom_idx:
                nbuildings += child.chromosome[idx]
            d_idx = get_index(nbuildings, 0, max_buildings, pop_range)
            e_idx = get_index(child.fitness, 0, 1, pop_range)

            if d_idx < 0 or d_idx >= pop_range: continue
            if e_idx < 0 or e_idx >= pop_range: continue

            if d_idx != i or e_idx != j:
                population[d_idx][e_idx].append(child)
            elif child.fitness < ind.fitness:
                population[i][j].remove(ind)
                population[i][j].append(child)

    for gen in range(generations):
        if gen % 100 == 0:
            # log some data from pop
            log("Generation: {}".format(gen))
            for i in range(len(population)):
                total_ind_per_range = 0
                for j in range(len(population[i])):
                    pop = population[i][j]
                    total_ind_per_range += len(pop)
                    if len(pop) == 0: n_bui, mini, maxi, avg, std = 0,0,0,0,0
                    else: n_bui, mini, maxi, avg, std = get_data(pop)
                    file1.write("{},{},{},{},{:.2f},{:.2f},{:.2f},{:.2f}".format(gen,i,j,len(pop),mini,maxi,avg,std))
                    log("Population [{}][{}], Cap: {}, n_bui:{}, best:{:.2f}, worst:{:.2f}, "  \
                            "avg:{:.2f}, std:{:.2f}".format(i,j, len(pop), n_bui, mini, maxi, avg, std))
                    file1.write("\n")

        steadystate(population, chrom_idx, max_buildings, neigh_idx, areas, pop_range)

        #downsize(population)
        downsize_diversity(population, 0.35)

    file1.close()

def initialize_pop_ME_backup(chrom, chrom_idx, neigh_idx, areas, pop_size=10, min_range=0, max_range=10):
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
                #print("min_r:{}, max_r:{}".format(min_r, max_r))
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
    ind1, ind2 = population[2][0], population[2][1]
    similarity(ind1.chromosome, ind2.chromosome, chrom_idx)
    for i in range(len(population)):
        print("Population {}: {}".format(i, len(population[i])))
        nb = ""
        for ind in population[i]:
            nb += "{:.2f}, ".format(sum(ind.chromosome[idx] for idx in chrom_idx))
        print(nb)

    return population

def generation_ME_backup(population, chrom_idx, neigh_idx, min_range, max_range, generations=1000):
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
            parent_n_buildings = sum([ind.chromosome[idx] for idx in chrom_idx])
            parent_idx = get_index(n_buildings, max_buildings)

            child = Individual.Individual(ind.chromosome)
            mutate_ME(child, chrom_idx, min_range, max_range, 0.2)
            child.fitness = fitness(child.chromosome, chrom_idx, neigh_idx)
            n_buildings = sum([child.chromosome[idx] for idx in chrom_idx])
            idx = get_index(n_buildings, max_buildings)

            if n_buildings < max_buildings:
                if idx != parent_idx:
                    population[idx].append(child)
                else:
                    if child.fitness > ind.fitness:
                        population[idx].remove(ind)
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
    pop_range = 10
    top_individuals = [[[] for i in range(pop_range)] for j in range(pop_range)]
    for i in range(len(population)):
        for j in range(len(population)):
            pop = population[i][j]
            if len(pop) == 0: continue
            best_ind = sorted(pop, key=lambda i: i.fitness)[:n_ind]
            top_individuals[i][j].extend(best_ind)
    return top_individuals

def top_individuals_ME_backup(population, n_ind=1):
    top_individuals = [[] for x in range(10)]
    for i in range(len(population)):
        pop = population[i]
        best_ind = sorted(pop, key=lambda i: i.fitness)[:n_ind]
        top_individuals[i].extend(best_ind)
    return top_individuals

def initialize_pop_ME_density(chrom, chrom_idx, neigh_idx, areas, pop_size=10, min_range=0, max_range=10, max_density=600, max_buildings=100):
    population = [[] for x in range(10)]
    max_buildings =  int(max_buildings)
    print("max_buildings: {}".format(max_buildings))
    print("max_density: {}".format(max_density))
    print("min_range={}, max_range={}".format(min_range, max_range))
    divisor = int(max_density/10)
    print("partitions={}".format([x for x in range(0, max_buildings+1, int(max_buildings/10))]))
    print("partitions={}".format(np.linspace(0, max_density, 10)))


    def get_index(density, max_density):
        import bisect
        bisect_range = np.linspace(0, max_density, 11)
        b_index = bisect.bisect(bisect_range, density)-1
        return b_index

    for i in range(10):
        new_chrom = [g for g in chrom]

        genes = [random.randint(50,60) for x in range(len(chrom_idx))]
        for c_idx, gene in zip(chrom_idx, genes):
            new_chrom[c_idx] = gene
        individual = Individual.Individual(new_chrom)
        individual.fitness = fitness(new_chrom, chrom_idx, neigh_idx)

        nbuildings = sum(individual.chromosome)
        density = nbuildings/sum(areas)
        print("Individual nbuildings: {}, density: {:.2f}".format(nbuildings, density))
        idx = get_index(density, max_density)
        print("Population idx: {}".format(idx))

    # for i in range(pop_size):
    #     divisor = int(max_buildings/10)
    #
    #     # very ugly hack to ensure that all partitions are full
    #     # fix this eventually
    #     flag = True
    #     while flag:
    #         for i in range(10):
    #             min_r = int((max_buildings/10)*i)
    #             max_r = int((max_buildings/10)*(i+1))
    #             size = min_r + int((max_r-min_r)/2)
    #             #print("min_r:{}, max_r:{}".format(min_r, max_r))
    #             new_chrom = [g for g in chrom]
    #
    #             genes = [random.random() for x in range(len(chrom_idx))]
    #             generated_sum = sum(genes)
    #             for i in range(len(genes)):
    #                 genes[i] = int((genes[i]/generated_sum)*size)
    #
    #             for c_idx, gene in zip(chrom_idx, genes):
    #                 new_chrom[c_idx] = gene
    #
    #             individual = Individual.Individual(new_chrom)
    #             individual.fitness = fitness(new_chrom, chrom_idx, neigh_idx)
    #
    #             nbuildings = get_nbuildings(individual,chrom_idx)
    #             idx = get_index(nbuildings, max_buildings)
    #             if len(population[idx]) < 10:
    #                 population[idx].append(individual)
    #
    #         flag = False
    #         for pop in population:
    #             if len(pop) < 10:
    #                 flag = True
    #                 break
    # ind1, ind2 = population[2][0], population[2][1]
    # similarity(ind1.chromosome, ind2.chromosome, chrom_idx)
    # for i in range(len(population)):
    #     print("Population {}: {}".format(i, len(population[i])))
    #     nb = ""
    #     for ind in population[i]:
    #         nb += "{:.2f}, ".format(sum(ind.chromosome[idx] for idx in chrom_idx))
    #     print(nb)

    return population
