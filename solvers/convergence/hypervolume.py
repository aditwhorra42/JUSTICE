from collections import defaultdict
import os
from ema_workbench.em_framework.optimization import ArchiveLogger, EpsilonProgress
from sklearn.preprocessing import MinMaxScaler
from deap.tools import _hypervolume
import numpy as np
import pandas as pd
from functools import partial
import multiprocessing
import datetime
from sklearn.preprocessing import MinMaxScaler
from itertools import chain
from solvers.convergence import pareto
from pathlib import Path
from typing import List, Tuple, Union

# Suppress warnings
import warnings


def calculate_hypervolume(maxima, generation):
    return _hypervolume.hv.hypervolume(generation, maxima)


def transform_data(data, scaler, direction_of_optimization=[]):

    # scale data
    transformed_data = scaler.transform(data)
    # Handle Directions # NOTE: This is not needed. The hypervolume calculation is already taking care of this
    # for i, direction in enumerate(direction_of_optimization):
    #     if direction == "max":
    #         transformed_data[:, i] = 1 - transformed_data[:, i]
    return transformed_data


def load_archives(
    list_of_objectives: List[str] = None,
    data_path: Union[str, Path] = None,
    file_name: str = None,
) -> Tuple[dict, List[pd.DataFrame]]:
    """
    Load archives from a tar.gz file containing multiple CSVs and extracts a list of DataFrames with relevant objective columns.

    Parameters
    ----------
    list_of_objectives : List[str]
        List of objective column names to extract from CSV files.
    data_path : str or Path
        Directory path containing the archive file.
    file_name : str
        Archive filename (tar.gz).

    Returns
    -------
    archives : dict
        Raw loaded archives dictionary.
    list_of_archives : List[pandas.DataFrame]
        List of DataFrames, one per generation, each containing only the selected objectives.
    """

    if list_of_objectives is None:
        raise ValueError("list_of_objectives cannot be None or empty.")
    if data_path is None:
        raise ValueError("data_path cannot be None.")
    if file_name is None:
        raise ValueError("file_name cannot be None.")

    full_path = Path(data_path) / file_name
    archives = ArchiveLogger.load_archives(str(full_path))

    list_of_archives = []
    num_objectives = len(list_of_objectives)

    print(f"Loading archives for {file_name}")

    for key, df in archives.items():
        # If "Unnamed: 0" exists, group by it. Otherwise, group by the index.
        group_key = "Unnamed: 0" if "Unnamed: 0" in df.columns else None

        grouped = (
            df.groupby(group_key)
            if group_key
            else ((idx, group) for idx, group in df.groupby(df.index))
        )

        for nfe, generation in grouped:
            # Rename columns from 0-based indices to objective names for only the last N columns
            # It assumes that the last `num_objectives` columns correspond to objectives.
            generation = generation.rename(
                {str(i): name for i, name in enumerate(list_of_objectives)},
                axis=1,
            )

            # Select only the last n objective columns
            generation = generation.iloc[:, -num_objectives:]

            list_of_archives.append(generation)

    print("Archives loaded")
    return archives, list_of_archives


def load_archives_all_seeds(
    list_of_objectives=[],
    data_path=None,
    file_name=None,  # "UTILITARIAN_100000_1644652.tar.gz",
    swf=None,
    nfe=None,
):
    """

    Returns
    -------


    """
    # Assert if arguments are None
    assert data_path is not None, "data_path is None"
    # assert file_name is not None, "file_name is None"
    # Assert if list_of_objectives is empty
    assert list_of_objectives, "list_of_objectives is empty"

    solutions = []
    # Convert swf to a list if it isn't one
    if not isinstance(swf, (list, tuple)):
        swf = [swf]

    print("Loading list of files")
    seed_archive_dict = {}
    for current_swf in swf:
        print("Loading archives for: ", current_swf)
        for filename in os.listdir(data_path):
            print("Filename: ", filename)
            if filename.startswith(f"{current_swf}_{nfe}"):
                file_name = filename
                print("Matching file:", file_name)
                archives = ArchiveLogger.load_archives(f"{data_path}/{file_name}")

                print("Loading archives from:", file_name)

                # Get the maximum key from the archive keys
                max_key = max(archives.keys())
                print("Max key:", max_key)

                # Retrieve the archive corresponding to the maximum key
                archive = archives[max_key]

                # Print the number of rows in the archive
                print("Number of rows in archive:", archive.shape[0])

                solutions.append(archive)

                print("Archives loaded for:", file_name)

        if solutions:  # Only if there are solutions found for this swf
            seed_archive_dict[current_swf] = pd.concat(solutions, ignore_index=True)
        else:
            print(
                f"No archives found for {current_swf} with prefix {current_swf}_{nfe}"
            )

    return seed_archive_dict


def get_global_reference_set(
    list_of_objectives=[],
    data_path=None,
    swf=None,
    nfe=None,
    epsilons=[],
    direction_of_optimization=[],
    output_data_path=None,
    saving=True,
):
    """
    Get the global reference set
    """
    # Throw error if epsilon length is not equal to the number of objectives
    assert len(epsilons) == len(
        list_of_objectives
    ), "Length of epsilons is not equal to the number of objectives"

    seed_archive_dict = load_archives_all_seeds(
        list_of_objectives=list_of_objectives, data_path=data_path, swf=swf, nfe=nfe
    )

    # This will convert the list of indices of the objectives. Needed for the pareto sorting library
    list_of_objectives = list(range(len(list_of_objectives)))

    # This will return the indices of the objectives that are to be maximized
    max_indices = [
        index for index, value in enumerate(direction_of_optimization) if value == "max"
    ]

    reference_sets = {}

    for swf in seed_archive_dict:

        # TODO: Temp
        archive = seed_archive_dict[swf]

        # Add index column to the archive
        archive = archive.reset_index(drop=True)

        # only select the objective columns
        objective_data = archive.iloc[:, -len(list_of_objectives) :]
        objective_data = objective_data.values.tolist()

        nondominated = pareto.eps_sort(
            objective_data,
            list_of_objectives,
            epsilons,
            maximize=max_indices,
        )

        nondominated_list = [tuple(row) for row in nondominated]

        # Convert the objective data array to a list of tuples
        objective_data_list = [tuple(row) for row in objective_data]

        # Find indices in the original data that match the nondominated solutions

        nondominated_indices = [
            index
            for index, row in enumerate(objective_data_list)
            if row in nondominated_list
        ]
        reference_sets[swf] = archive.iloc[nondominated_indices]

        if saving:
            output_file = f"{output_data_path}/{swf}_reference_set.csv"
            # Save the nondominated in csv withouth the index
            pd.DataFrame(reference_sets[swf]).to_csv(output_file, index=False)
            print(f"Reference set saved to {output_file}")

    return reference_sets


def calculate_hypervolume_from_archives(
    list_of_objectives=[
        "welfare",
        "years_above_temperature_threshold",
        "welfare_loss_damage",
        "welfare_loss_abatement",
    ],
    direction_of_optimization=[],  # ["min", "min", "min", "min"],
    input_data_path="data/optimized_rbf_weights/200k",
    file_name="PRIORITARIAN_200000.tar.gz",
    output_data_path="data/convergence_metrics",
    saving=True,
    global_reference_set=False,
    global_reference_set_path=None,
    global_reference_set_file=None,
    pool=None,
):

    archives, list_of_archives = load_archives(
        list_of_objectives=list_of_objectives,
        data_path=input_data_path,
        file_name=file_name,
    )
    list_of_archives = pd.concat(list_of_archives).values

    # Temporary #TODO: Remove
    print("list_of_archives: ", list_of_archives.shape)

    scaler = MinMaxScaler()

    if global_reference_set:
        # Throw an error if the path and file are not provided
        assert (
            global_reference_set_path is not None
        ), "global_reference_set_path is None"
        assert (
            global_reference_set_file is not None
        ), "global_reference_set_file is None"

        # load the global reference set
        global_reference_set = pd.read_csv(
            f"{global_reference_set_path}/{global_reference_set_file}"
        )
        # TODO: Check this.
        global_reference_set = global_reference_set.iloc[
            :, -len(list_of_objectives) :
        ].values

        scaler.fit(global_reference_set)
        reference_set = transform_data(
            global_reference_set, scaler, direction_of_optimization
        )

    else:
        scaler.fit(list_of_archives)
        reference_set = transform_data(
            list_of_archives, scaler, direction_of_optimization
        )  # .values

    print("reference_set", reference_set.shape)
    # Print the type of reference_set
    print("type of reference_set", type(reference_set))

    maxima = np.max(reference_set, axis=0)

    nfes = list(archives.keys())

    # Check if there is a key with 0. If there is, remove it
    if 0 in nfes:
        nfes.remove(0)
    print("nfes: \n", nfes)
    scores = []
    overall_starttime = datetime.datetime.now()

    # Enumerate through the keys of the archives
    nfe_archives = [
        transform_data(
            ((archives[key]).iloc[:, -(len(list_of_objectives)) :]).values,
            scaler,
            # direction_of_optimization, # This is not needed. The hypervolume calculation is already taking care of this
        )
        for key in nfes
        if key != 0
    ]
    print("Computing hypervolume for ", file_name)
    hv_results = pool.map(partial(calculate_hypervolume, maxima), nfe_archives)

    scores.append(pd.DataFrame.from_dict(dict(nfe=nfes, hypervolume=hv_results)))

    delta_time = datetime.datetime.now() - overall_starttime
    print(
        f"Time taken for Hypervolume Calculation: {delta_time.total_seconds():.3f} seconds"
    )
    scores = pd.concat(scores, axis=0, ignore_index=True)

    if saving:
        output_file = f"{output_data_path}/{file_name.split('.')[0]}_hv.csv"
        print(output_file)
        scores.to_csv(output_file)

    return scores


if __name__ == "__main__":

    # Suppress warnings
    warnings.filterwarnings("ignore")

    list_of_objectives = [
        "welfare",
        "years_above_temperature_threshold",
        "welfare_loss_damage",
        "welfare_loss_abatement",
    ]
    data_path = "data/optimized_rbf_weights/150k/SUFF"  # NOTE: Change this according to the PF folder name

    direction_of_optimization = ["min", "min", "max", "max"]

    get_global_reference_set(
        list_of_objectives=list_of_objectives,
        data_path=data_path,
        file_name=None,
        swf=[
            # "UTILITARIAN",
            # "PRIORITARIAN",
            # "EGALITARIAN",
            "SUFFICIENTARIAN",
        ],
        nfe="150000",
        epsilons=[
            0.1,
            0.25,
            10,
            10,
        ],
        direction_of_optimization=direction_of_optimization,
        output_data_path="data/convergence_metrics",
        saving=True,
    )

    filenames = [
        "PRIORITARIAN_150000_521475.tar.gz",
        "PRIORITARIAN_150000_1644652.tar.gz",
        "PRIORITARIAN_150000_3569126.tar.gz",
        "PRIORITARIAN_150000_6075612.tar.gz",
        "PRIORITARIAN_150000_9845531.tar.gz",
        # "UTILITARIAN_150000_521475.tar.gz",
        # "UTILITARIAN_150000_1644652.tar.gz",
        # "UTILITARIAN_150000_3569126.tar.gz",
        # "UTILITARIAN_150000_6075612.tar.gz",
        # "UTILITARIAN_150000_9845531.tar.gz",
        # "EGALITARIAN_150000_521475.tar.gz",
        # "EGALITARIAN_150000_1644652.tar.gz",
        # "EGALITARIAN_150000_3569126.tar.gz",
        # "EGALITARIAN_150000_6075612.tar.gz",
        # "EGALITARIAN_150000_9845531.tar.gz",
        # "SUFFICIENTARIAN_150000_521475.tar.gz",
        # "SUFFICIENTARIAN_150000_1644652.tar.gz",
        # "SUFFICIENTARIAN_150000_3569126.tar.gz",
        # "SUFFICIENTARIAN_150000_6075612.tar.gz",
        # "SUFFICIENTARIAN_150000_9845531.tar.gz",
    ]

    with multiprocessing.Pool() as pool:
        # Enumerate through the filenames
        for filename in filenames:
            scores = calculate_hypervolume_from_archives(
                list_of_objectives=list_of_objectives,
                direction_of_optimization=direction_of_optimization,
                input_data_path=data_path,
                file_name=filename,
                output_data_path="data/convergence_metrics",
                saving=True,
                global_reference_set=True,
                global_reference_set_path="data/convergence_metrics",
                global_reference_set_file="PRIORITARIAN_reference_set.csv",  # NOTE: Change this according to the PF refset
            )
