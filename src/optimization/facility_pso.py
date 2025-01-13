import numpy as np
from typing import Dict, List, Tuple
import math
import pandas as pd

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on Earth"""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def calculate_total_cost(
    facility_locations: np.ndarray,
    customers: List[str],
    demands: Dict[str, float],
    customer_coords: Dict[str, Tuple[float, float]],
    facility_capacity: float,
    fixed_cost: float,
    cost_per_km: float,
    units_per_load: float
) -> Tuple[float, Dict[str, int]]:
    """Calculate total cost for a given solution"""
    facility_usage = {i: 0 for i in range(len(facility_locations))}
    total_cost = 0
    penalty_factor = 1000000
    assignments = {}

    for customer, demand in demands.items():
        customer_lat, customer_lon = customer_coords[customer]
        distances = [haversine_distance(customer_lat, customer_lon, fac_lat, fac_lon) 
                    for fac_lat, fac_lon in facility_locations]
        sorted_facilities = sorted(range(len(distances)), key=lambda k: distances[k])

        assigned = False
        for facility in sorted_facilities:
            if facility_usage[facility] + demand <= facility_capacity:
                facility_usage[facility] += demand
                distance = distances[facility]
                loads = math.ceil(demand / units_per_load)
                transport_cost = distance * cost_per_km * loads
                total_cost += transport_cost
                assignments[customer] = facility
                assigned = True
                break
        
        if not assigned:
            total_cost += penalty_factor
            assignments[customer] = None

    # Add fixed costs for used facilities
    for facility, usage in facility_usage.items():
        if usage > 0:
            total_cost += fixed_cost

    # Calculate usage standard deviation
    usage_values = list(facility_usage.values())
    if len(usage_values) > 1 and len(set(usage_values)) > 1:
        usage_std = np.std(usage_values)
        total_cost += usage_std * 100
    
    return float(total_cost), assignments

def optimize_facility_locations_pso(
    customers_df: pd.DataFrame,
    n_facilities: int,
    facility_capacity: float,
    fixed_cost: float,
    cost_per_km: float,
    units_per_load: float,
    n_particles: int = 30,
    n_iterations: int = 100,
    max_run_time_seconds: int = 300,  # Added time limit parameter
    inertia_weight: float = 0.9,
    cognitive_coefficient: float = 2.0,
    social_coefficient: float = 2.0
) -> Dict:
    """
    Optimize facility locations using Particle Swarm Optimization
    """
    import time
    start_time = time.time()
    
    # Extract data from DataFrame
    customers = customers_df['CustomerID'].tolist()
    demands = dict(zip(customers_df['CustomerID'], customers_df['Demand']))
    customer_coords = dict(zip(customers_df['CustomerID'], 
                             zip(customers_df['Latitude'], customers_df['Longitude'])))
    
    # Define bounds
    lat_bounds = (customers_df['Latitude'].min(), customers_df['Latitude'].max())
    lon_bounds = (customers_df['Longitude'].min(), customers_df['Longitude'].max())
    
    # Initialize particles
    particles = np.random.uniform(
        low=[lat_bounds[0], lon_bounds[0]], 
        high=[lat_bounds[1], lon_bounds[1]], 
        size=(n_particles, n_facilities, 2)
    )
    velocities = np.random.uniform(-1, 1, size=(n_particles, n_facilities, 2))
    
    # Initialize best positions and scores
    personal_best_positions = np.copy(particles)
    personal_best_scores = np.array([
        calculate_total_cost(
            p, customers, demands, customer_coords,
            facility_capacity, fixed_cost, cost_per_km, units_per_load
        )[0] for p in personal_best_positions
    ])
    
    global_best_index = np.argmin(personal_best_scores)
    global_best_position = personal_best_positions[global_best_index]
    global_best_score = personal_best_scores[global_best_index]
    
    current_inertia_weight = inertia_weight

    # Store iteration history for plotting
    history = []
    completed_iterations = 0

    for iteration in range(n_iterations):
        # Check if time limit is exceeded
        if time.time() - start_time > max_run_time_seconds:
            break
            
        for i in range(n_particles):
            inertia = current_inertia_weight * velocities[i]
            cognitive_component = cognitive_coefficient * np.random.rand(n_facilities, 2) * (
                personal_best_positions[i] - particles[i]
            )
            social_component = social_coefficient * np.random.rand(n_facilities, 2) * (
                global_best_position - particles[i]
            )
            
            velocities[i] = inertia + cognitive_component + social_component
            particles[i] += velocities[i]
            
            # Apply bounds
            particles[i] = np.clip(
                particles[i], 
                [lat_bounds[0], lon_bounds[0]], 
                [lat_bounds[1], lon_bounds[1]]
            )

            score, assignments = calculate_total_cost(
                particles[i], customers, demands, customer_coords,
                facility_capacity, fixed_cost, cost_per_km, units_per_load
            )
            
            if score < personal_best_scores[i]:
                personal_best_positions[i] = np.copy(particles[i])
                personal_best_scores[i] = score

        best_particle_index = np.argmin(personal_best_scores)
        if personal_best_scores[best_particle_index] < global_best_score:
            global_best_position = np.copy(personal_best_positions[best_particle_index])
            global_best_score = personal_best_scores[best_particle_index]

        current_inertia_weight = max(0.4, current_inertia_weight * 0.99)
        
        # Store iteration results
        history.append({
            'iteration': iteration,
            'best_score': global_best_score,
            'time': time.time() - start_time
        })
        
        completed_iterations = iteration + 1

    # Calculate final assignments and costs
    total_cost, final_assignments = calculate_total_cost(
        global_best_position, customers, demands, customer_coords,
        facility_capacity, fixed_cost, cost_per_km, units_per_load
    )

    # Prepare results in a structured format
    facility_locations = [
        {'FacilityID': f'FAC{i+1}', 'Latitude': lat, 'Longitude': lon}
        for i, (lat, lon) in enumerate(global_best_position)
    ]
    
    assignments_list = [
        {
            'CustomerID': customer,
            'FacilityID': f'FAC{facility+1}' if facility is not None else None,
            'Demand': demands[customer]
        }
        for customer, facility in final_assignments.items()
    ]

    total_time = time.time() - start_time

    return {
        'status': 'Optimal',
        'total_cost': total_cost,
        'facility_locations': pd.DataFrame(facility_locations),
        'assignments': pd.DataFrame(assignments_list),
        'history': pd.DataFrame(history),
        'completed_iterations': completed_iterations,
        'total_time': total_time
    }