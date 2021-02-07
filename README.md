# Building Placements Generation in OpenStreetMap

This repository contains the code for the manuscript Building Placements Generation in OpenStreetMap and the code used for the experiment.

Contents:

Main code: ```/generator```  
Manuscript: ```/manuscript```  

## How to run the code in this repository?

1 - Create a conda environment using the environment file running:

```conda env create -f environment.yml```

2 - Invoke the created conda environment with:

```conda activate experiment_env```

3 - You can run the main code by navigating to ```/generator``` and running:

```python3 generation_mapelites.py```

## How to reproduce the experiment?

After creating the environment and activating it, navigate to ```/generator``` and run:

```python3 experiment.py```

## Folder structure
```
.
└── CityGen
    ├── generator                     # main repository folder
    │   ├── classifier
    │   │   ├── model.py
    │   │   ├── Validator.py
    │   │   ├── Tokyo.hdf5
    │   │   └── Tsukuba.hdf5
    │   ├── data                      # input data for the system
    │   │   ├── smaller_tsukuba.osm
    │   │   └── sumidaku.osm
    │   ├── lib                       # modules used by the main script
    │   │   ├── mapelites
    │   │   │   ├── evolution.py
    │   │   │   └── Individual.py
    │   │   ├── __init__.py
    │   │   ├── building.py
    │   │   ├── handler.py
    │   │   ├── helper.py
    │   │   ├── logger.py
    │   │   ├── Map.py
    │   │   ├── obb.p
    │   │   ├── parcel.py
    │   │   ├── plotter.py
    │   │   ├── settings.py
    │   │   └── trigonometry.py
    │   ├── experiment.py             # experiment standalone script
    │   └── generation_mapelites.py   # main system script
    ├── manuscript              
    │   └── manuscript.pdf            # manuscript describing the system
    ├── LICENSE
    ├── README.md
    ├── setup.py                      # require setup file so scripts can find all the libraries
    └── environment.yml               # environment description containg all required libraries
```
