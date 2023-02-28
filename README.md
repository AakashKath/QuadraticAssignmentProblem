# Quadratic Assignment Problem
Implementation of Quadratic Assignment Problem using Minimum Congestion Algorithm by [Bansal et. al.](https://dl.acm.org/doi/10.1145/1993806.1993854)

```
Currently the code only supports random graph with no user input.
Substrate Graph- Random connected graph with random capacity and weights/costs.
Workload Graph- Star graph with random number of leaf nodes, random uniform edge demand and node demand of 1.
```

## How to use:
1. Create a pytohn [virtual environment](https://docs.python.org/3/library/venv.html)
2. Run `pip install -r requirments.txt`
3. Run `python algorithm.py`