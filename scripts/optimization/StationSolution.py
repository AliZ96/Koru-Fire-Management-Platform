from Vehicle import *
from random import shuffle
class StationSolution:

    def __init__(self, type : str = "random"):
        self.__reset()
        self.__assignedFirePointsList = ProblemInstance.getCurrentSolutionFirePointsList()
        self.__fireStationIndex = ProblemInstance.getCurrentSolutionStationIndex()

        if isinstance(type, str) and type in ["random", "ordered"]:
            self.__giantTour = self.__assignedFirePointsList.copy()
            self.__splitToVehicles(type)
            self.evaluate()
        elif isinstance(type, list):
            self.setGiantTour(type)
            self.__splitToVehicles("ordered")
            self.evaluate()
        elif isinstance(type, StationSolution):
            self.__giantTour = type.getFullListOfFirePoints()
            self.__totalDistance = type.getFitness()
            self.__vehiclesList = list()
            for vehicle in type.getVehicles():
                newVehicle = Vehicle()
                for point in vehicle.getTour():
                    newVehicle.addPoint(point)
                self.__vehiclesList.append(newVehicle)

    def __reset(self):
        self.__vehiclesList = list()
        self.__giantTour = list()
        self.__totalDistance = 0.0


    def setGiantTour(self, giantTour : list[int]):
        self.__giantTour = giantTour.copy()
        self.__splitToVehicles("ordered")
        self.evaluate()

    def __splitToVehicles(self, type : str = "random"):
        self.__vehiclesList = list()
        if type == "ordered":
            self.__basicSplit()
        elif type == "random":
            shuffle(self.__giantTour)
            self.__basicSplit()

    def __basicSplit(self):
        count = 0
        while count < len(self.__giantTour):
            vehicle = Vehicle()
            for i in range(count, len(self.__giantTour)):
                firePoint = self.__giantTour[i]
                demand = ProblemInstance.getFirePointDemand(firePoint)
                if vehicle.getRemainingCapacity() >= demand:
                    vehicle.addPoint(firePoint)
                    count += 1
                else:
                    break
            self.__vehiclesList.append(vehicle)
        '''miss = self.missingFirePoints()
        if len(miss) > 0:
            pass'''


    def evaluate(self):
        self.__totalDistance = 0.0
        self.__deleteEmptyVehicles()
        for vehicle in self.__vehiclesList:
            self.__totalDistance += vehicle.getDistance()

    def __deleteEmptyVehicles(self):
        self.__vehiclesList = [v for v in self.__vehiclesList if v.getTourLength() > 0]

    def getGiantTour(self):
        self.__giantTour = list()
        for v in self.__vehiclesList:
            self.__giantTour.extend(v.getTour())
        return self.__giantTour

    def getFitness(self) -> float:
        return self.__totalDistance

    def getVehicles(self) -> list[Vehicle]:
        return self.__vehiclesList

    def getVehicle(self, index : int) -> Vehicle:
        return self.__vehiclesList[index]

    def getFireStationID(self):
        return self.__fireStationIndex

    def getFullListOfFirePoints(self):
        return self.__assignedFirePointsList

    def getNumberOfAllFirePoints(self):
        return len(self.__assignedFirePointsList)

    def getResult(self):
        vehicleList = list()
        self.__deleteEmptyVehicles()
        for vehicle in self.__vehiclesList:
            vehicleList.append(vehicle.getTour())
        return vehicleList, self.__totalDistance


    def missingFirePoints(self):
        missingFirePointsList = list()
        for firePoint in self.__assignedFirePointsList:
            found = False
            for vehicle in self.__vehiclesList:
                if firePoint in vehicle.getTour():
                    found = True
                    break
            if not found:
                missingFirePointsList.append(firePoint)
        return missingFirePointsList

    def __str__(self):
        result = "Station " + str(self.__fireStationIndex) + ":\n"
        for vehicle in self.__vehiclesList:
            result += "\t" + str(vehicle) + "\n"
        result += f"\tTotal Distance: {self.__totalDistance : .2f}"
        return result