import math
import networkx as nx
import os

from functools import partial
from matplotlib import pyplot as plt, animation
from networkx.drawing.nx_pydot import graphviz_layout


class DrawGraphs:
    excluded_attributes = ["color", "is_switch"]

    def __init__(self, graph, with_labels=False, title=None, layout=None, path=None):
        self.figure_number = 0
        self.graph = graph
        self.title = title
        self.with_labels = with_labels
        self.figure = None
        self.ani = None
        self.path=path
        self.__generate_graph_position(layout)
        self.add_graph()

    def __generate_graph_position(self, layout):
        if layout == "circular":
            self.pos = nx.circular_layout(self.graph)
        elif layout == "tree":
            self.pos = graphviz_layout(self.graph, prog="dot")
        else:
            self.pos = nx.spring_layout(self.graph, k=10)

    def draw(self):
        if self.path:
            directories = "/".join(self.path.split("/")[:-1])
            if not os.path.exists(directories):
                os.makedirs(directories)
            plt.savefig(self.path)
            plt.clf()
        else:
            plt.show()
        self.figure_number = 0

    def __add_figure_details(self):
        self.figure_number += 1
        self.figure = plt.figure(self.figure_number, figsize=(20, 10))
        if not self.title:
            self.title = f"Figure {self.figure_number}"
        plt.title(self.title)

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

    def __extract_attribute_values(self, attributes, values):
        temp = list()
        for key in attributes:
            temp.append(values.get(key, self.__default_values(key)))
        return temp

    def __draw_table(self):
        node_data = dict(self.graph.nodes(data=True))
        attributes = list(set(self.__get_attributes(node_data)) - set(self.excluded_attributes))
        if attributes:
            plt.table([(["node", ] + attributes), ] + [[node, ]+self.__extract_attribute_values(attributes, values) 
                                                         for node, values in node_data.items()])

        edge_data = self.graph.edges(data=True)
        attributes = list(set(self.__get_attributes(edge_data)) - set(self.excluded_attributes))
        if attributes:
            plt.table([(["start_node", "end_node"] + attributes), ] + 
                      [[u, v]+self.__extract_attribute_values(attributes, values) 
                       for u, v, values in edge_data])

    def __add_default_colors(self):
        # Node colors
        for _, values in self.graph.nodes(data=True):
            if values.get("color", None):
                continue
            if values.get("is_switch", False):
                values.update({"color": "g"})
            else:
                values.update({"color": "b"})

        # Edge colors
        for _, _, values in self.graph.edges(data=True):
            if values.get("color", None):
                continue
            values.update({"color": "k"})

    def add_graph(self):
        self.__add_figure_details()
        self.__add_default_colors()
        labels = dict()
        if self.with_labels:
            self.__draw_table()
            edge_color = nx.get_edge_attributes(self.graph, "color").values()
            if edge_color:
                labels.update({"edge_color": edge_color})
            node_color = nx.get_node_attributes(self.graph, "color").values()
            if node_color:
                labels.update({"node_color": node_color})
        nx.draw(self.graph, self.pos, with_labels=True, **labels)

    def __init_animation(self):
        pass

    def __add_flow(self, updated_details, colored_edges, frame):
        self.figure.clear()
        u, v, values = updated_details[frame]
        if self.graph.has_edge(v, u):
            self.graph.remove_edge(v, u)
        self.graph[u][v]["color"] = "r"
        colored_edges.update({(u, v): values.get("capacity")})
        nx.draw(self.graph, self.pos, with_labels=True, edge_color=nx.get_edge_attributes(self.graph, "color").values())
        if colored_edges:
            nx.draw_networkx_edge_labels(self.graph, self.pos, edge_labels=colored_edges, font_color="r")

    def add_flow(self, flow_graph):
        updated_details = [(u, v, values) for u, v, values in flow_graph.edges(data=True)]
        colored_edges = dict()
        frames = len(nx.get_edge_attributes(flow_graph, "capacity"))
        if self.path:
            for frame in range(frames):
                self.__add_flow(updated_details, colored_edges, frame)
        else:
            self.ani = animation.FuncAnimation(self.figure, partial(self.__add_flow, updated_details, colored_edges), frames=frames, 
                                               interval=1000, repeat=False, init_func=self.__init_animation)


def from_min_cost_flow(flow_dict, flow_graph):
    G = nx.DiGraph()
    total_cost = 0
    total_capacity = 0
    substrate_edges = flow_graph.edges()
    for node in flow_dict.keys():
        G.add_node(node)
    for u, values in flow_dict.items():
        for v, capacity in values.items():
            if capacity != 0:
                weight = substrate_edges[u, v]["weight"]
                G.add_edge(u, v, capacity=capacity, weight=weight)
                total_cost += weight*capacity
                if u == "source":
                    total_capacity += capacity
    return G, total_cost, total_capacity
