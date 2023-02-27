import networkx as nx

def generate_workload(node_count, node_demand, edge_demand):
    G = nx.Graph()
    G.add_node("center", weight=0)
    G.add_nodes_from([f"leaf_{i}" for i in range(node_count)], weight=node_demand)
    edge_list = list()
    for i in range(node_count):
        edge_list.append(("center", f"leaf_{i}", edge_demand))
    G.add_weighted_edges_from(edge_list)
    return G
