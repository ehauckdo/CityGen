def similarity_order(chrom1, chrom2, chrom_idx):

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

    return diff

def similarity_range(chrom1, chrom2, chrom_idx, range=0.8):

    _chrom1 = [chrom1[idx] for idx in chrom_idx]
    _chrom2 = [chrom2[idx] for idx in chrom_idx]

    equals = 0
    for g1, g2 in zip(_chrom1, _chrom2):
        bigger = max(g1,g2)
        smaller = min(g1,g2)
        if smaller >= int(bigger*range):
            equals += 1
    return equals/len(_chrom1)
