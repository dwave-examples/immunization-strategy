# Copyright 2021 D-Wave Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dimod import DiscreteQuadraticModel
from dwave.system import LeapHybridDQMSampler
import networkx as nx
import matplotlib.pyplot as plt
import igraph as ig

print("\nReading in graph...")

# Karate club graph: 33 nodes
# G = nx.karate_club_graph()

# Internet AS network graph
G = nx.random_internet_as_graph(1000)

# HEP graph (HUGE and slow)
# G = nx.read_pajek("hep-th-new.net")

# Visualize the input graph
g1 = ig.Graph(len(G), list(zip(*list(zip(*nx.to_edgelist(G)))[:2])))
layout = g1.layout("kk")
visual_style = {}
visual_style["vertex_size"] = 10
visual_style["edge_color"] = ["gray"]
ig.plot(g1, "input_graph.png", **visual_style)

# Two groups (cases 0, 1) and one separator group (case 2)
num_groups = 3

# Lagrange parameter on constraint
gamma = 1

# Initialize the DQM object
print("\nBuilding DQM...")
dqm = DiscreteQuadraticModel()

# Build the DQM starting by adding variables
for name in G.nodes():
    dqm.add_variable(num_groups, label=name)

# Add objective to DQM
for name in G.nodes():
    dqm.set_linear_case(name, 2, 1)

# Add constraint to DQM: |G1|=|G2|
all_nodes_ordered = list(G.nodes())
# print(all_nodes_ordered[0])
for i in range(len(all_nodes_ordered)):
    dqm.set_linear_case(all_nodes_ordered[i], 0, gamma)
    dqm.set_linear_case(all_nodes_ordered[i], 1, gamma)
    for j in range(i+1, len(all_nodes_ordered)):
        dqm.set_quadratic_case(all_nodes_ordered[i], 0, all_nodes_ordered[j], 0, 2*gamma)
        dqm.set_quadratic_case(all_nodes_ordered[i], 1, all_nodes_ordered[j], 1, 2*gamma)
        dqm.set_quadratic_case(all_nodes_ordered[i], 0, all_nodes_ordered[j], 1, -2*gamma)
        dqm.set_quadratic_case(all_nodes_ordered[i], 1, all_nodes_ordered[j], 0, -2*gamma)

# Add constraint to DQM: e(G1, G2) = 0
gamma2 = 100
for a, b in G.edges():
    if a != b:
        dqm.set_quadratic_case(a, 0, b, 1, gamma2)
        dqm.set_quadratic_case(a, 1, b, 0, gamma2)

# Initialize the DQM solver
print("\nSending to the DQM solver...")
sampler = LeapHybridDQMSampler()

# Solve the problem using the DQM solver
sampleset = sampler.sample_dqm(dqm, label='Example - Immunization Strategy')

# Get the first solution, and print it
sample = sampleset.first.sample
energy = sampleset.first.energy

# Visualize output
print("\nVisualizing output...")
group_1 = []
group_2 = []
sep_group = []
for key, val in sample.items():
    if val == 0:
        group_1.append(key)
    elif val == 1:
        group_2.append(key)
    else:
        sep_group.append(key)

# Display best result
print("\nPartition Found:")
print("\tGroup 1: \tSize", len(group_1))
print("\tGroup 2: \tSize", len(group_2))
print("\tSeparator: \tSize", len(sep_group))

illegal_edges = [(u, v) for u, v in G.edges if ({sample[u], sample[v]} == {0, 1})]

print("\nNumber of illegal edges:\t", len(illegal_edges))

G1 = G.subgraph(group_1)
G2 = G.subgraph(group_2)
SG = G.subgraph(sep_group)

pos_1 = nx.random_layout(G1, center=(-5,0))
pos_2 = nx.random_layout(G2, center=(5,0))
pos_sep = nx.random_layout(SG, center=(0,0))

# pos = nx.spring_layout(G)
pos = {**pos_1, **pos_2, **pos_sep}
nx.draw_networkx_nodes(G, pos_1, node_size=10, nodelist=group_1, node_color='#17bebb', edgecolors='k')
nx.draw_networkx_nodes(G, pos_2, node_size=10, nodelist=group_2, node_color='#2a7de1', edgecolors='k')
nx.draw_networkx_nodes(G, pos_sep, node_size=10, nodelist=sep_group, node_color='#f37820', edgecolors='k')

nx.draw_networkx_edges(G, pos, edgelist=G.edges(), style='solid', edge_color='#808080')
nx.draw_networkx_edges(G, pos, edgelist=illegal_edges, style='solid')
plt.draw()
plt.savefig('separator.png')
