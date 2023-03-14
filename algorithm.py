import argparse
import networkx as nx
import os

from math import inf, floor
from os.path import isfile, join

from helpers import DrawGraphs, from_min_cost_flow
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
        data.update({"color": "k"})
        if u == "source":
            # data.update({"capacity": data.get("capacity", 0)-1})
            data.update({"capacity": 0}) # source-sink capacity set to 0 to avoid trivial path
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
    G = nx.relabel_nodes(G, {source: "source"})
    return G


def min_congestion(substrate_graph, flow, edge_demand, layout=None):
    min_cost = inf
    min_graph = None
    min_substrate_graph = None
    max_capacity = 0
    for source in list(substrate_graph.nodes())[:1]:
        if substrate_graph.nodes().get(source).get("is_switch", False):
            continue
        network_flow_graph = generate_network_flow(substrate_graph, source, -flow, edge_demand)
        network_flow_graph = add_sink_node(network_flow_graph, substrate_graph, flow)
        # if network_flow_graph.get_edge_data(source, "sink").get("capacity", 0)-1 >= flow:
        #     print("Encountered trivial case.")
        #     continue
        try:
            flow_dict = nx.min_cost_flow(network_flow_graph)
            flow_graph, cost, capacity = from_min_cost_flow(flow_dict, network_flow_graph)
            max_capacity = max(capacity, max_capacity)
            if cost < min_cost and capacity >= flow:
                min_cost = cost
                min_graph = flow_graph
                min_substrate_graph = network_flow_graph
        except nx.exception.NetworkXUnfeasible:
            print("No path found.")
    if min_graph:
        drawing = DrawGraphs(min_substrate_graph, title=f"Substrate Graph[{flow}]", layout=layout)
        drawing.add_flow(min_graph)
        drawing.draw()
        return True, flow
    return False, max_capacity


def min_congestion_star_workload(topology):
    workload_graph = generate_workload(node_demand=1, edge_demand=10)
    flow = len(workload_graph.nodes())-1
    edge_demand = workload_graph.get_edge_data("center", "leaf_0")["weight"]
    if topology == "internet":
        dir_path = "dataset/internet"
        # Enabled only a few files as capacity is still not certain
        # internet_toplogy_files = [f for f in os.listdir(dir_path) if isfile(join(dir_path, f)) and f.endswith(".graphml")]
        internet_toplogy_files = ['Cesnet1999.graphml', 'Sinet.graphml', 'Cudi.graphml', 'Garr200912.graphml', 'Internetmci.graphml', 'Garr201104.graphml', 'Cesnet200511.graphml', 'Arn.graphml', 'Aconet.graphml', 'SwitchL3.graphml', 'Cesnet201006.graphml', 'KentmanJul2005.graphml', 'Kreonet.graphml', 'Garr200908.graphml', 'Sanet.graphml', 'Marwan.graphml', 'Garr201003.graphml', 'Litnet.graphml', 'Garr199904.graphml', 'Savvis.graphml', 'Pacificwave.graphml', 'Garr200112.graphml', 'Renater2006.graphml', 'Janetlense.graphml', 'Basnet.graphml', 'Cesnet200603.graphml', 'Karen.graphml', 'Myren.graphml', 'Ulaknet.graphml', 'Cesnet200304.graphml', 'Geant2009.graphml', 'Garr201110.graphml', 'Latnet.graphml', 'Garr201112.graphml', 'Garr201111.graphml', 'KentmanJan2011.graphml', 'Carnet.graphml', 'Garr201001.graphml', 'Cesnet1997.graphml', 'Arnes.graphml', 'Zamren.graphml', 'Restena.graphml', 'Garr201004.graphml', 'Geant2001.graphml', 'Geant2012.graphml', 'KentmanFeb2008.graphml', 'Nordu1989.graphml', 'Agis.graphml', 'Garr201201.graphml', 'Garr201107.graphml', 'Atmnet.graphml', 'Belnet2005.graphml', 'Geant2010.graphml', 'Garr201105.graphml', 'Cynet.graphml', 'Renater2001.graphml', 'Renam.graphml', 'Grnet.graphml', 'Ilan.graphml', 'Garr201108.graphml', 'Niif.graphml', 'Harnet.graphml', 'Renater2010.graphml', 'Garr201012.graphml', 'Renater1999.graphml', 'Uran.graphml', 'Padi.graphml', 'Renater2004.graphml', 'Gambia.graphml', 'KentmanAug2005.graphml', 'WideJpn.graphml', 'KentmanApr2007.graphml', 'Garr200109.graphml', 'Internode.graphml', 'Amres.graphml', 'Rediris.graphml', 'Rnp.graphml', 'Uninett2011.graphml', 'Garr201008.graphml', 'TLex.graphml', 'Iij.graphml', 'Belnet2006.graphml', 'Cesnet2001.graphml', 'Nordu2005.graphml', 'Garr200212.graphml', 'Esnet.graphml', 'Garr199905.graphml', 'Forthnet.graphml', 'Vinaren.graphml', 'Garr201103.graphml', 'Reuna.graphml', 'PionierL3.graphml', 'Garr201101.graphml', 'Garr200902.graphml', 'Belnet2003.graphml', 'Uninett2010.graphml', 'Eenet.graphml', 'Bren.graphml', 'Garr201010.graphml', 'Belnet2004.graphml', 'Garr201102.graphml', 'Marnet.graphml', 'Garr201109.graphml', 'Cesnet200706.graphml', 'Garr200909.graphml', 'Garr201007.graphml', 'Renater2008.graphml', 'Garr201005.graphml', 'Cernet.graphml', 'Cesnet1993.graphml', 'Garr200404.graphml']
        for file_name in internet_toplogy_files[:1]:
            substrate_graph = generate_internet_topology_graph(join(dir_path, file_name))
            found_flow, capacity = min_congestion(substrate_graph, flow, edge_demand)
            if not found_flow:
                print(f"Couldn't find a min cost flow for the graph. Maximum flow: {capacity}")
    elif topology == "clos":
        substrate_graph = generate_clos_topology_graph()
    elif topology == "bcube":
        substrate_graph = generate_bcube_topology_graph()
    elif topology == "xpander":
        substrate_graph = generate_xpander_topology_graph()
    elif topology == "random":
        while True:
            substrate_graph = generate_random_graph()
            found_flow, _ = min_congestion(substrate_graph, flow, edge_demand)
            if found_flow:
                return
    else:
        print(f"We don't support {topology} topology right now.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minimum Congestion algorithm", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-t", "--topology", choices=ALLOWED_TOPOLOGIES, help="Topology", type=str.lower)
    args = parser.parse_args()
    config = vars(args)
    min_congestion_star_workload(config.get("topology", None))
