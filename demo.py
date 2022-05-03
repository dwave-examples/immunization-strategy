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

import argparse
import sys
import matplotlib
import networkx as nx
from dimod import ConstrainedQuadraticModel, Binary, quicksum
from dwave.system import LeapHybridCQMSampler

try:
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib.use("agg")
    import matplotlib.pyplot as plt

def read_in_args(args):
    """ Read in user specified parameters."""

    # Set up user-specified optional arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--graph", default='internet', choices=['karate', 'internet', 'rand-reg', 'ER', 'SF'], help='Graph to partition (default: %(default)s)')
    parser.add_argument("-n", "--nodes", help="Set graph size for graph. (default: %(default)s)", default=1000, type=int)
    parser.add_argument("-d", "--degree", help="Set node degree for random regular graph. (default: %(default)s)", default=4, type=int)
    parser.add_argument("-p", "--prob", help="Set graph edge probability for ER graph. Must be between 0 and 1. (default: %(default)s)", default=0.25, type=float)
    parser.add_argument("-e", "--new-edges", help="Set number of edges from new node to existing node in SF graph. (default: %(default)s)", default=4, type=int)

    return parser.parse_args(args)

def build_graph(args):
    """ Builds graph from user specified parameters or use defaults."""

    max_vars = int(5000/3)
    
    # Build graph using networkx
    if args.graph == 'karate':
        print("\nReading in karate graph...")
        G = nx.karate_club_graph()
    elif args.graph == 'internet':
        if args.nodes < 1000 or args.nodes > max_vars:
            args.nodes = 1000
            print("\nSize for internet graph must be between 1000 and " + str(max_vars) + ". Setting size to 1000.\n")
        print("\nReading in internet graph of size", args.nodes, "...")
        G = nx.random_internet_as_graph(args.nodes)
    elif args.graph == 'rand-reg':
        if args.nodes < 1 or args.nodes > max_vars:
            print("\nSize for random regular graph must be between 1 and " + str(max_vars) + ". Setting size to 1000.\n")
        if args.degree < 0 or args.degree >= args.nodes:
            print("\nDegree must be between 0 and n-1. Setting size to min(4, n-1).\n")
            args.degree = min(4, args.nodes-1)
        if args.degree*args.nodes % 2 == 1:
            print("\nRequirement: n*d must be even.\n")
            if args.degree > 0:
                args.degree -= 1
                print("\nSetting degree to", args.degree, "\n")
            elif args.nodes-1 > args.degree:
                args.nodes -= 1
                print("\nSetting nodes to", args.nodes, "\n")
            else:
                print("\nSetting nodes to 1000 and degree to 4.\n")
                args.nodes = 1000
                args.degree = 4
        print("\nGenerating random regular graph...")
        G = nx.random_regular_graph(args.degree, args.nodes)
    elif args.graph == 'ER':
        if args.nodes < 1 or args.nodes > max_vars:
            print("\nSize for ER graph must be between 1 and " + str(max_vars) + ". Setting size to 1000.\n")
            args.nodes = 1000
        if args.prob < 0 or args.prob > 1:
            print("\nProbability must be between 0 and 1. Setting prob to 0.25.\n")
            args.prob = 0.25
        print("\nGenerating Erdos-Renyi graph...")
        G = nx.erdos_renyi_graph(args.nodes, args.prob)
    elif args.graph == 'SF':
        if args.nodes < 1 or args.nodes > max_vars:
            print("\nSize for SF graph must be between 1 and " + str(max_vars) + ". Setting size to 1000.\n")
            args.nodes = 1000
        if args.new_edges < 0 or args.new_edges > args.nodes:
            print("\nNumber of edges must be between 1 and n. Setting to 5.\n")
            args.new_edges = 5
        print("\nGenerating Barabasi-Albert scale-free graph...")
        G = nx.barabasi_albert_graph(args.nodes, args.new_edges)
    else:
        print("\nReading in karate graph...")
        G = nx.karate_club_graph()

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

def build_cqm(G):
    """ Build the CQM for the problem instance."""

    # Two groups (cases 0, 1) and one separator group (case 2)
    num_groups = 3

    # Initialize the CQM object
    print("\nBuilding CQM...")
    cqm = ConstrainedQuadraticModel()

    # Build the CQM starting by creating variables
    vars = [[Binary(f'x_{name}_{i}') for i in range(num_groups)] for name in G.nodes()]

    # Set objective for CQM
    cqm.set_objective(quicksum(vars[i][2] for i in range(len(vars))))

    # Add constraint to make variables discrete
    for v in range(len(vars)):
        cqm.add_discrete([f'x_{v}_{i}' for i in range(num_groups)])

    # Add constraint to CQM: |G1|=|G2|
    g1 = [vars[i][0] for i in range(len(vars))]
    g2 = [vars[i][1] for i in range(len(vars))]
    cqm.add_constraint(quicksum(g1) - quicksum(g2) == 0)

    # Add constraint to CQM: e(G1, G2) = 0
    edge_sum = []
    for a, b in G.edges():
        if a != b:
            edge_sum.append(vars[a][0]*vars[b][1]+vars[a][1]*vars[b][0])
    cqm.add_constraint(quicksum(edge_sum) == 0, label='cross edges')

    return cqm

def run_cqm_and_collect_solutions(cqm, sampler):
    """ Send the CQM to the sampler and return the best sample found."""

    # Initialize the solver
    print("\nSending to the solver...")
    
    # Solve the CQM problem using the solver
    sampleset = sampler.sample_cqm(cqm, label='Example - Immunization Strategy')

    # Get the first feasible solution
    feasible_sampleset = sampleset.filter(lambda d: d.is_feasible)
    if len(feasible_sampleset) == 0:
        print("\nNo feasible solution found. Returning best infeasible solution.")
        return sampleset.first.sample

    return feasible_sampleset.first.sample

def process_sample(G, sample):
    """ Interpret the CQM solution in terms of the partitioning problem."""

    # Display results to user
    group_1 = []
    group_2 = []
    sep_group = []
    results = [[],[],[]]
    for key, val in sample.items():
        if val == 1:
            v = key.split("_")
            results[int(v[-1])].append(int(v[1]))

    group_1 = results[0]
    group_2 = results[1]
    sep_group = results[2]

    # Display best result
    print("\nPartition Found:")
    print("\tGroup 1: \tSize", len(group_1))
    print("\tGroup 2: \tSize", len(group_2))
    print("\tSeparator: \tSize", len(sep_group))

    print("\nSeparator Fraction: \t", len(sep_group)/len(G.nodes()))

    # Determines if there are any edges directly between the large groups
    illegal_edges = [(u, v) for u, v in G.edges if (sample[f'x_{u}_{0}']*sample[f'x_{v}_{1}'] == 1 or sample[f'x_{u}_{1}']*sample[f'x_{v}_{0}'] == 1)]

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
    pos = {**pos_1, **pos_2, **pos_sep}

    nx.draw_networkx_nodes(G, pos_1, node_size=10, nodelist=group_1, node_color='#17bebb', edgecolors='k')
    nx.draw_networkx_nodes(G, pos_2, node_size=10, nodelist=group_2, node_color='#2a7de1', edgecolors='k')
    nx.draw_networkx_nodes(G, pos_sep, node_size=10, nodelist=sep_group, node_color='#f37820', edgecolors='k')

    nx.draw_networkx_edges(G, pos, edgelist=G.edges(), style='solid', edge_color='#808080')
    nx.draw_networkx_edges(G, pos, edgelist=illegal_edges, style='solid')

    plt.draw()
    output_name = 'separator.png'
    plt.savefig(output_name)

    print("\tOutput stored in", output_name)

if __name__ == '__main__':

    args = read_in_args(sys.argv[1:])

    G = build_graph(args)

    visualize_input_graph(G)

    cqm = build_cqm(G)

    sampler = LeapHybridCQMSampler()
    sample = run_cqm_and_collect_solutions(cqm, sampler)

    group_1, group_2, sep_group, illegal_edges = process_sample(G, sample)

    visualize_results(G, group_1, group_2, sep_group, illegal_edges)
