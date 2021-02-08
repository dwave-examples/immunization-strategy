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
import argparse
import matplotlib
try:
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib.use("agg")
    import matplotlib.pyplot as plt

def read_in_args():
    """ Read in user specified parameters or use defaults."""

    # Set up user-specified optional arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--graph", default='karate', choices=['karate', 'internet', 'HEP'], help='Graph to partition (default: %(default)s)')
    parser.add_argument("-n", "--nodes", help="Set graph size for internet graph. Must be between 1000 and 10000. (default: %(default)s)", default=1000, type=int)

    args = parser.parse_args()
    
    if args.graph == 'karate':
        print("\nReading in karate graph...")
        G = nx.karate_club_graph()
    elif args.graph == 'internet':
        if args.nodes < 1000 or args.nodes > 10000:
            args.nodes = 1000
            print("\nSize for internet graph must be between 1000 and 10000.\nSetting size to 1000.\n")
        print("\nReading in internet graph of size", args.nodes, "...")
        G = nx.random_internet_as_graph(args.nodes)
    elif args.graph == 'HEP':
        print("\nReading in HEP graph (this will take a while)...")
        G = nx.read_pajek("hep-th-new.net")

    return G

# Visualize the input graph
def visualize_input_graph(G):
    """ Visualize graph to be partitioned."""

    pos = nx.spring_layout(G)
    nx.draw_networkx_nodes(G, pos, node_size=20, node_color='r', edgecolors='k')
    nx.draw_networkx_edges(G, pos, edgelist=G.edges(), style='solid', edge_color='#808080')
    plt.draw()
    plt.savefig('input_graph.png')
    plt.close()

def build_dqm(G):
    """ Build the DQM for the problem instance."""

    # Two groups (cases 0, 1) and one separator group (case 2)
    num_groups = 3

    # Lagrange parameter on constraints
    gamma_1 = 1
    gamma2 = 100

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
    for i in range(len(all_nodes_ordered)):
        dqm.set_linear_case(all_nodes_ordered[i], 0, gamma_1)
        dqm.set_linear_case(all_nodes_ordered[i], 1, gamma_1)
        for j in range(i+1, len(all_nodes_ordered)):
            dqm.set_quadratic_case(all_nodes_ordered[i], 0, all_nodes_ordered[j], 0, 2*gamma_1)
            dqm.set_quadratic_case(all_nodes_ordered[i], 1, all_nodes_ordered[j], 1, 2*gamma_1)
            dqm.set_quadratic_case(all_nodes_ordered[i], 0, all_nodes_ordered[j], 1, -2*gamma_1)
            dqm.set_quadratic_case(all_nodes_ordered[i], 1, all_nodes_ordered[j], 0, -2*gamma_1)

    # Add constraint to DQM: e(G1, G2) = 0
    for a, b in G.edges():
        if a != b:
            dqm.set_quadratic_case(a, 0, b, 1, gamma2)
            dqm.set_quadratic_case(a, 1, b, 0, gamma2)

    return dqm

def run_dqm_and_collect_solutions(dqm, sampler):
    """ Send the DQM to the sampler and return the best sample found."""

    # Initialize the solver
    print("\nSending to the solver...")
    
    # Solve the DQM problem using the solver
    sampleset = sampler.sample_dqm(dqm, label='Example - Immunization Strategy')

    # Get the first solution, and print it
    sample = sampleset.first.sample

    return sample

def process_sample(G, sample):
    """ Interpret the DQM solution in terms of the partitioning problem."""

    # Display results to user
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

    print("\nSeparator Fraction: \t", len(sep_group)/len(G.nodes()))

    illegal_edges = [(u, v) for u, v in G.edges if ({sample[u], sample[v]} == {0, 1})]

    print("\nNumber of illegal edges:\t", len(illegal_edges))

    return group_1, group_2, sep_group, illegal_edges

def visualize_results(G, group_1, group_2, sep_group, illegal_edges):
    """ Visualize the partition."""

    print("\nVisualizing output...")

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

if __name__ == '__main__':

    G = read_in_args()

    visualize_input_graph(G)

    dqm = build_dqm(G)

    sampler = LeapHybridDQMSampler()
    sample = run_dqm_and_collect_solutions(dqm, sampler)

    group_1, group_2, sep_group, illegal_edges = process_sample(G, sample)

    visualize_results(G, group_1, group_2, sep_group, illegal_edges)
