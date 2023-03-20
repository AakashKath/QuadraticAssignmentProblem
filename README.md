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
3. Create `dataset/internet` directory to add graphs for internet topology.
4. Run `python algorithm.py [-t/--topology <topology>] [-sg/--save_graph] [-sd/--save_drive]`
5. To save all the results to google drive.
    1. [Create a project](https://d35mpxyw7m7k7g.cloudfront.net/bigdata_1/Get+Authentication+for+Google+Service+API+.pdf) in google cloud.
    2. [Create a service](https://cloud.google.com/iam/docs/service-accounts-create) account to avoid authorization before run.
    3. Save service account key as `client_sercets.json`.
    4. Get folder_id from Google drive URL.
    5. Add `{"folder_id": $folder_id_fetched_from_url}` in config.json.
```
Note: Currently we support only Internet Topology. Clos, Bcube, and Xpander topologies will be added in next iterations.
```
