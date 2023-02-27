import networkx as nx
import random

from helpers import draw_graph, from_min_cost_flow
from substrate import generate_random_substrate_graph

def add_sink_node(flow_graph, substrate_graph):
    flow_graph.add_node("t")
    substrate_nodes = dict(substrate_graph.nodes(data=True))
    for u in flow_graph.nodes():
        if u != "t":
            flow_graph.add_edge(u, "t", **substrate_nodes.get(u, {}))
    return flow_graph

def generate_network_flow(graph):
    G = nx.DiGraph()
    source = random.choice(list(graph.nodes()))
    for (u, v, kwargs) in graph.edges(data=True):
        if source != v:
            G.add_edge(u, v, **kwargs)
        if source != u:
            G.add_edge(v, u, **kwargs)
    return G

def min_congestion_star_workload():
    substrate_graph = generate_random_substrate_graph(4, 0.2)
    network_flow_graph = generate_network_flow(substrate_graph)
    network_flow_graph = add_sink_node(network_flow_graph, substrate_graph)
    flowDict = nx.min_cost_flow(network_flow_graph)
    flowGraph = from_min_cost_flow(flowDict)
    draw_graph(flowGraph, True)

min_congestion_star_workload()
