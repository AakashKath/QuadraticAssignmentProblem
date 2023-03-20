import argparse
import networkx as nx
import os
import shutil
import uuid

from datetime import datetime
from math import inf, floor
from os.path import isfile, join

from helpers import DrawGraphs, from_min_cost_flow, save_flow_details, upload_to_google_drive, get_google_drive_folder_id
from substrate import (
    generate_random_graph,
    generate_internet_topology_graph,
    generate_bcube_topology_graph,
    generate_clos_topology_graph,
    generate_xpander_topology_graph
)
from workload import generate_workload

ALLOWED_TOPOLOGIES = ["internet", "clos", "bcube", "xpander", "random"]

def add_sink_node(flow_graph, substrate_graph, node_demand):
    flow_graph.add_node("sink", demand=node_demand)
    substrate_nodes = dict(substrate_graph.nodes(data=True))
    for u in flow_graph.nodes():
        if u == "sink":
            continue
        if u != "source" and substrate_graph.nodes().get(u).get("is_switch", False):
            continue
        data = substrate_nodes.get(u, {})
        if u == "source":
            # data.update({"capacity": data.get("capacity", 0)-1})
            data.update({"capacity": 0}) # source-sink capacity set to 0 to avoid trivial path
        flow_graph.add_edge(u, "sink", **data)
    return flow_graph


def generate_network_flow(graph, source, node_demand, edge_demand):
    G = nx.DiGraph()
    for u, values in graph.nodes(data=True):
        if values.get("is_switch"):
            G.add_node(u, is_switch=True)
        else:
            G.add_node(u)
    for (u, v, kwargs) in graph.edges(data=True):
        kwargs.update({"capacity": floor(kwargs.get("capacity", 0)/edge_demand)})
        if source != v:
            G.add_edge(u, v, **kwargs)
        if source != u:
            G.add_edge(v, u, **kwargs)
    G.nodes().get(source).update({"demand": node_demand})
    G = nx.relabel_nodes(G, {source: "source"})
    return G


def min_congestion(substrate_graph, flow, edge_demand, layout=None, path=None):
    min_cost = inf
    min_graph = None
    min_flow_dict = None
    min_substrate_graph = substrate_graph
    for source in list(substrate_graph.nodes()):
        if substrate_graph.nodes().get(source).get("is_switch", False):
            continue
        network_flow_graph = generate_network_flow(substrate_graph, source, -flow, edge_demand)
        network_flow_graph = add_sink_node(network_flow_graph, substrate_graph, flow)
        # if network_flow_graph.get_edge_data(source, "sink").get("capacity", 0)-1 >= flow:
        #     print("Encountered trivial case.")
        #     continue
        try:
            flow_dict = nx.min_cost_flow(network_flow_graph)
            flow_graph, cost = from_min_cost_flow(flow_dict, network_flow_graph)
            if cost < min_cost:
                min_cost = cost
                min_graph = flow_graph
                min_substrate_graph = network_flow_graph
                min_flow_dict = flow_dict
        except nx.exception.NetworkXUnfeasible:
            # No path found.
            pass
    save_flow_details(min_substrate_graph, min_flow_dict, flow, min_cost, path)
    if min_graph:
        drawing = DrawGraphs(min_substrate_graph, layout=layout, path=path, title=f"Flow: {flow}")
        drawing.add_flow(min_graph)
        drawing.draw()
        return True
    return False


def min_congestion_star_workload(topology, save_graph, save_drive=None):
    workload_graph = generate_workload(node_demand=1, edge_demand=10)
    flow = len(workload_graph.nodes())-1
    edge_demand = workload_graph.get_edge_data("center", "leaf_0")["weight"]
    now = datetime.now()
    path = f"figures/{now.strftime('%Y_%m_%d')}/{now.strftime('%H_%M_%S')}_[{flow}]_{uuid.uuid4()}" if save_graph else None

    if topology == "internet":
        dir_path = "dataset/internet"
        internet_toplogy_files = [f for f in os.listdir(dir_path) if isfile(join(dir_path, f)) and f.endswith(".graphml")]
        for file_name in internet_toplogy_files:
            substrate_graph = generate_internet_topology_graph(join(dir_path, file_name))
            path = f"figures/{now.strftime('%Y_%m_%d')}/{now.strftime('%H_%M_%S')}_{file_name}_[{flow}]_{uuid.uuid4()}" if path else None
            min_congestion(substrate_graph, flow, edge_demand, path=path)
    elif topology == "clos":
        substrate_graph = generate_clos_topology_graph()
        min_congestion(substrate_graph, flow, edge_demand, path=path)
    elif topology == "bcube":
        substrate_graph = generate_bcube_topology_graph()
        min_congestion(substrate_graph, flow, edge_demand, path=path)
    elif topology == "xpander":
        substrate_graph = generate_xpander_topology_graph()
        min_congestion(substrate_graph, flow, edge_demand, path=path)
    elif topology == "random":
        while True:
            substrate_graph = generate_random_graph()
            found_flow = min_congestion(substrate_graph, flow, edge_demand, path=path)
            if found_flow:
                return
    else:
        print(f"We don't support {topology} topology right now.")

    if save_drive:
        folder_id = get_google_drive_folder_id(topology)
        upload_to_google_drive(path, folder_id)
        shutil.rmtree("figures")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minimum Congestion algorithm", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-t", "--topology", choices=ALLOWED_TOPOLOGIES, help="Topology", type=str.lower)
    parser.add_argument("-sg", "--save_graph", help="Save Graph", action="store_true")
    parser.add_argument("-sd", "--save_drive", help="Save to Google Drive (Requires client_secrets.json)", action="store_true")
    args = parser.parse_args()
    config = vars(args)
    min_congestion_star_workload(config.get("topology", None), config.get("save_graph"), config.get("save_drive"))
