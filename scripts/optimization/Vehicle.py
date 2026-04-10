from copy import copy

from ProblemInstance import *


class Vehicle:

    def __init__(self):
        self.reset()

    def reset(self):
        self.__load = 0
        self.__distance = 0.0
        self.__tour = []
        self.__stationIndex = ProblemInstance.getCurrentSolutionStationIndex()

    def calculateDistance(self):
        self.__distance = 0.0
        if len(self.__tour) == 0:
            return

        self.__distance += ProblemInstance.getDistance(self.__stationIndex, self.__tour[0])
        for i in range(1, len(self.__tour)):
            self.__distance += ProblemInstance.getDistance(self.__tour[i - 1], self.__tour[i])
        self.__distance += ProblemInstance.getDistance(self.__tour[-1], self.__stationIndex)

    def addPoint(self, pointID: int, index: int = None):
        demand = ProblemInstance.getFirePointDemand(pointID)
        deltaDistance = 0.0
        if (self.__load + demand > ProblemInstance.getVehicleCapacity()
                or (index != None and (index < 0 or index > len(self.__tour)))):
            return False

        if pointID in self.__tour:
            return False

        prevPointID, nextPointID = None, None
        if len(self.__tour) == 0:
            prevPointID = self.__stationIndex
            nextPointID = self.__stationIndex
            index = 0
        elif index == None or index == len(self.__tour):
            prevPointID = self.getPoint(len(self.__tour) - 1)
            nextPointID = self.__stationIndex
            index = len(self.__tour)
        else:
            prevPointID = self.getPreviousPoint(index)
            nextPointID = self.getPoint(index)

        deltaDistance += ((ProblemInstance.getDistance(prevPointID, pointID)
                           + ProblemInstance.getDistance(pointID, nextPointID))
                          - ProblemInstance.getDistance(prevPointID, nextPointID))
        self.__tour.insert(index, pointID)

        self.__load += demand
        self.__distance += deltaDistance
        return True

    def removePoint(self, index: int):
        if self.getTourLength() < 1 or index < 0 or index >= len(self.__tour):
            return False

        pointID = self.getPoint(index)
        prevPointID = self.getPreviousPoint(index)
        nextPointID = self.getNextPoint(index)

        deltaDistance = (ProblemInstance.getDistance(prevPointID, nextPointID)
                         - ProblemInstance.getDistance(prevPointID, pointID)
                         - ProblemInstance.getDistance(pointID, nextPointID))

        self.__tour.pop(index)
        demand = ProblemInstance.getFirePointDemand(pointID)
        self.__load -= demand
        self.__distance += deltaDistance
        return True

    def getTour(self):
        return self.__tour

    def getTourLength(self):
        return len(self.__tour)

    def getLoad(self):
        return self.__load

    def getDistance(self):
        return self.__distance

    def getRemainingCapacity(self):
        return ProblemInstance.getVehicleCapacity() - self.__load

    def getPoint(self, index: int):
        return self.__tour[index]

    def getPreviousPoint(self, index: int):
        if index == 0:
            return self.__stationIndex
        return self.__tour[index - 1]

    def getNextPoint(self, index: int):
        if index == len(self.__tour) - 1:
            return self.__stationIndex
        return self.__tour[index + 1]


    def setTour(self, tour : list):
        self.__tour = copy(tour)

    def __deltaSwap(self, i, j):
        if i < 0 or i >= len(self.__tour) or j < 0 or j >= len(self.__tour):
            return None

        pointI = self.getPoint(i)
        prevI = self.getPreviousPoint(i)
        nextI = self.getNextPoint(i)
        pointJ = self.getPoint(j)
        prevJ = self.getPreviousPoint(j)
        nextJ = self.getNextPoint(j)

        deltaDistance = (ProblemInstance.getDistance(prevI, pointI)
                         + ProblemInstance.getDistance(pointI, nextI)
                         + ProblemInstance.getDistance(prevJ, pointJ)
                         + ProblemInstance.getDistance(pointJ, nextJ))

        return deltaDistance

    def swap(self, i, j):
        if i < 0 or i >= len(self.__tour) or j < 0 or j >= len(self.__tour):
            return False

        self.__distance -= self.__deltaSwap(i, j)
        self.__tour[i], self.__tour[j] = self.__tour[j], self.__tour[i]
        self.__distance += self.__deltaSwap(i, j)

        return True

    def reverse(self, i, j):
        if i < 0 or i >= len(self.__tour) or j < 0 or j >= len(self.__tour) or i >= j:
            return False

        negativeDelta = (ProblemInstance.getDistance(self.getPreviousPoint(i), self.getPoint(i))
                       + ProblemInstance.getDistance(self.getPoint(j), self.getNextPoint(j)))

        self.__tour[i:j + 1] = reversed(self.__tour[i:j + 1])

        positiveDelta = (ProblemInstance.getDistance(self.getPreviousPoint(i), self.getPoint(i))
                       + ProblemInstance.getDistance(self.getPoint(j), self.getNextPoint(j)))

        self.__distance += positiveDelta - negativeDelta

        return True

    def __str__(self):
        tempTour = [point for point in self.__tour]
        tempTour.insert(0, self.__stationIndex)
        tempTour.append(self.__stationIndex)
        return (f'Tour: {tempTour}, Load: {self.__load} / {ProblemInstance.getVehicleCapacity()}, '
                f'Distance: {self.__distance:.2f}')