import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from lib.logger import log

def plot(nodes, ways, tags=None, ways_labels=None):

    G = nx.Graph()
    pos = {}

    for w_id, way in ways.items():
        parse_way = False
        if tags == None:
            parse_way = True
        else:
            for k, v in tags:
                if k in way.tags and (way.tags[k] == v or v == None):
                    parse_way = True
                    break

        if parse_way == False:
            continue

        log("Way accepted into plot with tags: {}".format(way.tags), "DEBUG")
        for i in range(len(way.nodes)-1):
            n1, n2 = way.nodes[i], way.nodes[i+1]
            if n1 not in pos:
                G.add_node(n1, node_color=nodes[n1].color)
                pos[n1] = nodes[n1].location
            if n2 not in pos:
                G.add_node(n2, node_color=nodes[n2].color)
                pos[n2] = nodes[n2].location
            G.add_edge(n1, n2, width=1, edge_color=way.color)

    options = { "node_size": 20, "linewidths": 0}
    edges = G.edges()
    node_color = nx.get_node_attributes(G,'node_color').values()
    edge_width = [G[u][v]['width'] for u,v in edges]
    edge_color = [G[u][v]['edge_color'] for u,v in edges]
    nx.draw(G, pos, node_color=node_color, edge_color=edge_color,
                width=edge_width, **options)

    if ways_labels != None:
        h2 = nx.draw_networkx_edges(G, pos=pos, edge_color=edge_color)

        def make_proxy(clr, mappable, **kwargs):
            return Line2D([0, 1], [0, 1], color=clr, **kwargs)

        # generate proxies with the above function
        proxies = [make_proxy(clr, h2, lw=5) for clr in list(ways_labels.values())]
        edge_labels = ["{}".format(tag) for tag, color in ways_labels.items()]
        plt.legend(proxies, edge_labels)

    plt.show()
