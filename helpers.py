import matplotlib.pyplot as plt
import networkx as nx


def draw_graph(graph, with_labels=False):
    pos = nx.spring_layout(graph)
    if with_labels:
        node_labels = {n: str(n) + ': ' + str(graph.nodes[n].get('weight', -1)) for n in
                                               graph.nodes}
        edge_labels = nx.get_edge_attributes(graph, 'weight')
        nx.draw(graph, pos, with_labels=True, labels=node_labels)
        nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels)
    else:
        nx.draw(graph, pos)
    plt.show()

def from_min_cost_flow(flowDict):
    G = nx.DiGraph()
    for node in flowDict.keys():
        G.add_node(node)
    for u, values in flowDict.items():
        for v, w in values.items():
            G.add_edge(u, v, weight=w)
    return G
