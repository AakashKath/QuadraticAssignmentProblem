from math import inf, floor
import networkx as nx

from helpers import DrawGraphs, from_min_cost_flow
from substrate import generate_random_substrate_graph
from workload import generate_workload

def add_sink_node(flow_graph, substrate_graph, source, node_demand):
    flow_graph.add_node("sink", demand=node_demand)
    substrate_nodes = dict(substrate_graph.nodes(data=True))
    for u in flow_graph.nodes():
        if u == "sink":
            continue
        data = substrate_nodes.get(u, {})
        if u == source:
            data.update({"capacity": data.get("capacity", 0)-1})
        flow_graph.add_edge(u, "sink", **data)
    return flow_graph

def generate_network_flow(graph, source, node_demand, edge_demand):
    G = nx.DiGraph()
    for (u, v, kwargs) in graph.edges(data=True):
        kwargs.update({"capacity": floor(kwargs.get("capacity", 0)/edge_demand)})
        if source != v:
            G.add_edge(u, v, **kwargs)
        if source != u:
            G.add_edge(v, u, **kwargs)
    G.nodes().get(source).update({"demand": node_demand})
    return G

def min_congestion_star_workload(flow, edge_demand):
    drawing = DrawGraphs()
    while True:
        substrate_graph = generate_random_substrate_graph()
        min_cost = inf
        min_graph = None
        for source in substrate_graph.nodes():
            network_flow_graph = generate_network_flow(substrate_graph, source, -flow, edge_demand)
            network_flow_graph = add_sink_node(network_flow_graph, substrate_graph, source, flow)
            # if network_flow_graph.get_edge_data(source, "sink").get("capacity", 0)-1 >= flow:
            #     print("Encountered trivial case.")
            #     continue
            try:
                flow_dict = nx.min_cost_flow(network_flow_graph)
                flow_graph, cost = from_min_cost_flow(flow_dict)
                if cost < min_cost:
                    min_cost = cost
                    min_graph = flow_graph
            except nx.exception.NetworkXUnfeasible:
                print("No path found.")
        if min_graph:
            drawing.add_graph(substrate_graph, with_labels=True, title="Substrate Graph")
            drawing.add_graph(min_graph, with_labels=True, title="Min Cost Flow")
            drawing.draw()
            return

if __name__ == "__main__":
    workload_graph = generate_workload(node_demand=1, edge_demand=10)
    min_congestion_star_workload(
        flow=len(workload_graph.nodes()),
        edge_demand=workload_graph.get_edge_data("center", "leaf_0")["weight"]
    )
