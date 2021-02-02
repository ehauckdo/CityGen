import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from lib.logger import log

matplotlib.use('TkAgg') # this is required for mac when matplotlib is used in
                        # conjuction with tensorflow, otherwise a cryptic error
                        # is thrown

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
                G.add_node(n1, node_color=nodes[n1].color, label=str(n1))
                pos[n1] = nodes[n1].location
            if n2 not in pos:
                G.add_node(n2, node_color=nodes[n2].color, label=str(n2))
                pos[n2] = nodes[n2].location
            G.add_edge(n1, n2, width=1, edge_color=way.color)

    labels = nx.get_node_attributes(G,'label')
    options = { "node_size": 20, "linewidths": 0}#,"labels":labels}
    edges = G.edges()
    node_color = nx.get_node_attributes(G,'node_color').values()
    edge_width = [G[u][v]['width'] for u,v in edges]
    edge_color = [G[u][v]['edge_color'] for u,v in edges]

    nx.draw(G, pos, node_color=node_color, #edge_color=edge_color,
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

def plot_cycles_w_density(nodes, cycles, buildings,tags=None,ways_labels=None):
    G = nx.Graph()
    pos = {}

    for c_id, cycle in cycles.items():
        c = cycle["n_ids"]
        density_color = "black" if cycles[c_id]["density"] == 0 else "blue"
        for i in range(len(c)):
            n1 = c[i]
            n2 = c[(i+1)%len(c)]
            if n1 not in pos:
                G.add_node(n1, node_color=density_color, node_size=1.0)
                pos[n1] = nodes[n1].location
            if n2 not in pos:
                G.add_node(n2, node_color=density_color, node_size=1.0)
                pos[n2] = nodes[n2].location
            G.add_edge(n1, n2, width=1, edge_color=density_color)

    for w_id, way in buildings.items():
        for i in range(len(way.nodes)):
            n1 = way.nodes[i]
            n2 = way.nodes[(i+1)%len(way.nodes)]
            if n1 not in pos:
                G.add_node(n1, node_color="black", node_size=0.1)
                pos[n1] = nodes[n1].location
            if n2 not in pos:
                G.add_node(n2, node_color="black", node_size=0.1)
                pos[n2] = nodes[n2].location
            if G.has_edge(n1, n2) == False:
                G.add_edge(n1, n2, width=1, edge_color="black")

    options = {
               "linewidths": 1,
               "node_color": nx.get_node_attributes(G,'node_color').values(),
               "node_size": list(nx.get_node_attributes(G,'node_size').values()),
               "width": [G[u][v]['width'] for u,v in G.edges()],
               "edge_color": [G[u][v]['edge_color'] for u,v in G.edges()]
              }
    nx.draw(G, pos, **options)

    plt.show()
