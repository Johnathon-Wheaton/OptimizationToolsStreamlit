import pandas as pd
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import Dict, List

def create_data_model(
    df: pd.DataFrame,
    num_vehicles: int,
    use_capacity: bool = True,
    vehicle_capacity: int = 100
) -> Dict:
    """
    Prepare data for the VRP solver
    """
    data = {}
    data['locations'] = list(zip(df['Latitude'], df['Longitude']))
    data['num_vehicles'] = num_vehicles
    data['depot'] = 0
    data['demands'] = df['Demand'].tolist()
    data['vehicle_capacity'] = vehicle_capacity
    data['use_capacity'] = use_capacity
    
    # Handle time windows - if any are null, don't use time windows
    if df['Time_Window_Start'].isna().any() or df['Time_Window_End'].isna().any():
        data['use_time_windows'] = False
        data['time_windows'] = None
        data['service_times'] = [0] * len(df)
    else:
        data['use_time_windows'] = True
        data['time_windows'] = list(zip(df['Time_Window_Start'], df['Time_Window_End']))
        data['service_times'] = df['Service_Time'].fillna(0).tolist()
    
    # Calculate time matrix (using Haversine distance)
    locations = data['locations']
    num_locations = len(locations)
    time_matrix = np.zeros((num_locations, num_locations))
    
    for from_node in range(num_locations):
        for to_node in range(num_locations):
            if from_node == to_node:
                time_matrix[from_node][to_node] = 0
            else:
                # Haversine formula
                lat1, lon1 = np.radians([locations[from_node][0], locations[from_node][1]])
                lat2, lon2 = np.radians([locations[to_node][0], locations[to_node][1]])
                
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                
                a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
                c = 2 * np.arcsin(np.sqrt(a))
                distance = 6371 * c  # Earth's radius in km
                
                # Convert distance to time (assuming average speed of 30 km/h)
                time_matrix[from_node][to_node] = distance * 2  # Time in minutes
    
    data['time_matrix'] = time_matrix.astype(int).tolist()
    data['distance_matrix'] = time_matrix.tolist()
    
    return data

def solve_vrp(
    df: pd.DataFrame,
    num_vehicles: int,
    use_capacity: bool = True,
    vehicle_capacity: int = 100,
    max_run_time_seconds: int = 30
) -> Dict:
    """
    Solve the Vehicle Routing Problem
    """
    # Create data model
    data = create_data_model(df, num_vehicles, use_capacity, vehicle_capacity)
    
    # Create routing index manager
    manager = pywrapcp.RoutingIndexManager(
        len(data['time_matrix']),
        data['num_vehicles'],
        data['depot']
    )
    
    # Create Routing Model
    routing = pywrapcp.RoutingModel(manager)

    # Create and register transit callback
    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['time_matrix'][from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Capacity constraint if enabled
    if data['use_capacity']:
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return data['demands'][from_node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            [data['vehicle_capacity']] * data['num_vehicles'],  # vehicle maximum capacities
            True,  # start cumul to zero
            'Capacity'
        )

    # Add Time Windows constraint if enabled
    if data['use_time_windows']:
        time = 'Time'
        routing.AddDimension(
            transit_callback_index,
            30,  # allow waiting time
            1440,  # maximum time per vehicle (24 hours in minutes)
            False,  # Don't force start cumul to zero
            time
        )
        time_dimension = routing.GetDimensionOrDie(time)

        # Add time window constraints for each location except depot
        for location_idx, time_window in enumerate(data['time_windows']):
            if location_idx == data['depot']:
                continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

    # Setting first solution heuristic
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.time_limit.seconds = max_run_time_seconds

    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)

    # Extract solution
    if solution:
        routes = []
        route_info = []
        total_distance = 0
        total_time = 0
        
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            route = []
            route_distance = 0
            route_time = 0
            route_load = 0
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route.append(node_index)
                route_load += data['demands'][node_index]
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                
                # Add distance and time
                route_distance += data['distance_matrix'][manager.IndexToNode(previous_index)][manager.IndexToNode(index)]
                route_time += data['time_matrix'][manager.IndexToNode(previous_index)][manager.IndexToNode(index)]
                
                if data['use_time_windows']:
                    route_time += data['service_times'][node_index]
            
            route.append(manager.IndexToNode(index))
            
            if len(route) > 2:  # Only include routes that visit at least one customer
                routes.append(route)
                route_info.append({
                    'distance': route_distance,
                    'total_time': route_time,
                    'load': route_load,
                    'locations': route
                })
                total_distance += route_distance
                total_time += route_time

        return {
            'status': 'SUCCESS',
            'routes': routes,
            'route_info': route_info,
            'total_distance': total_distance,
            'total_time': total_time
        }
    
    return {
        'status': 'FAILED',
        'error': 'No solution found'
    }