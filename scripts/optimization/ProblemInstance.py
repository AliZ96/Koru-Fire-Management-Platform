import csv

class ProblemInstance:

    __FireStationsList = list()
    __FirePointsList = list()
    __FireStationContainingFirePoints = dict()
    __PointsDemands = dict()
    __PointsRisks = dict()
    __DM = list()
    __Coordinates = list()
    __vehicleCapacity = 0
    __currentSolutionStationIndex = int()
    __currentSolutionFirePointsList = list()


    @staticmethod
    def loadInstance(pointsFile: str, distanceMatrixFile: str,
                     firePointsCoordinatesFile: str, fireStationsCoordinatesFile: str):
        ProblemInstance.__reset()
        ProblemInstance.__readPointsFromFile(pointsFile)
        ProblemInstance.__readDistanceMatrixFromFile(distanceMatrixFile)
        ProblemInstance.__readCoordinatesFromFile(firePointsCoordinatesFile, fireStationsCoordinatesFile)

    @staticmethod
    def __reset():
        ProblemInstance.__FireStationsList = list()
        ProblemInstance.__FirePointsList = list()
        ProblemInstance.__FireStationContainingFirePoints = dict()
        ProblemInstance.__PointsDemands = dict()
        ProblemInstance.__PointsRisks = dict()
        ProblemInstance.__DM = list()
        ProblemInstance.__Coordinates = list()
        ProblemInstance.__vehicleCapacity = 0

    #@staticmethod
    def __readPointsFromFile(path: str):

        with (open(path, newline='', encoding='utf-8') as csvfile):
            reader = csv.reader(csvfile, delimiter=';')
            for row in reader:
                if row[0].isalpha():
                    continue

                firePointID = int(row[0])
                demand = int(row[1])
                fireStationID = int(row[2])
                risk = row[3].strip()

                if firePointID not in ProblemInstance.__FirePointsList:
                    ProblemInstance.__FirePointsList.append(firePointID)
                    ProblemInstance.__PointsDemands[firePointID] = demand
                    ProblemInstance.__PointsRisks[firePointID] = risk

                if fireStationID not in ProblemInstance.__FireStationsList:
                    ProblemInstance.__FireStationsList.append(fireStationID)

                if fireStationID in ProblemInstance.__FireStationContainingFirePoints:
                    ProblemInstance.__FireStationContainingFirePoints[fireStationID].append(firePointID)
                else:
                    ProblemInstance.__FireStationContainingFirePoints[fireStationID] = [firePointID]

    @staticmethod
    def __readDistanceMatrixFromFile(distanceMatrixFile):
        with (open(distanceMatrixFile, newline='', encoding='utf-8') as csvfile):
            reader = csv.reader(csvfile, delimiter=';')
            for row in reader:
                if row[0].isalpha():
                    continue
                ProblemInstance.__DM.append([float(row[i]) for i in range(1, len(row))])


    @staticmethod
    def __readCoordinatesFromFile(firePointsCoordinatesFile, fireStationsCoordinatesFile):

        # Fire Points Coordinates
        with (open(firePointsCoordinatesFile, newline='', encoding='utf-8') as csvfile):
            reader = csv.reader(csvfile, delimiter=',')
            for row in reader:
                if row[0].isalpha():
                    continue
                #pointID = int(row[0])
                x = float(row[4])
                y = float(row[5])
                ProblemInstance.__Coordinates.append([x, y])

        #Fire Station Coordinates
        with (open(fireStationsCoordinatesFile, newline='', encoding='utf-8') as csvfile):
            reader = csv.reader(csvfile, delimiter=',')
            for row in reader:
                if row[0] == "station_name":
                    continue
                #stationID = int(row[0])
                x = float(row[1])
                y = float(row[2])
                ProblemInstance.__Coordinates.append([x,y])

    @staticmethod
    def getDistance(i: int, j: int) -> float:
        return ProblemInstance.__DM[i][j]

    @staticmethod
    def getFireStationsList() -> list:
        return ProblemInstance.__FireStationsList

    @staticmethod
    def getFirePointsList() -> list:
        return ProblemInstance.__FirePointsList

    @staticmethod
    def getAllCoordinates() -> list:
        return ProblemInstance.__Coordinates

    @staticmethod
    def getFireStationFirePointsMap() -> dict:
        return ProblemInstance.__FireStationContainingFirePoints

    @staticmethod
    def getFirePointDemand(point: int) -> int:
        return ProblemInstance.__PointsDemands[point]

    @staticmethod
    def getRisk(point: int) -> str:
        return ProblemInstance.__PointsRisks[point]

    @staticmethod
    def getCoordinate(ID: int) -> list[float]:
        return ProblemInstance.__Coordinates[ID]

    @staticmethod
    def getFireStationAssignedFirePoints(station: int) -> list[int]:
        return ProblemInstance.__FireStationContainingFirePoints[station]

    @staticmethod
    def getFirePointsAssignedStation(firePoint: int) -> int:
        for station, firePoints in ProblemInstance.__FireStationContainingFirePoints.items():
            if firePoint in firePoints:
                return station
        return None

    @staticmethod
    def getVehicleCapacity() -> int:
        return ProblemInstance.__vehicleCapacity

    @staticmethod
    def setVehicleCapacity(capacity: int):
        ProblemInstance.__vehicleCapacity = capacity

    @staticmethod
    def setCurrentSolutionSetStationID(stationIndex: int):
        ProblemInstance.__currentSolutionStationIndex = stationIndex

    @staticmethod
    def setCurrentSolutionSetFirePointsList(firePointsList: list[int]):
        ProblemInstance.__currentSolutionFirePointsList = firePointsList.copy()

    @staticmethod
    def getCurrentSolutionStationIndex() -> int:
        return ProblemInstance.__currentSolutionStationIndex

    @staticmethod
    def getCurrentSolutionFirePointsList() -> list[int]:
        return ProblemInstance.__currentSolutionFirePointsList.copy()

    @staticmethod
    def printDistanceMatrix():
        for i in range(len(ProblemInstance.__DM)):
            for j in range(len(ProblemInstance.__DM[i])):
                print(f"{(i, j)}: {ProblemInstance.__DM[i][j]:.4f}", end="  ")
            print()