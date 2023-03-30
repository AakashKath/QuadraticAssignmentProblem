import argparse
import networkx as nx
import os
import shutil

from collections import Counter
from datetime import datetime
from math import inf, floor, exp
from os.path import isfile, join
from pulp import LpProblem, LpMaximize, LpVariable, lpSum

from constants import ALLOWED_TOPOLOGIES, ALLOWED_VARIANTS, MWU_FACTOR, GAMMA, RHO2
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


def add_sink_node(flow_graph, substrate_graph, source, node_demand, current_time):
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
        data.update({"capacity": data.get("capacity", 0) - data["load"][current_time]})
        flow_graph.add_edge(u, "sink", **data)
    return flow_graph


def generate_network_flow(graph, source, node_demand, edge_demand, current_time):
    G = nx.DiGraph()
    for u, values in graph.nodes(data=True):
        if values.get("is_switch"):
            G.add_node(u, is_switch=True)
        else:
            G.add_node(u)
    for u, v, kwargs in graph.edges(data=True):
        kwargs.update(
            {
                "capacity": floor(
                    (kwargs.get("capacity", 0) - kwargs["load"][current_time])
                    / edge_demand
                )
            }
        )
        if source != v:
            G.add_edge(u, v, **kwargs)
        if source != u:
            G.add_edge(v, u, **kwargs)
    G.nodes().get(source).update({"demand": node_demand})
    G = nx.relabel_nodes(G, {source: "source"})
    return G


def update_flow_graph(graph, source):
    for u, v, values in graph.edges(data=True):
        if v == "sink":
            graph.nodes().get(u).update(values)
    graph.remove_node("sink")
    graph = nx.relabel_nodes(graph, {"source": source})
    return graph


def fetch_all_mappings(substrate_graph, flow, edge_demand, current_time):
    all_mappings = list()
    for source in list(substrate_graph.nodes()):
        if substrate_graph.nodes().get(source).get("is_switch", False):
            continue
        network_flow_graph = generate_network_flow(
            substrate_graph, source, -flow, edge_demand, current_time
        )
        network_flow_graph = add_sink_node(
            network_flow_graph, substrate_graph, source, flow, current_time
        )
        # if network_flow_graph.get_edge_data(source, "sink").get("capacity", 0)-1 >= flow:
        #     print("Encountered trivial case.")
        #     continue
        try:
            flow_dict = nx.min_cost_flow(network_flow_graph)
            flow_graph, cost = from_min_cost_flow(flow_dict, network_flow_graph)
            flow_graph = update_flow_graph(flow_graph, source)
            all_mappings.append((network_flow_graph, flow_graph, cost, source))
        except nx.exception.NetworkXUnfeasible:
            # No path found.
            pass
    return all_mappings


def min_congestion(substrate_graph, flow, edge_demand, current_time):
    min_cost = inf
    min_graph = None
    min_source = None
    min_substrate_graph = substrate_graph
    all_mappings = fetch_all_mappings(substrate_graph, flow, edge_demand, current_time)
    for network_flow_graph, flow_graph, cost, source in all_mappings:
        if cost < min_cost:
            min_cost = cost
            min_graph = flow_graph
            min_substrate_graph = network_flow_graph
            min_source = source
    if min_substrate_graph:
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


def update_weight(graph, min_graph, start_time, end_time, variant="default"):
    if variant == "default" and min_graph:
        for u, v, values in min_graph.edges(data=True):
            edge = graph.edges()[u, v]
            edge.update({"weight": edge.get("weight", 0) * (1 + MWU_FACTOR)})
        for u, values in min_graph.nodes(data=True):
            if values.get("load", 0) == 0:
                continue
            node = graph.nodes().get(u)
            node.update({"weight": node.get("weight", 0) * (1 + MWU_FACTOR)})
    elif variant == "bansal":
        for u, v, values in graph.edges(data=True):
            load_factor = 0
            deno = RHO2 * values.get("capacity")
            for time in range(start_time, end_time + 1):
                load_factor += exp((values.get("load")[time] * GAMMA) / deno)
            # Since min_cost_flow doesn't work on proper fraction weight
            weight = (GAMMA * load_factor) / deno
            if weight < 1:
                weight = 0
            values.update({"weight": weight})


def update_load(graph, min_graph, start_time, end_time):
    if not min_graph:
        return
    for u, v, values in min_graph.edges(data=True):
        for time in range(start_time, end_time + 1):
            edge = graph.edges()[u, v]
            edge.get("load")[time] += values.get("load", 0)
    for u, values in min_graph.nodes(data=True):
        for time in range(start_time, end_time + 1):
            load = graph.nodes().get(u)["load"]
            load[time] += values.get("load", 0)


def solve_lp(graph, workload_map):
    obj = list()
    variables = dict()
    model = LpProblem(name="workload_mapping", sense=LpMaximize)
    for u, v, values in graph.edges(data=True):
        e_var = LpVariable(name=f"{u}-{v}", lowBound=0, cat="Integer")
        variables.update({f"{u}-{v}": e_var})
        obj.append(-values.get("capacity", 0) * e_var)
    for u, values in graph.nodes(data=True):
        n_var = LpVariable(name=f"{u}", lowBound=0, cat="Integer")
        variables.update({f"{u}": n_var})
        obj.append(-values.get("capacity", 0) * n_var)
    for workload, all_mappings in workload_map:
        zi = LpVariable(name=f"z_{workload}", lowBound=0, cat="Integer")
        variables.update({f"z_{workload}": zi})
        obj.append(zi)
        for idx, mapping in enumerate(all_mappings):
            mapping_expression = 0
            for u, values in mapping.nodes(data=True):
                if values.get("load", 0) > 0:
                    mapping_expression += values.get("load") * variables.get(f"{u}")
            for u, v, values in mapping.edges(data=True):
                if values.get("load", 0) > 0:
                    var = variables.get(f"{u}-{v}")
                    if var is None:
                        var = variables.get(f"{v}-{u}")
                    mapping_expression += values.get("load") * var
            model += (mapping_expression >= zi, f"c_{workload}_{idx}")
    model += lpSum(obj)
    status = model.solve()


def fetch_congestion_value(graph):
    congestion = 0
    for _, _, values in graph.edges(data=True):
        capacity = values.get("capacity")
        for load in values.get("load"):
            congestion = max(congestion, load / capacity)
    for _, values in graph.nodes(data=True):
        capacity = values.get("capacity")
        for load in values.get("load"):
            congestion = max(congestion, load / capacity)
    return congestion


def min_congestion_star_workload(
    topology, leaf_counts, variant, save_graph, save_drive, workload_details
):
    congestions = list()
    substrate_graphs = get_substrate_graphs(topology)
    folder_path = (
        f"figures/{datetime.now().strftime('%Y_%m_%d')}" if save_graph else None
    )
    if not (leaf_counts or workload_details):
        print("No workload info found. Exiting...")
        return
    if not workload_details:
        workload_details = [(0, 1, lc) for lc in leaf_counts]
    workload_details.sort()
    algo_end_time = max([t for _, t, _ in workload_details]) + 1
    for title, graph in substrate_graphs:
        added_flows = list()
        graph_path = (
            f"{folder_path}/{title}_{datetime.now().strftime('%H_%M_%S')}"
            if folder_path
            else None
        )
        for u in graph.nodes():
            graph.nodes().get(u).update({"load": [0] * algo_end_time})
        for u, v in graph.edges():
            graph.edges()[u, v].update({"load": [0] * algo_end_time})
        drawing = DrawGraphs(graph, with_labels=True, path=graph_path)
        for current_time in range(algo_end_time):
            min_graph = None
            # workloads_to_remove = [
            #     (s, t, l) for s, t, l in workload_details if t == current_time
            # ]
            # if workloads_to_remove:
            #     drawing.remove_flow()
            workloads_to_map = [
                (s, t, l) for s, t, l in workload_details if s == current_time
            ]
            if not workloads_to_map:
                continue
            for i, (start_time, end_time, lc) in enumerate(workloads_to_map):
                update_weight(graph, min_graph, start_time, end_time, variant)
                # Hard-coding workload graph, as star workload is trivial to visualize
                # workload_graph = generate_workload(edge_demand=1, node_count=lc)
                # flow = len(workload_graph.nodes()) - 1
                # edge_demand = list(nx.get_edge_attributes(workload_graph, "weight").values())[0]
                flow = lc
                edge_demand = 1
                path = f"{graph_path}_{i}_{flow}" if graph_path else None
                min_substrate_graph, min_graph, cost, source = min_congestion(
                    graph.copy(), flow, edge_demand, current_time
                )
                save_flow_details(min_substrate_graph, min_graph, flow, cost, path)
                if min_graph:
                    added_flows.append(flow)
                    drawing.add_flow(min_graph, source)
                    update_load(graph, min_graph, start_time, end_time)
                else:
                    print("Couldn't fit workload in substrate graph.")
        congestions.append(fetch_congestion_value(graph))
        drawing.add_title(title=f"Flow: {added_flows}")
        drawing.draw()
    print(congestions)

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
    parser.add_argument(
        "-wd",
        "--workload_details",
        nargs="+",
        help="Details of incoming workload, (start_time, end_time, leaf_count)",
        type=lambda a: tuple(map(int, a.split(","))),
    )
    args = parser.parse_args()
    config = vars(args)
    min_congestion_star_workload(
        topology=config.get("topology", None),
        leaf_counts=config.get("leaf_counts"),
        save_graph=config.get("save_graph"),
        save_drive=config.get("save_drive"),
        variant=config.get("variant"),
        workload_details=config.get("workload_details"),
    )
