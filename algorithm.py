import argparse
import networkx as nx
import os
import shutil

from collections import Counter
from datetime import datetime
from math import inf, floor
from os.path import isfile, join

from constants import ALLOWED_TOPOLOGIES, ALLOWED_VARIANTS, MWU_FACTOR
from helpers import (
    DrawGraphs,
    from_min_cost_flow,
    save_flow_details,
    upload_to_google_drive,
    get_google_drive_folder_id,
)
from substrate import (
    generate_random_graph,
    generate_internet_topology_graph,
    generate_bcube_topology_graph,
    generate_clos_topology_graph,
    generate_xpander_topology_graph,
)
from workload import generate_workload


def add_sink_node(flow_graph, substrate_graph, source, node_demand):
    flow_graph.add_node("sink", demand=node_demand)
    substrate_nodes = dict(substrate_graph.nodes(data=True))
    for u in flow_graph.nodes():
        if u == "sink" or substrate_graph.nodes().get(u, {}).get("is_switch", False):
            continue
        data = substrate_nodes.get(u, {})
        if u == "source":
            data = substrate_nodes.get(source, {})
            data.update({"capacity": data.get("capacity", 1) - 1})
            # data.update({"capacity": 0}) # source-sink capacity set to 0 to avoid trivial path
        flow_graph.add_edge(u, "sink", **data)
    return flow_graph


def generate_network_flow(graph, source, node_demand, edge_demand):
    G = nx.DiGraph()
    for u, values in graph.nodes(data=True):
        if values.get("is_switch"):
            G.add_node(u, is_switch=True)
        else:
            G.add_node(u)
    for u, v, kwargs in graph.edges(data=True):
        kwargs.update({"capacity": floor(kwargs.get("capacity", 0) / edge_demand)})
        if source != v:
            G.add_edge(u, v, **kwargs)
        if source != u:
            G.add_edge(v, u, **kwargs)
    G.nodes().get(source).update({"demand": node_demand})
    G = nx.relabel_nodes(G, {source: "source"})
    return G


def min_congestion(substrate_graph, flow, edge_demand):
    min_cost = inf
    min_graph = None
    min_source = None
    min_substrate_graph = substrate_graph
    for source in list(substrate_graph.nodes()):
        if substrate_graph.nodes().get(source).get("is_switch", False):
            continue
        network_flow_graph = generate_network_flow(
            substrate_graph, source, -flow, edge_demand
        )
        network_flow_graph = add_sink_node(
            network_flow_graph, substrate_graph, source, flow
        )
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
                min_source = source
        except nx.exception.NetworkXUnfeasible:
            # No path found.
            pass
    if min_graph:
        min_graph = nx.relabel_nodes(min_graph, {"source": min_source})
        min_substrate_graph = nx.relabel_nodes(
            min_substrate_graph, {"source": f"source_{min_source}"}
        )
    return min_substrate_graph, min_graph, min_cost, min_source


def get_substrate_graphs(topology):
    substrate_graphs = list()
    if topology == "internet":
        dir_path = "dataset/internet"
        internet_toplogy_files = [
            f
            for f in os.listdir(dir_path)
            if isfile(join(dir_path, f)) and f.endswith(".graphml")
        ]
        for file_name in internet_toplogy_files:
            substrate_graphs.append(
                (
                    f"{file_name}",
                    generate_internet_topology_graph(join(dir_path, file_name)),
                )
            )
    elif topology == "clos":
        substrate_graphs.append((f"clos", generate_clos_topology_graph()))
    elif topology == "bcube":
        substrate_graphs.append((f"bcube", generate_bcube_topology_graph()))
    elif topology == "xpander":
        substrate_graphs.append((f"xpander", generate_xpander_topology_graph()))
    elif topology == "random":
        substrate_graphs.append((f"random", generate_random_graph()))
    else:
        print(f"We don't support {topology} topology right now.")
    return substrate_graphs


def update_substrate_graph(graph, min_graph, variant="default"):
    if variant == "default":
        for u, v, values in min_graph.edges(data=True):
            if v == "sink":
                node = graph.nodes().get(u)
                node.update(
                    {
                        "weight": node.get("weight") * (1 + MWU_FACTOR),
                        "capacity": node.get("capacity") - values.get("capacity"),
                    }
                )
            else:
                edge = graph.edges()[u, v]
                edge.update(
                    {
                        "weight": edge.get("weight") * (1 + MWU_FACTOR),
                        "capacity": edge.get("capacity") - values.get("capacity"),
                    }
                )
    elif variant == "bansal":
        pass


def min_congestion_star_workload(
    topology, leaf_counts, variant, save_graph, save_drive
):
    substrate_graphs = get_substrate_graphs(topology)
    folder_path = (
        f"figures/{datetime.now().strftime('%Y_%m_%d')}" if save_graph else None
    )
    for title, graph in substrate_graphs:
        added_flows = list()
        graph_path = (
            f"{folder_path}/{title}_{datetime.now().strftime('%H_%M_%S')}"
            if folder_path
            else None
        )
        drawing = DrawGraphs(graph, with_labels=True, path=graph_path)
        for i, lc in enumerate(leaf_counts):
            # Hard-coding workload graph, as star workload is trivial to visualize
            # workload_graph = generate_workload(edge_demand=1, node_count=lc)
            # flow = len(workload_graph.nodes()) - 1
            # edge_demand = list(nx.get_edge_attributes(workload_graph, "weight").values())[0]
            flow = lc
            edge_demand = 1
            path = f"{graph_path}_{i}_{flow}" if graph_path else None
            min_substrate_graph, min_graph, cost, source = min_congestion(
                graph.copy(), flow, edge_demand
            )
            save_flow_details(min_substrate_graph, min_graph, flow, cost, path)
            if min_graph:
                added_flows.append(flow)
                drawing.add_flow(min_graph, source)
                update_substrate_graph(graph, min_graph, variant=variant)
            else:
                print("Couldn't fit workload in substrate graph.")
        drawing.add_title(title=f"Flow: {added_flows}")
        drawing.draw()

    if save_drive:
        folder_id = get_google_drive_folder_id(topology)
        upload_to_google_drive(folder_path, folder_id)
        shutil.rmtree(folder_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Minimum Congestion algorithm",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-t", "--topology", choices=ALLOWED_TOPOLOGIES, help="Topology", type=str.lower
    )
    parser.add_argument("-sg", "--save_graph", help="Save Graph", action="store_true")
    parser.add_argument(
        "-sd",
        "--save_drive",
        help="Save to Google Drive (Requires client_secrets.json)",
        action="store_true",
    )
    parser.add_argument(
        "-lc", "--leaf_counts", nargs="+", help="Number of workloads to fit.", type=int
    )
    parser.add_argument(
        "-v",
        "--variant",
        choices=ALLOWED_VARIANTS,
        help="Multiplicative weight update variant to use for multiple workloads.",
        type=str.lower,
        default="default",
    )
    args = parser.parse_args()
    config = vars(args)
    min_congestion_star_workload(
        topology=config.get("topology", None),
        leaf_counts=config.get("leaf_counts"),
        save_graph=config.get("save_graph"),
        save_drive=config.get("save_drive"),
        variant=config.get("variant"),
    )
