import math
import matplotlib.pyplot as plt
import networkx as nx


class DrawGraphs:

    def __init__(self) -> None:
        self.figure_number = 0

    def draw(self):
        plt.show()
        self.figure_number = 0

    def __add_figure_details(self, title):
        self.figure_number += 1
        plt.figure(self.figure_number)
        if title:
            plt.title(title)
        else:
            plt.title(f"Figure {self.figure_number}")

    def add_graph(self, graph, with_labels=False, title=None):
        self.__add_figure_details(title)
        pos = nx.spring_layout(graph)
        if with_labels:
            node_labels = dict()
            node_data = dict(graph.nodes(data=True))
            for node, values in node_data.items():
                node_labels.update({
                    node: f"{str(node)}: {values.get('capacity', 0)}, {values.get('weight', math.inf)}, {values.get('demand', 0)}"
                })
            edge_labels = dict()
            edge_data = graph.edges(data=True)
            for u, v, values in edge_data:
                edge_labels.update({
                    (u, v): f"{values.get('capacity', 0)}, {values.get('weight', math.inf)}"
                })
            nx.draw(graph, pos, with_labels=True, labels=node_labels)
            nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels)
        else:
            nx.draw(graph, pos)

def from_min_cost_flow(flowDict):
    G = nx.DiGraph()
    total_cost = 0
    for node in flowDict.keys():
        G.add_node(node)
    for u, values in flowDict.items():
        for v, w in values.items():
            if w != 0:
                G.add_edge(u, v, weight=w)
                total_cost += w
    return G, total_cost
