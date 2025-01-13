import pulp
import pandas as pd
from typing import Dict, Tuple, List

def optimize_facility_locations(
    facilities_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    distances_df: pd.DataFrame,
    mip_gap: float = 0.01,
    max_run_time_seconds: int = 300,
    facility_fixed_cost_multiplier: float = 1,
    cost_per_unit_distance: float = 1
) -> Dict:
    """
    Optimize facility locations using Mixed Integer Linear Programming
    Args:
        facilities_df: DataFrame with facility data
        customers_df: DataFrame with customer data
        distances_df: DataFrame with distance data
        mip_gap: Maximum MIP gap tolerance (default: 0.01 or 1%)
        max_run_time_seconds: Maximum runtime in seconds (default: 300)
        facility_fixed_cost_multiplier: Multiplier for facility fixed costs
        cost_per_unit_distance: Cost per unit distance for transportation
    """
    # Extract data from DataFrames
    facilities = facilities_df['FacilityID'].tolist()
    fixed_costs = dict(zip(facilities_df['FacilityID'], facilities_df['FixedCost']))
    capacities = dict(zip(facilities_df['FacilityID'], facilities_df['Capacity']))
    facility_coords = dict(zip(facilities_df['FacilityID'], 
                             zip(facilities_df['Latitude'], facilities_df['Longitude'])))
    
    customers = customers_df['CustomerID'].tolist()
    demands = dict(zip(customers_df['CustomerID'], customers_df['Demand']))
    customer_coords = dict(zip(customers_df['CustomerID'], 
                             zip(customers_df['Latitude'], customers_df['Longitude'])))
    
    distances = {(row['FacilityID'], row['CustomerID']): row['Distance'] 
                for _, row in distances_df.iterrows()}

    # Define the problem
    prob = pulp.LpProblem("Facility_Location", pulp.LpMinimize)
    
    # Decision variables
    facility_vars = pulp.LpVariable.dicts("Facility", facilities, cat='Binary')
    transport_vars = pulp.LpVariable.dicts("Transport", 
                                         (facilities, customers), 
                                         lowBound=0, 
                                         cat='Continuous')
    
    # Objective function
    total_cost = (
        pulp.lpSum([fixed_costs[f] * facility_vars[f] * facility_fixed_cost_multiplier for f in facilities]) +
        pulp.lpSum([distances[(f, c)] * transport_vars[f][c] * cost_per_unit_distance
                   for f in facilities for c in customers])
    )
    prob += total_cost

    # Constraints
    for c in customers:
        prob += pulp.lpSum([transport_vars[f][c] for f in facilities]) == demands[c]

    for f in facilities:
        prob += (pulp.lpSum([transport_vars[f][c] for c in customers]) 
                <= capacities[f] * facility_vars[f])

    # Create solver with custom parameters
    solver = pulp.PULP_CBC_CMD(
        msg=False,  # Suppress solver output
        gapRel=mip_gap,  # Relative MIP gap tolerance
        maxSeconds=max_run_time_seconds,  # Maximum runtime in seconds
        options=['allowableGap', str(mip_gap), 
                'seconds', str(max_run_time_seconds)]
    )

    # Solve the problem
    prob.solve(solver)
    
    # Prepare results
    results_df = pd.DataFrame({
        'FacilityID': facilities,
        'Open': [pulp.value(facility_vars[f]) == 1 for f in facilities],
        'FixedCost': [fixed_costs[f] for f in facilities],
        'Capacity': [capacities[f] for f in facilities],
        'Selected': ['Yes' if pulp.value(facility_vars[f]) == 1 else 'No' for f in facilities]
    })
    
    transport_results = [
        {
            'FacilityID': f,
            'CustomerID': c,
            'TransportAmount': pulp.value(transport_vars[f][c])
        }
        for f in facilities
        for c in customers
        if pulp.value(transport_vars[f][c]) > 0
    ]
    transport_df = pd.DataFrame(transport_results)
    
    return {
        'results': results_df,
        'transport': transport_df,
        'total_cost': pulp.value(total_cost),
        'status': pulp.LpStatus[prob.status]
    }