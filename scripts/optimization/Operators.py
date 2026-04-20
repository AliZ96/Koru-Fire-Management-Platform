from random import randint, randrange
from StationSolution import *

class Operators:

    # CROSSOVERS
    @classmethod
    def crossover(cls, crossoverType, P1 : list, P2 : list):
        if crossoverType == "CX":
            return Operators.__CX(P1, P2)
        

    @classmethod
    def __CX(cls, P1 : list, P2 : list):
        size = len(P1)
        C1, C2 = [-1] * size, [-1] * size
        turn = True
        for ind in range(size):
            if not (C1[ind] == -1):
                continue
            cycle = list()
            current = ind
            while not (P2[current] == P1[ind]):
                cycle.append(current)
                current = P1.index(P2[current])
            cycle.append(current)
            
            # Filling the offspring
            for i in cycle:
                if turn:
                    C1[i] = P1[i]
                    C2[i] = P2[i]
                else:
                    C1[i] = P2[i]
                    C2[i] = P1[i]
            turn = not turn
        
        return C1, C2
    

    # MUTATIONS
    @classmethod
    def mutate(cls, mutationType, P : StationSolution) -> None:
        # n : number of times to apply the mutation move (swap)
        # 10% of the tour length

        if mutationType == "swap":
            Operators.__swap(P)

    
    @classmethod
    def __swap(cls, C : StationSolution) -> None:
        n = C.getNumberOfAllFirePoints() // 10 + 1
        for i in range(n):
            fromVehicle = randrange(len(C.getVehicles()))
            toVehicle = randrange(len(C.getVehicles()))
            if len(C.getVehicle(fromVehicle).getTour()) == 0 or len(C.getVehicle(toVehicle).getTour()) == 0:
                continue
            fromFirePointIndex = randrange(len(C.getVehicle(fromVehicle).getTour()))
            removedFirePoint = C.getVehicle(fromVehicle).getPoint(fromFirePointIndex)
            toFirePointIndex = randrange(len(C.getVehicle(toVehicle).getTour()))
            demand = ProblemInstance.getFirePointDemand(removedFirePoint)
            if fromVehicle == toVehicle or demand <= C.getVehicle(toVehicle).getRemainingCapacity():
                C.getVehicle(fromVehicle).removePoint(fromFirePointIndex)
                C.getVehicle(toVehicle).addPoint(removedFirePoint, toFirePointIndex)
