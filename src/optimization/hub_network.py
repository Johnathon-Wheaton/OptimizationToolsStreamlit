import pulp
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates Euclidean distance and converts to kilometers"""
    return np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2) * 111.2

def optimize_hub_network(
    origins_df: pd.DataFrame,
    candidate_hubs_df: pd.DataFrame,
    destinations_df: pd.DataFrame,
    demand_df: pd.DataFrame,
    max_hubs: int,
    cost_per_unit_distance: float,
    capacity_per_shipment: float,
    minimum_cost_per_load: float,
    time_limit: int,
    optimality_gap: float
) -> Dict:
    """
    Optimize hub-and-spoke network design
    
    Args:
        origins_df: DataFrame with origin locations (City, Latitude, Longitude)
        candidate_hubs_df: DataFrame with candidate hub locations (City, Latitude, Longitude, FixedCost)
        destinations_df: DataFrame with destination locations (City, Latitude, Longitude)
        demand_df: DataFrame with demand data (Origin, Destination, Demand)
        max_hubs: Maximum number of hubs to open
        cost_per_unit_distance: Transportation cost per unit distance
        capacity_per_shipment: Maximum capacity per shipment/load
        minimum_cost_per_load: Minimum cost per load (regardless of distance)
        time_limit: Maximum solver runtime in seconds
        optimality_gap: Relative optimality gap for solver
    
    Returns:
        Dictionary containing optimization results
    """
    # Create sets
    origins = origins_df['City'].tolist()
    hubs = candidate_hubs_df['City'].tolist()
    destinations = destinations_df['City'].tolist()
    
    # Create distance dictionary
    distances = {}
    for df in [origins_df, candidate_hubs_df, destinations_df]:
        for _, row in df.iterrows():
            for df2 in [origins_df, candidate_hubs_df, destinations_df]:
                for _, row2 in df2.iterrows():
                    if row['City'] != row2['City']:
                        dist = calculate_distance(row['Latitude'], row['Longitude'], 
                                               row2['Latitude'], row2['Longitude'])
                        distances[(row['City'], row2['City'])] = dist

    # Create demand dictionary
    demand = {(row['Origin'], row['Destination']): row['Demand'] 
             for _, row in demand_df.iterrows()}

    # Create optimization model
    model = pulp.LpProblem("Hub_Network_Optimization", pulp.LpMinimize)
    
    # Decision variables
    # Direct flow variables
    x = pulp.LpVariable.dicts("DirectFlow", 
                             ((i, j) for i in origins for j in destinations), 
                             lowBound=0, cat='Continuous')
    
    # Hub flow variables
    y = pulp.LpVariable.dicts("HubFlow", 
                             ((i, h, j) for i in origins for h in hubs for j in destinations), 
                             lowBound=0, cat='Continuous')
    
    # Hub opening variables
    z = pulp.LpVariable.dicts("HubOpen", hubs, cat='Binary')
    
    # Load variables (integer)
    l_direct = pulp.LpVariable.dicts("DirectLoads", 
                                    ((i, j) for i in origins for j in destinations), 
                                    lowBound=0, cat='Integer')
    
    l_oh = pulp.LpVariable.dicts("OriginHubLoads", 
                                ((i, h) for i in origins for h in hubs), 
                                lowBound=0, cat='Integer')
    
    l_hd = pulp.LpVariable.dicts("HubDestinationLoads", 
                                ((h, j) for h in hubs for j in destinations), 
                                lowBound=0, cat='Integer')

    # Objective function
    model += (
        # Direct shipping costs
        pulp.lpSum(l_direct[i, j] * max(minimum_cost_per_load, 
                                       distances.get((i, j), 9999) * cost_per_unit_distance)
                   for i in origins for j in destinations) +
        # Origin to hub shipping costs
        pulp.lpSum(l_oh[i, h] * max(minimum_cost_per_load, 
                                   distances.get((i, h), 9999) * cost_per_unit_distance)
                   for i in origins for h in hubs) +
        # Hub to destination shipping costs
        pulp.lpSum(l_hd[h, j] * max(minimum_cost_per_load, 
                                   distances.get((h, j), 9999) * cost_per_unit_distance)
                   for h in hubs for j in destinations) +
        # Fixed costs for opening hubs
        pulp.lpSum(candidate_hubs_df.loc[candidate_hubs_df['City'] == h, 'FixedCost'].values[0] * z[h] 
                   for h in hubs)
    )

    # Constraints
    # Demand satisfaction constraints
    for i in origins:
        for j in destinations:
            model += (x[i, j] + pulp.lpSum(y[i, h, j] for h in hubs) == demand.get((i, j), 0), 
                     f"Demand_{i}_{j}")

    # Direct shipping capacity constraints
    for i in origins:
        for j in destinations:
            model += (x[i, j] <= l_direct[i, j] * capacity_per_shipment, 
                     f"DirectCapacity_{i}_{j}")

    # Origin-hub capacity constraints
    for i in origins:
        for h in hubs:
            model += (pulp.lpSum(y[i, h, j] for j in destinations) <= 
                     l_oh[i, h] * capacity_per_shipment, 
                     f"OriginHubCapacity_{i}_{h}")

    # Hub-destination capacity constraints
    for h in hubs:
        for j in destinations:
            model += (pulp.lpSum(y[i, h, j] for i in origins) <= 
                     l_hd[h, j] * capacity_per_shipment, 
                     f"HubDestinationCapacity_{h}_{j}")

    # Hub opening constraints
    for h in hubs:
        model += (pulp.lpSum(y[i, h, j] for i in origins for j in destinations) <= 
                 z[h] * sum(demand.values()), 
                 f"HubOpening_{h}")

    # Maximum number of hubs constraint
    model += (pulp.lpSum(z[h] for h in hubs) <= max_hubs, 
             "MaxHubs")

    # Solve the model
    solver = pulp.PULP_CBC_CMD(timeLimit=time_limit, gapRel=optimality_gap)
    model.solve(solver)

    # Process results
    facilities_df = pd.DataFrame({
        'City': hubs,
        'IsOpen': [pulp.value(z[h]) == 1 for h in hubs],
        'Latitude': [candidate_hubs_df.loc[candidate_hubs_df['City'] == h, 'Latitude'].values[0] for h in hubs],
        'Longitude': [candidate_hubs_df.loc[candidate_hubs_df['City'] == h, 'Longitude'].values[0] for h in hubs]
    })

    # Collect flow information
    connections = []
    
    # Direct flows
    for i in origins:
        for j in destinations:
            direct_flow = pulp.value(x[i, j])
            if direct_flow > 0:
                loads = pulp.value(l_direct[i, j])
                distance = distances.get((i, j), 9999)
                cost = loads * max(minimum_cost_per_load, distance * cost_per_unit_distance)
                connections.append({
                    'From': i,
                    'To': j,
                    'Type': 'Direct',
                    'Volume': direct_flow,
                    'Loads': loads,
                    'Distance': distance,
                    'Cost': cost
                })

    # Hub flows
    for i in origins:
        for h in hubs:
            for j in destinations:
                hub_flow = pulp.value(y[i, h, j])
                if hub_flow > 0:
                    oh_loads = pulp.value(l_oh[i, h])
                    hd_loads = pulp.value(l_hd[h, j])
                    distance_oh = distances.get((i, h), 9999)
                    distance_hd = distances.get((h, j), 9999)
                    cost_oh = oh_loads * max(minimum_cost_per_load, distance_oh * cost_per_unit_distance)
                    cost_hd = hd_loads * max(minimum_cost_per_load, distance_hd * cost_per_unit_distance)
                    connections.append({
                        'From': i,
                        'To': j,
                        'Via': h,
                        'Type': 'Hub',
                        'Volume': hub_flow,
                        'LoadsOH': oh_loads,
                        'LoadsHD': hd_loads,
                        'DistanceOH': distance_oh,
                        'DistanceHD': distance_hd,
                        'CostOH': cost_oh,
                        'CostHD': cost_hd
                    })

    return {
        'status': pulp.LpStatus[model.status],
        'total_cost': pulp.value(model.objective),
        'connections': pd.DataFrame(connections),
        'facilities': facilities_df,
        'solver_time': solver.solution_time if hasattr(solver, 'solution_time') else None
    }