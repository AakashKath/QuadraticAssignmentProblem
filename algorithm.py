import math
import networkx as nx

from helpers import DrawGraphs, from_min_cost_flow
from substrate import generate_random_substrate_graph

def add_sink_node(flow_graph, substrate_graph, source, demand):
    flow_graph.add_node("sink", demand=demand)
    substrate_nodes = dict(substrate_graph.nodes(data=True))
    for u in flow_graph.nodes():
        if u == "sink":
            continue
        data = substrate_nodes.get(u, {})
        if u == source:
            data.update({"capacity": data.get("capacity", 0)-1})
        flow_graph.add_edge(u, "sink", **data)
    return flow_graph

def generate_network_flow(graph, source, demand):
    G = nx.DiGraph()
    for (u, v, kwargs) in graph.edges(data=True):
        if source != v:
            G.add_edge(u, v, **kwargs)
        if source != u:
            G.add_edge(v, u, **kwargs)
    G.nodes().get(source).update({"demand": demand})
    return G

def min_congestion_star_workload(demand):
    drawing = DrawGraphs()
    substrate_graph = generate_random_substrate_graph(4, 0.2)
    drawing.add_graph(substrate_graph, True)
    min_cost = math.inf
    for source in substrate_graph.nodes():
        network_flow_graph = generate_network_flow(substrate_graph, source, -demand)
        network_flow_graph = add_sink_node(network_flow_graph, substrate_graph, source, demand)
        try:
            flow_dict = nx.min_cost_flow(network_flow_graph)
            flow_graph, cost = from_min_cost_flow(flow_dict)
            if cost < min_cost:
                min_cost = cost
                min_graph = flow_graph
        except nx.exception.NetworkXUnfeasible:
            print("No path found.")
    drawing.add_graph(min_graph, True)
    drawing.draw()

min_congestion_star_workload(1)
