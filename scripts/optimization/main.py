import json
import PlotResults
from GA import *
from SA import *

def SA_AllStationsBestSolutionOfPopulationTests():
    ProblemInstance.loadInstance("pipeline_result.csv",
                                 "../llf22/output/dist_all.csv",
                                 "../llf22/output/izmir_fire_points_filtered2.csv",
                                 "../llf22/output/izmir_itfaiye_master_dataset.csv")
    ProblemInstance.setVehicleCapacity(200)
    print("Fire Station List:", ProblemInstance.getFireStationsList())
    print("Fire Point List:", ProblemInstance.getFirePointsList())
    print("Fire Station - Fire Points Map:" + str(ProblemInstance.getFireStationFirePointsMap()))
    print("Coordinates of Fire Stations and Fire Points:", ProblemInstance.getAllCoordinates())
    stationSolutions = []
    for i in range(len(ProblemInstance.getFireStationsList())):
        stationID = ProblemInstance.getFireStationsList()[i]
        firePoints = ProblemInstance.getFireStationAssignedFirePoints(stationID)
        ProblemInstance.setCurrentSolutionSetStationID(stationID)
        ProblemInstance.setCurrentSolutionSetFirePointsList(firePoints)
        popSize, nbOfGenerations = 100, 10
        crossoverType, crossoverRate = "CX", 0.7
        mutationType, mutationRate =  "swap", 0.1
        sa = SA(100)
        sa.run()
        stationBestSolution = sa.getBestSolution()
        print("Fire Station ID: " + str(stationBestSolution.getFireStationID()))
        print("Assigned Fire Points: " + str(stationBestSolution.getFullListOfFirePoints()))
        print("Sample Station Solution:\n" + str(stationBestSolution))
        stationSolutions.append(stationBestSolution)
    return stationSolutions

def GA_AllStationsBestSolutionOfPopulationTests():
    ProblemInstance.loadInstance("pipeline_result.csv",
                                 "../llf22/output/dist_all.csv",
                                 "../llf22/output/izmir_fire_points_filtered2.csv",
                                 "../llf22/output/izmir_itfaiye_master_dataset.csv")
    ProblemInstance.setVehicleCapacity(200)
    print("Fire Station List:", ProblemInstance.getFireStationsList())
    print("Fire Point List:", ProblemInstance.getFirePointsList())
    print("Fire Station - Fire Points Map:" + str(ProblemInstance.getFireStationFirePointsMap()))
    print("Coordinates of Fire Stations and Fire Points:", ProblemInstance.getAllCoordinates())
    stationSolutions = []
    for i in range(len(ProblemInstance.getFireStationsList())):
        stationID = ProblemInstance.getFireStationsList()[i]
        firePoints = ProblemInstance.getFireStationAssignedFirePoints(stationID)
        ProblemInstance.setCurrentSolutionSetStationID(stationID)
        ProblemInstance.setCurrentSolutionSetFirePointsList(firePoints)
        popSize, nbOfGenerations = 100, 10
        crossoverType, crossoverRate = "CX", 0.7
        mutationType, mutationRate =  "swap", 0.1
        ga = GA(popSize, crossoverType, crossoverRate, mutationType, mutationRate, nbOfGenerations)
        ga.run()
        stationBestSolution = ga.getBestSolution()
        print("Fire Station ID: " + str(stationBestSolution.getFireStationID()))
        print("Assigned Fire Points: " + str(stationBestSolution.getFullListOfFirePoints()))
        print("Sample Station Solution:\n" + str(stationBestSolution))
        stationSolutions.append(stationBestSolution)
    return stationSolutions

def writeAllStationsSolutionsToFile(fileName : str, stationSolutionsList : list) -> None:
    with open(fileName, 'w') as f:
        for stationSolution in stationSolutionsList:
            f.write("Assigned Fire Points: " + str(stationSolution.getFullListOfFirePoints()) + "\n")
            f.write(str(stationSolution) + "\n\n")

def writeAllStationsSolutionsToJSON(fileName: str, stationSolutionsList: list) -> None:
    data = []
    for stationSolution in stationSolutionsList:
        vehicles_data = []
        for idx, vehicle in enumerate(stationSolution.getVehicles()):
            tour = vehicle.getTour()
            station_id = stationSolution.getFireStationID()
            full_tour = [station_id] + tour + [station_id]
            vehicles_data.append({
                "vehicle_index": idx,
                "tour": full_tour,
                "load": vehicle.getLoad(),
                "distance": round(vehicle.getDistance(), 4)
            })
        data.append({
            "station_id": stationSolution.getFireStationID(),
            "assigned_fire_points": stationSolution.getFullListOfFirePoints(),
            "total_distance": round(stationSolution.getFitness(), 4),
            "vehicles": vehicles_data
        })
    with open(fileName, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def runAlgorithm(algorithm : str) -> None:
    if algorithm == "GA":
        gaResults = GA_AllStationsBestSolutionOfPopulationTests()
        PlotResults.plotAllStationsVehicles(algorithm, gaResults)
        writeAllStationsSolutionsToFile("GA_All_Stations_Best_Solutions.txt", gaResults)
        writeAllStationsSolutionsToJSON("GA_All_Stations_Best_Solutions.json", gaResults)
    elif algorithm == "SA":
        saResults = SA_AllStationsBestSolutionOfPopulationTests()
        PlotResults.plotAllStationsVehicles(algorithm, saResults)
        writeAllStationsSolutionsToFile("SA_All_Stations_Best_Solutions.txt", saResults)
        writeAllStationsSolutionsToJSON("SA_All_Stations_Best_Solutions.json", saResults)

if __name__ == "__main__":
    runAlgorithm("GA")
    runAlgorithm("SA")