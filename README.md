# Immunization Strategy

There are many different strategies for immunizing populations in order to prevent transmission of a virus or an infectious disease with a minimal number of doses.  One such strategy, outlined in [1], is to fragment a population into separate groups via a "separator". This strategy partitions a population into two large groups of similar size and a smaller separator group. The separator is chosen so that all connections between the two larger groups pass through it. In this scenario, removing the separator  from the population disconnects the two large groups, preventing tramission of the infection between the groups. Immunizing the separator then breaks the transmission cycle, and so selecting a separator that contains as few individuals as possible will minimize the number of immunization doses required. In this example, we show how this optimization problem can be implemented using the Ocean SDK and solved using the hybrid discrete quadratic model solver available in Leap.

## Usage

To run the demo, type:

```python demo.py```

During a successful run of the program, two images are produced and saved. The first is the original input graph, saved as `input_graph.png`.

![Example Input](readme_imgs/input_graph.png)

The second highlights the partition of the population into large groups (left and right) and separator (center).

![Example Output](readme_imgs/separator.png)

## Code Overview

Given a population represented as a graph, the optimization problem can be broken down into the following objective and constraints.

- Objective: Minimize the number of nodes in the separator
- Constraint 1: Large groups have equal size
- Constraint 2: No edges between the large groups

This problem can be modeled as a discrete quadratic model (DQM). We assign a variable for each node in the graph, and each variable has three cases: one for each large group and one for the separator group. A variable can be assigned to exactly one of those three groups.

## References

[1] Chen, Yiping, et al. "Finding a better immunization strategy." Physical review letters 101.5 (2008): 058701.
