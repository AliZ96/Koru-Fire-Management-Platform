from Operators import *
from Neighborhood import *

class GA:
    
    def __init__(self, popSize, crossoverType, crossoverRate,
                 mutationType, mutationRate, nbOfGenerations):
        self.__popSize = popSize
        self.__crossoverType = crossoverType
        self.__crossoverRate = crossoverRate
        self.__mutationType = mutationType
        self.__mutationRate = mutationRate
        self.__nbOfGenerations = nbOfGenerations
       
    
    def run(self):
        # Initializing a random population.
        # Evaluations of the solutions are done in constructing the solution
        population = Population(self.__popSize)

        # Applying local search to the initial population
        Neighborhood.two_opt_first_All_vehicles_On_Population(population)

        # Finding the best solution in the population
        self.__best = population.findBestSolution()
        
        # Generational iterations
        for i in range(self.__nbOfGenerations):

            # Beginning each generation with an empty child population
            offspring = Population(0)

            # This loop is for the generating the offspring
            # By the end of the generational loop:
            # 0 <= offspring.getPopulationSize() <= popSize 
            for j in range(self.__popSize // 2):
            
                # Selecting two parents by binary tournament
                p1 = population.tournamentSelection(2)
                p2 = population.tournamentSelection(2)
                
                # Crossover
                c1, c2 = copy(p1), copy(p2)
                if random() < self.__crossoverRate:
                    pass
                    c1Tour, c2Tour = Operators.crossover(self.__crossoverType,
                                                         c1.getGiantTour(),
                                                         c2.getGiantTour())
                    c1 = StationSolution(c1Tour)
                    c2 = StationSolution(c2Tour)

                # Mutation
                if random() < self.__mutationRate:
                    pass
                    Operators.mutate(self.__mutationType, c1)
                    Operators.mutate(self.__mutationType, c2)

                # Local search
                Neighborhood.two_opt_first_All_vehicles(c1)
                Neighborhood.two_opt_first_All_vehicles(c2)

                # Update the best solution
                self.__updateBest(c1)
                self.__updateBest(c2)
                
                # Filling the offspring population
                offspring.addSolution(c1)
                offspring.addSolution(c2)

                assert set(c1.getGiantTour()) == set(c2.getGiantTour()), str(j) + " Parents must contain the same fire points"

            # Combining the parent and offspring populations
            population.extendPopulation(offspring)

            # Survival selection before next generational iteration.
            population.survivalSelection()
        #print()


    def getBestSolution(self):
        return self.__best
    
    def __updateBest(self, solution : StationSolution):
        if (solution is not None) and (solution.getFitness() < self.__best.getFitness()):
            self.__best = copy(solution)
            #print(self.__best)