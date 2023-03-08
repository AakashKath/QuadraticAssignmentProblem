import networkx as nx
import random

from itertools import combinations, groupby

DEFAULT_NODE_COUNT = 10
DEFAULT_PROBABILITY = 0.5
DEFAULT_LEVEL = 2

def generate_random_graph(node_count=DEFAULT_NODE_COUNT, probability=DEFAULT_PROBABILITY):
    G = nx.Graph()
    edges = combinations(range(node_count), 2)
    G.add_nodes_from(range(node_count), capacity=random.randint(10, 50), weight=random.randint(0, 10), color="b")
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
        G.edges[u, v].update({"capacity": random.randint(10, 50), "weight": random.randint(0, 10), "color": "k"})
    return G


def generate_internet_topology_graph(file_path):
    if file_path.endswith(".gml"):
        return nx.read_gml(file_path)
    if file_path.endswith(".graphml"):
        graph = nx.read_graphml(file_path)
        for u, v, values in graph.edges(data=True):
            raw_speed = values.get("LinkSpeedRaw", 0)/1000
            # Edge capacity set to link raw speed
            values.update({"capacity": raw_speed, "weight": raw_speed, "color": "k"})
            raw_speed = max(dict(graph.nodes(data=True)).get(u).get("capacity", 0), raw_speed)
            # Node capacity set to max of incident edge capacity
            graph.nodes().get(u).update({"capacity": raw_speed, "weight": raw_speed})
            raw_speed = max(dict(graph.nodes(data=True)).get(v).get("capacity", 0), raw_speed)
            graph.nodes().get(v).update({"capacity": raw_speed, "weight": raw_speed})
        return graph
    print("Only gml/graphml files allowed in Internet Topology.")


def generate_clos_topology_graph():
    pass


def create_bcube(graph, node_count, level, counter):
    server_list = list()
    if level == 0:
        graph.add_node(counter, is_switch=True)
        switch = counter
        counter += 1
        for _ in range(node_count):
            graph.add_node(counter)
            graph.add_edge(switch, counter)
            server_list.append(counter)
            counter += 1
        return server_list, counter
    for _ in range(node_count):
        servers, counter = create_bcube(graph, node_count, level-1, counter)
        server_list.extend(servers)
    for i in range(node_count**level):
        graph.add_node(counter, is_switch=True)
        switch = counter
        for j in range(node_count):
            graph.add_edge(switch, server_list[(node_count**level)*j+i])
        counter += 1
    return server_list, counter


def generate_bcube_topology_graph(node_count=DEFAULT_NODE_COUNT, level=DEFAULT_LEVEL):
    graph = nx.Graph()
    create_bcube(graph, node_count, level, 0)
    return graph

def generate_xpander_topology_graph():
    pass