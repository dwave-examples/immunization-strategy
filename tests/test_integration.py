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

import os
import subprocess
import sys
import unittest
import demo
from dwave.system import LeapHybridDQMSampler

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestDemo(unittest.TestCase):

    def test_smoke(self):
        """run demo.py and check that nothing crashes"""

        demo_file = os.path.join(project_dir, 'demo.py')
        subprocess.check_output([sys.executable, demo_file])

    # Test that the graph edge case constructions are caught
    def test_karate_graph(self):
        args = demo.read_in_args(["--graph", "karate", "--nodes", "1", "--degree", "3", "--prob", "1.2", "--new-edges", "1001"])
        G = demo.build_graph(args)
        self.assertEqual(len(G.nodes()), 34)

    def test_internet_graph_too_small(self):
        args = demo.read_in_args(["--graph", "internet", "--nodes", "1", "--degree", "3", "--prob", "1.2", "--new-edges", "1001"])
        G = demo.build_graph(args)
        self.assertEqual(len(G.nodes()), 1000)

    def test_internet_graph_too_big(self):
        args = demo.read_in_args(["--graph", "internet", "--nodes", "100001", "--degree", "3", "--prob", "1.2", "--new-edges", "1001"])
        G = demo.build_graph(args)
        self.assertEqual(len(G.nodes()), 1000)

    def test_rr_graph(self):
        args = demo.read_in_args(["--graph", "rand-reg", "--nodes", "1", "--degree", "3", "--prob", "1.2", "--new-edges", "1001"])
        G = demo.build_graph(args)
        self.assertEqual(len(G.nodes()), 1)

    def test_er_graph(self):
        args = demo.read_in_args(["--graph", "ER", "--nodes", "0", "--degree", "3", "--prob", "1.2", "--new-edges", "1001"])
        G = demo.build_graph(args)
        self.assertEqual(len(G.nodes()), 1000)

    def test_sf_graph(self):
        args = demo.read_in_args(["--graph", "SF", "--nodes", "0", "--degree", "3", "--prob", "1.2", "--new-edges", "1001"])
        G = demo.build_graph(args)
        self.assertEqual(len(G.nodes()), 1000)

    def test_illegal_edges(self):
        """Run demo.py and check that no illegal edges are reported. This ensures the lagrange parameter is set appropriately."""
        args = demo.read_in_args(["--graph", "internet"])
        G = demo.build_graph(args)
        dqm = demo.build_dqm(G)
        sampler = LeapHybridDQMSampler()
        sample = demo.run_dqm_and_collect_solutions(dqm, sampler)

        group_1, group_2, sep_group, illegal_edges = demo.process_sample(G, sample)

        self.assertEqual(len(illegal_edges), 0)

if __name__ == '__main__':
    unittest.main()
