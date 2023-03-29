import csv
import json
import math
import networkx as nx
import os
import random

from functools import partial
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from matplotlib import pyplot as plt, animation
from networkx.drawing.nx_pydot import graphviz_layout
from oauth2client.service_account import ServiceAccountCredentials


class DrawGraphs:
    excluded_attributes = ["color", "is_switch"]

    def __init__(self, graph, with_labels=False, title=None, layout=None, path=None):
        self.figure_number = 0
        self.graph = graph
        self.title = title
        self.with_labels = with_labels
        self.figure = None
        self.ani = list()
        self.path = path
        self.cmap = plt.cm.get_cmap("hsv", 50)
        self.flow_counter = 0
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
            create_directories(self.path)
            plt.savefig(f"{self.path}.png")
            plt.clf()
        else:
            plt.show()
        self.figure_number = 0

    def add_title(self, title=None):
        if title:
            self.title = title
        plt.title(self.title)

    def __add_figure_details(self):
        self.figure_number += 1
        self.figure = plt.figure(self.figure_number, figsize=(20, 10))
        if not self.title:
            self.title = f"Figure {self.figure_number}"
        self.add_title()

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
        attributes = list(
            set(self.__get_attributes(node_data)) - set(self.excluded_attributes)
        )
        if attributes:
            plt.table(
                [(["node"] + attributes)]
                + [
                    [node] + self.__extract_attribute_values(attributes, values)
                    for node, values in node_data.items()
                ]
            )

        edge_data = self.graph.edges(data=True)
        attributes = list(
            set(self.__get_attributes(edge_data)) - set(self.excluded_attributes)
        )
        if attributes:
            plt.table(
                [(["start_node", "end_node"] + attributes)]
                + [
                    [u, v] + self.__extract_attribute_values(attributes, values)
                    for u, v, values in edge_data
                ]
            )

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

    def __draw(self):
        labels = dict()
        if self.with_labels:
            # self.__draw_table()
            edge_color = nx.get_edge_attributes(self.graph, "color").values()
            if edge_color:
                labels.update({"edge_color": edge_color})
            node_color = nx.get_node_attributes(self.graph, "color").values()
            if node_color:
                labels.update({"node_color": node_color})
        nx.draw(self.graph, self.pos, with_labels=True, **labels)

    def add_graph(self):
        self.__add_figure_details()
        self.__add_default_colors()
        self.__draw()

    def __init_animation(self):
        pass

    def __add_flow(self, updated_details, color, frame):
        u, v = updated_details[frame]
        if "sink" not in [u, v]:
            self.graph[u][v]["color"] = color
        self.figure.clear()
        self.add_title()
        self.__draw()

    def add_flow(self, flow_graph, source):
        color = self.cmap(self.flow_counter)
        updated_details = list(flow_graph.edges())
        self.graph.nodes().get(source).update({"color": color})
        frames = len(nx.get_edge_attributes(flow_graph, "capacity"))
        if self.path:
            for frame in range(frames):
                self.__add_flow(updated_details, color, frame)
        else:
            self.ani.append(
                animation.FuncAnimation(
                    self.figure,
                    partial(self.__add_flow, updated_details, color),
                    frames=frames,
                    interval=1000,
                    repeat=False,
                    init_func=self.__init_animation,
                )
            )
        self.flow_counter += 1


def create_directories(path):
    directories = "/".join(path.split("/")[:-1])
    if not os.path.exists(directories):
        os.makedirs(directories)


def from_min_cost_flow(flow_dict, flow_graph):
    G = nx.DiGraph()
    total_cost = 0
    substrate_edges = flow_graph.edges()
    for node in flow_dict.keys():
        G.add_node(node)
    for u, values in flow_dict.items():
        for v, load in values.items():
            if load != 0:
                weight = substrate_edges[u, v]["weight"]
                G.add_edge(u, v, load=load, weight=weight)
                total_cost += weight * load
    return G, total_cost


def write_to_csv(file_name, fields, data):
    with open(file_name, "a") as csv_file:
        writer = csv.DictWriter(csv_file, fields)
        writer.writeheader()
        writer.writerows(data)


def save_flow_details(substrate_graph, flow_graph, flow, cost, path=None):
    if not path:
        return

    path = f"{path}.csv"
    create_directories(path)

    # Write flow, cost
    with open(path, "w") as csv_file:
        csv_file.write(f"Flow: {flow}\n")
        csv_file.write(f"Cost: {cost}\n")

    if substrate_graph:
        with open(path, "a") as csv_file:
            csv_file.write("\n\nSubstrate Node Data\n")

        # Write Node data
        fields = set()
        data = list()
        for source, details in substrate_graph.nodes(data=True):
            fields.update(details.keys())
            data.append({"source": source, **details})
        write_to_csv(path, ["source"] + list(fields), data)

        with open(path, "a") as csv_file:
            csv_file.write("\n\nSubstrate Edge Data\n")

        # Write Edge data
        fields = set()
        data = list()
        substrate_data = nx.to_dict_of_dicts(substrate_graph)
        for source, values in substrate_data.items():
            for dest, details in values.items():
                fields.update(details.keys())
                data.append({"source": source, "destination": dest, **details})
        write_to_csv(path, ["source", "destination"] + list(fields), data)

    if flow_graph:
        with open(path, "a") as csv_file:
            csv_file.write("\n\nFlow Data\n")

        # Write flow dict
        fields = ["source", "destination", "capacity", "weight", "load"]
        data = list()
        flow_data = nx.to_dict_of_dicts(flow_graph)
        for source, values in flow_data.items():
            for dest, details in values.items():
                data.append({"source": source, "destination": dest, **details})
        write_to_csv(path, fields, data)


def get_google_drive_folder_id(topology):
    with open("config.json", "r") as config_file:
        config = json.load(config_file)
    folder_id = config.get(topology, None)
    if not folder_id:
        folder_id = config.get("folder_id", None)
    if not folder_id:
        print("Folder id missing from config.json file.")
    return folder_id


def connect_to_gdrive():
    gauth = GoogleAuth()
    scope = ["https://www.googleapis.com/auth/drive"]
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        "client_secrets.json", scope
    )
    return GoogleDrive(gauth)


def upload_to_google_drive(path, folder_id):
    drive = connect_to_gdrive()
    filename_prefix = "_".join(path.split("/")[1:])
    for file in os.listdir(path):
        gfile = drive.CreateFile(
            {"title": f"{filename_prefix}_{file}", "parents": [{"id": folder_id}]}
        )
        gfile.SetContentFile(f"{path}/{file}")
        gfile.Upload()


def read_from_google_drive(folder_id):
    drive = connect_to_gdrive()
    files = drive.ListFile(
        {"q": f"'{folder_id}' in parents and trashed=false"}
    ).GetList()
    min_cost = math.inf
    min_files = list()
    for file in files:
        filename = file.get("title")
        if filename.endswith(".csv"):
            file_id = file.get("id")
            gfile = drive.CreateFile({"id": file_id})
            resp = gfile.GetContentString()
            cost = resp.split("\n")[1].split(": ")[1]
            if cost == "inf":
                continue
            cost = int(cost)
            if cost == min_cost:
                min_files.append(filename)
            if cost < min_cost:
                min_files = [filename]
    return min_files


def fetch_minimum_costs(folder_ids=None):
    min_flow_dict = dict()
    if not folder_ids:
        with open("config.json", "r") as config_file:
            folder_ids = json.load(config_file)
    for flow, folder_id in folder_ids.items():
        min_flow_dict.update({flow: read_from_google_drive(folder_id)})
    return min_flow_dict
