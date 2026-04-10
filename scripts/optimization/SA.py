from Operators import *
from Neighborhood import *
import math

class SA:
    
    _minT = 0.1
    
    def __init__(self, T):
        self._T = T
        
    def run(self):
        sc = StationSolution()
        self._bestSolution = copy(sc)
        while (self._T > self._minT):
            local = False
            while not local:
                sn = copy(sc)
                Operators.mutate("swap", sn)

                if sn.getFitness() < sc.getFitness():
                    sc = copy(sn)
                    if sn.getFitness() < self._bestSolution.getFitness():
                        self._bestSolution = copy(sn)
                    local = True
                else:
                    delta = math.exp(-abs(sn.getFitness() - sc.getFitness()) / self._T)
                    if random() < delta:
                        sc = copy(sn)
                        local = True

            self._T *= 0.99
    
    def getBestSolution(self):
        return self._bestSolution