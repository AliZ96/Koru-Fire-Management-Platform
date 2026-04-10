from Population import *

class Neighborhood:

    @staticmethod
    def two_opt_first(vehicle : Vehicle) -> None:
        
        n = vehicle.getTourLength()

        if n < 3:
            return

        modified = True

        while modified:
            modified = False

            for i in range(n - 2):
                for j in range(i + 2, n - 1):

                    d_i_j = ProblemInstance.getDistance(vehicle.getPoint(i), vehicle.getPoint(j))
                    d_i1_j1 = ProblemInstance.getDistance(vehicle.getPoint(i + 1), vehicle.getPoint(j + 1))
                    d_i_i1 = ProblemInstance.getDistance(vehicle.getPoint(i), vehicle.getPoint(i + 1))
                    d_j_j1 = ProblemInstance.getDistance(vehicle.getPoint(j), vehicle.getPoint(j + 1))

                    if d_i_j + d_i1_j1 < d_i_i1 + d_j_j1:
                        vehicle.reverse(i + 1, j)
                        modified = True
                        break

                if modified:
                    break

    @staticmethod
    def two_opt_first_All_vehicles (solution : StationSolution) -> None:
        for vehicle in solution.getVehicles():
            Neighborhood.two_opt_first(vehicle)

    @staticmethod
    def two_opt_first_All_vehicles_On_Population (population : Population) -> None:
        for solution in population.getPopulation():
            Neighborhood.two_opt_first_All_vehicles(solution)