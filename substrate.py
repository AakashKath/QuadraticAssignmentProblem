import networkx as nx
import random

from itertools import combinations, groupby

DEFAULT_NODE_COUNT = 10
PROBABILITY = 0.5

def generate_random_substrate_graph(node_count=DEFAULT_NODE_COUNT, probability=PROBABILITY):
    G = nx.Graph()
    edges = combinations(range(node_count), 2)
    G.add_nodes_from(range(node_count), capacity=random.randint(10, 50), weight=random.randint(0, 10))
    if probability <= 0:
        return G
    if probability >= 1:
        return nx.complete_graph(node_count, create_using=G)
    for _, node_edges in groupby(edges, key=lambda x: x[0]):
        node_edges = list(node_edges)
        random_edge = random.choice(node_edges)
        G.add_edge(*random_edge)
        for e in node_edges:
            if random.random() < probability:
                G.add_edge(*e)
    for (u, v) in G.edges():
        G.edges[u, v].update({'capacity': random.randint(10, 50), 'weight': random.randint(0, 10)})
    return G
