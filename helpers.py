import math
import networkx as nx

from functools import partial
from matplotlib import pyplot as plt, animation


class DrawGraphs:

    def __init__(self, graph, with_labels=False, title=None) -> None:
        self.figure_number = 0
        self.graph = graph
        self.title = title
        self.with_labels = with_labels
        self.figure = None
        self.pos = nx.spring_layout(self.graph, k=10)
        self.ani = None
        self.add_graph()

    def draw(self):
        plt.show()
        self.figure_number = 0

    def __add_figure_details(self):
        self.figure_number += 1
        self.figure = plt.figure(self.figure_number, figsize=(20, 10))
        if self.title:
            plt.title(self.title)
        else:
            plt.title(f"Figure {self.figure_number}")

    def __default_values(self, key):
        if key.lower() in ["capacity", "demand"]:
            return 0
        if key.lower() in ["cost", "weight"]:
            return math.inf
        return -1
    
    def __get_attributes(self, entity):
        try:
            return list(set(sum([list(v.keys()) for _, v in entity.items()], [])))
        except AttributeError:
            return list(set(sum([list(v.keys()) for _, _, v in entity], [])))

    def __draw_table(self):
        node_data = dict(self.graph.nodes(data=True))
        attributes = self.__get_attributes(node_data)
        node_info = [(["node", ] + attributes), ]
        for node, values in node_data.items():
            temp = [node, ]
            for key in attributes:
                temp.append(values.get(key, self.__default_values(key)))
            node_info.append(temp)
        plt.table(node_info)

        edge_data = self.graph.edges(data=True)
        attributes = self.__get_attributes(edge_data)
        edge_info = [(["start_node", "end_node"] + attributes), ]
        for u, v, values in edge_data:
            temp = [u, v]
            for key in attributes:
                temp.append(values.get(key, self.__default_values(key)))
            edge_info.append(temp)
        plt.table(edge_info)

    def add_graph(self):
        self.__add_figure_details()
        if self.with_labels:
            self.__draw_table()
        nx.draw(self.graph, self.pos, with_labels=True)

    def __init_animation(self):
        pass

    def __add_flow(self, updated_details, frame):
        u, v, values = updated_details[frame]
        if self.graph.has_edge(v, u):
            self.graph.remove_edge(v, u)
        if values.get("weight") > 0:
            self.graph[u][v]["color"] = "r"
        nx.draw(self.graph, self.pos, with_labels=True, edge_color=nx.get_edge_attributes(self.graph, "color").values())

    def add_flow(self, flow_graph):
        updated_details = [(u, v, values) for u, v, values in flow_graph.edges(data=True)]
        frames = len(nx.get_edge_attributes(flow_graph, "weight"))
        self.ani = animation.FuncAnimation(self.figure, partial(self.__add_flow, updated_details), frames=frames, 
                                           interval=2000, repeat=False, init_func=self.__init_animation)

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
