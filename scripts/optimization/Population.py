from StationSolution import *
from random import randrange, random
from copy import copy, deepcopy

class Population:
    
    def __init__(self, size):
        self.__size = size
        self.__population = list()
        if size > 0:
            self.__population.append(StationSolution("ordered"))
            for i in range(1,size):
                self.__population.append(StationSolution())
    
    def getPopulationSize(self):
        return len(self.__population)
    
    def getPopulation(self):
        return self.__population
    
    def getSolution(self, index):
        return self.__population[index]
    
    def findBestSolution(self):
        self.__bestSolution = copy(self.__population[0])
        for i in range(1,len(self.__population)):
            if self.__population[i].getFitness() < self.__bestSolution.getFitness():
                self.__bestSolution = copy(self.__population[i])
        return copy(self.__bestSolution)
    
    def addSolution(self,solution : StationSolution):
        self.__population.append(solution)
        
    def extendPopulation(self, population):
        if population is not None:
            for solution in population.getPopulation():
                self.addSolution(copy(solution))
    
    def tournamentSelection(self,tournamentSize):
        winner = self.getSolution(randrange(self.getPopulationSize()))
        for i in range(tournamentSize - 1):
            rival = self.getSolution(randrange(self.getPopulationSize()))
            if rival.getFitness() < winner.getFitness():
                winner = rival
        return copy(winner)
    
    def survivalSelection(self):
        self.__population = sorted(self.__population, key=lambda x:x.getFitness())

        # Elitism
        n = self.getPopulationSize() // 10
        if n == 0: n = 1

        pop = deepcopy(self.__population[:n])
        self.__population = deepcopy(self.__population[n:])

        # Tournament Selection
        while len(pop) < self.__size:
            winner = self.tournamentSelection(2)
            pop.append(deepcopy(winner))

        self.__population = deepcopy(pop)

        
    def __str__(self):
        s = ""
        for i in range(self.getPopulationSize()):
            s += str(i) + ")" + str(self.getSolution(i).getFitness()) + "\n"
        return s
            