import math
import networkx as nx
import random

from itertools import combinations, groupby

DEFAULT_NODE_COUNT = 10
DEFAULT_PROBABILITY = 0.5
DEFAULT_LEVEL = 2
DEFAULT_MIDDLE_STAGE_COUNT = 5
DEFAULT_STAGE_COUNT = 1
DEFAULT_EDGE_SWITCH_COUNT = 5
DEFAULT_SERVERS_PER_RACK = 4
DEFAULT_LIFT_NO = 2

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


def create_clos_server(graph, previous_nodes, node_count, stage_no):
    node_list = list()
    are_egress_servers = True if graph.nodes() else False
    for i in range(node_count):
        node = f"{stage_no}_{i}"
        node_list.append(node)
        graph.add_node(node)
        if are_egress_servers:
            for pre in previous_nodes:
                graph.add_edge(node, pre)
    stage_no += 1
    return node_list, stage_no


def create_clos_stage(graph, previous_nodes, crossbars, stage_no):
    node_list = list()
    for i in range(crossbars):
        node = f"{stage_no}_{i}"
        node_list.append(node)
        graph.add_node(node, is_switch=True)
        for pre in previous_nodes:
            graph.add_edge(node, pre)
    stage_no += 1
    return node_list, stage_no


def generate_clos_topology_graph(
    node_count=DEFAULT_NODE_COUNT,
    middle_stage_crossbars=DEFAULT_MIDDLE_STAGE_COUNT,
    number_of_stages=DEFAULT_STAGE_COUNT,
    edge_crossbars=DEFAULT_EDGE_SWITCH_COUNT
):
    graph = nx.Graph()
    stage_no = 0
    node_list = list()
    # Divide the servers into two parts
    node_list, stage_no = create_clos_server(graph, node_list, math.floor(node_count/2), stage_no)
    # Create Ingress stage
    node_list, stage_no = create_clos_stage(graph, node_list, edge_crossbars, stage_no)
    # Create middle stages
    for _ in range(number_of_stages):
        node_list, stage_no = create_clos_stage(graph, node_list, middle_stage_crossbars, stage_no)
    # Create egress stage
    node_list, stage_no = create_clos_stage(graph, node_list, edge_crossbars, stage_no)
    create_clos_server(graph, node_list, math.ceil(node_count/2), stage_no)
    return graph


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


def lift_graph(graph, lift):
    mapping = dict(zip(graph.nodes(), [lift*x for x in graph.nodes()]))
    graph = nx.relabel_nodes(graph, mapping)
    for n in list(graph.nodes()):
        for i in range(1, lift):
            graph.add_node(n+i, is_switch=True)
    for u, v in list(graph.edges()):
        graph.remove_edge(u, v)
        matching = list(range(lift))
        random.shuffle(matching)
        for i in range(lift):
            j = matching[i]
            graph.add_edge(u+i, v+j, capacity=random.randint(10, 50), weight=random.randint(0, 10))
    return graph


def generate_xpander_topology_graph(node_count=DEFAULT_NODE_COUNT, servers_per_rack=DEFAULT_SERVERS_PER_RACK, lift=DEFAULT_LIFT_NO):
    """
    Xpander topology generated as per https://github.com/prvnkumar/xpander/blob/master/xpander/xpander.py
    """
    # Update parameters to create xpander topology
    num_switches = int(math.ceil(node_count/servers_per_rack))
    switch_d = random.randint(1, num_switches-1)
    num_lifts = int(math.ceil(math.log(num_switches/(switch_d+1), lift)))
    num_switches = int((switch_d + 1) * math.pow(lift, num_lifts))
    node_count = num_switches * servers_per_rack
    print(f"No. of switches: {num_switches}")

    # Create expander graph for switches
    graph = nx.random_regular_graph(switch_d, switch_d+1)
    nx.set_node_attributes(graph, True, "is_switch")

    # Lift graph
    for i in range(num_lifts):
        graph = lift_graph(graph, lift)

    # Add server nodes
    server_no = num_switches
    for i in list(graph.nodes()):
        for _ in range(servers_per_rack):
            graph.add_edge(i, server_no, capacity=random.randint(10, 50), weight=random.randint(0, 10))
            server_no += 1

    return graph
