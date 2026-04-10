import matplotlib.pyplot as plt
from StationSolution import *
import matplotlib.pyplot as plt
import mplcursors


def plotOneStationsVehicles(stationSolution: StationSolution, ax=None, all_scatters=None, all_ids=None, color='blue'):
    """Plot a single station and its vehicles on the given axes."""
    if ax is None:
        ax = plt.gca()
    if all_scatters is None:
        all_scatters = []
    if all_ids is None:
        all_ids = []

    vehicles = stationSolution.getVehicles()

    # Station coordinates and ID
    stationID = stationSolution.getFireStationID()
    stationX = ProblemInstance.getCoordinate(stationID)[0]
    stationY = ProblemInstance.getCoordinate(stationID)[1]

    for vehicle in vehicles:
        firePoints = vehicle.getTour()
        x = [ProblemInstance.getCoordinate(fp)[0] for fp in firePoints]
        y = [ProblemInstance.getCoordinate(fp)[1] for fp in firePoints]

        # Close tour lines
        pathX = [stationX] + x + [stationX]
        pathY = [stationY] + y + [stationY]
        ax.plot(pathX, pathY, color=color, linewidth=2)

        # Fire points
        sc = ax.scatter(x, y, s=100, c=color, marker='o', edgecolors='black')
        all_scatters.append(sc)
        all_ids.append(firePoints)

    # Station square
    station_sc = ax.scatter(stationX, stationY, s=300, c=color, marker='s', edgecolors='black')
    all_scatters.append(station_sc)
    all_ids.append([stationID])

    return all_scatters, all_ids


def plotAllStationsVehicles(title : str, stationSolutions: list) -> None:
    """Plot all stations and their vehicles in one figure with different colors per station."""
    plt.figure()
    ax = plt.gca()
    all_scatters = []
    all_ids = []

    # List of distinct colors to cycle through
    color_list = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'cyan', 'magenta', 'yellow']
    num_colors = len(color_list)

    for i, stationSolution in enumerate(stationSolutions):
        station_color = color_list[i % num_colors]  # Cycle colors if more stations than colors
        all_scatters, all_ids = plotOneStationsVehicles(
            stationSolution, ax=ax, all_scatters=all_scatters, all_ids=all_ids, color=station_color
        )

    # Labels and grid
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Result of " + title)
    ax.grid()

    # Single cursor for all scatter plots
    cursor = mplcursors.cursor(all_scatters, hover=True, multiple=False)

    @cursor.connect("add")
    def on_add(sel):
        for sc, ids in zip(all_scatters, all_ids):
            if sel.artist == sc:
                sel.annotation.set_text(str(ids[sel.index]))
                sel.annotation.get_bbox_patch().set(fc="white", alpha=0.8, edgecolor="black")
                sel.annotation.set_fontsize(9)
                break

    plt.show()
