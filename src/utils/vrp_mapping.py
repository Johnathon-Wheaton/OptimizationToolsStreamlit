import pydeck as pdk
import pandas as pd
import numpy as np
from typing import List

def generate_vehicle_colors(num_vehicles: int) -> List[List[int]]:
    """Generate distinct colors for number of vehicles"""
    base_colors = [
        [239, 71, 111],   # Red
        [6, 214, 160],    # Green
        [17, 138, 178],   # Blue
        [255, 209, 102],  # Yellow
        [7, 59, 76],      # Dark Blue
        [255, 107, 107],  # Coral
        [97, 212, 198],   # Turquoise
        [122, 81, 149],   # Purple
        [242, 132, 130],  # Salmon
        [146, 188, 222],  # Light Blue
    ]
    
    if num_vehicles <= len(base_colors):
        return base_colors[:num_vehicles]
    
    # If more vehicles than base colors, generate additional colors
    import colorsys
    additional_colors = []
    for i in range(num_vehicles - len(base_colors)):
        hue = i / (num_vehicles - len(base_colors))
        rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
        additional_colors.append([int(c * 255) for c in rgb])
    
    return base_colors + additional_colors

def create_vrp_map(
    locations_df: pd.DataFrame,
    routes: List[List[int]],
) -> pdk.Deck:
    """Create an interactive map visualization for VRP results"""
    
    vehicle_colors = generate_vehicle_colors(len(routes))
    
    # Prepare route data
    route_data = []
    for i, route in enumerate(routes):
        color = vehicle_colors[i]
        for j in range(len(route) - 1):
            start = route[j]
            end = route[j + 1]
            route_data.append({
                'start_lat': locations_df.loc[start, 'Latitude'],
                'start_lon': locations_df.loc[start, 'Longitude'],
                'end_lat': locations_df.loc[end, 'Latitude'],
                'end_lon': locations_df.loc[end, 'Longitude'],
                'color': color,
                'vehicle_id': i + 1
            })
    route_df = pd.DataFrame(route_data)

    # Create layers
    layers = [
        # Routes layer
        pdk.Layer(
            "ArcLayer",
            data=route_df,
            get_width=3,
            get_source_position=["start_lon", "start_lat"],
            get_target_position=["end_lon", "end_lat"],
            get_tilt=15,
            get_source_color="color",
            get_target_color="color",
            pickable=True,
            auto_highlight=True,
        ),
        
        # Delivery locations layer
        pdk.Layer(
            "ScatterplotLayer",
            data=locations_df[locations_df['Location_ID'] != 0],
            get_position=["Longitude", "Latitude"],
            get_color=[200, 30, 0, 160],
            get_radius=200,
            pickable=True,
        ),
        
        # Depot layer
        pdk.Layer(
            "ScatterplotLayer",
            data=locations_df[locations_df['Location_ID'] == 0],
            get_position=["Longitude", "Latitude"],
            get_color=[0, 255, 0, 160],
            get_radius=300,
            pickable=True,
        )
    ]

    # Set view state
    view_state = pdk.ViewState(
        latitude=np.mean(locations_df['Latitude']),
        longitude=np.mean(locations_df['Longitude']),
        zoom=11,
        pitch=30,
    )

    return {
        'deck': pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            layers=layers,
            initial_view_state=view_state,
            tooltip={
                "html": "<b>Location ID:</b> {Location_ID}<br/>"
                        "<b>Demand:</b> {Demand}<br/>"
                        "<b>Time Window:</b> {Time_Window_Start} - {Time_Window_End}"
            },
        ),
        'vehicle_colors': vehicle_colors
    }