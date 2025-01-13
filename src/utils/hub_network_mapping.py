import pydeck as pdk
import pandas as pd
import numpy as np
from typing import Dict, List

def generate_color_scale(values: List[float], 
                        min_alpha: int = 100, 
                        max_alpha: int = 200) -> List[List[int]]:
    """
    Generate colors for flows with alpha channel based on volume
    """
    if not values:
        return []
        
    min_val = min(values)
    max_val = max(values)
    
    if min_val == max_val:
        return [[128, 0, 128, max_alpha]] * len(values)
        
    colors = []
    for val in values:
        alpha = min_alpha + (max_alpha - min_alpha) * (val - min_val) / (max_val - min_val)
        colors.append([128, 0, 128, int(alpha)])
    return colors

def create_hub_network_map(
    connections_df: pd.DataFrame,
    facilities_df: pd.DataFrame,
    origins_df: pd.DataFrame,
    destinations_df: pd.DataFrame,
    candidate_hubs_df: pd.DataFrame
) -> Dict:
    """
    Create an interactive map visualization for hub network optimization results
    
    Args:
        connections_df: DataFrame with flow information
        facilities_df: DataFrame with hub selection results
        origins_df: DataFrame with origin locations
        destinations_df: DataFrame with destination locations
        candidate_hubs_df: DataFrame with candidate hub locations
        
    Returns:
        Dictionary containing deck object and additional visualization info
    """
    # Process connections data for visualization
    viz_connections = []
    
    # Process direct connections
    direct_flows = connections_df[connections_df['Type'] == 'Direct']
    for _, flow in direct_flows.iterrows():
        # Get coordinates
        origin = origins_df[origins_df['City'] == flow['From']].iloc[0]
        dest = destinations_df[destinations_df['City'] == flow['To']].iloc[0]
        
        viz_connections.append({
            'start_lat': origin['Latitude'],
            'start_lon': origin['Longitude'],
            'end_lat': dest['Latitude'],
            'end_lon': dest['Longitude'],
            'volume': flow['Volume'],
            'loads': flow['Loads'],
            'type': 'Direct'
        })
    
    # Process hub connections
    hub_flows = connections_df[connections_df['Type'] == 'Hub']
    for _, flow in hub_flows.iterrows():
        # Origin to Hub segment
        origin = origins_df[origins_df['City'] == flow['From']].iloc[0]
        hub = candidate_hubs_df[candidate_hubs_df['City'] == flow['Via']].iloc[0]
        
        viz_connections.append({
            'start_lat': origin['Latitude'],
            'start_lon': origin['Longitude'],
            'end_lat': hub['Latitude'],
            'end_lon': hub['Longitude'],
            'volume': flow['Volume'],
            'loads': flow['LoadsOH'],
            'type': 'Hub-Inbound'
        })
        
        # Hub to Destination segment
        dest = destinations_df[destinations_df['City'] == flow['To']].iloc[0]
        
        viz_connections.append({
            'start_lat': hub['Latitude'],
            'start_lon': hub['Longitude'],
            'end_lat': dest['Latitude'],
            'end_lon': dest['Longitude'],
            'volume': flow['Volume'],
            'loads': flow['LoadsHD'],
            'type': 'Hub-Outbound'
        })
    
    connections_viz_df = pd.DataFrame(viz_connections)
    
    # Generate colors based on volume
    if not connections_viz_df.empty:
        flow_colors = generate_color_scale(connections_viz_df['volume'].tolist())
        connections_viz_df['color'] = flow_colors
    
    # Create layers
    layers = []
    
    # Calculate width scaling factor based on median load
    if not connections_viz_df.empty:
        median_load = connections_viz_df['loads'].median()
        width_scale_factor = 5 / median_load if median_load > 0 else 1
        connections_viz_df['scaled_width'] = connections_viz_df['loads'] * width_scale_factor
        
        # Add flow layer with adjusted width scaling
        layers.append(pdk.Layer(
            "LineLayer",
            connections_viz_df,
            get_source_position=['start_lon', 'start_lat'],
            get_target_position=['end_lon', 'end_lat'],
            get_color='color',
            get_width='scaled_width',  # Use the scaled width
            pickable=True,
        ))
    
    # Origins layer
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        origins_df,
        get_position=['Longitude', 'Latitude'],
        get_color=[255, 0, 0, 160],  # Red
        get_radius=25000,
        pickable=True,
    ))
    
    # Selected hubs layer
    selected_hubs = facilities_df[facilities_df['IsOpen']]
    if not selected_hubs.empty:
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            selected_hubs,
            get_position=['Longitude', 'Latitude'],
            get_color=[0, 255, 0, 160],  # Green
            get_radius=35000,
            pickable=True,
        ))
    
    # Unselected hubs layer
    unselected_hubs = facilities_df[~facilities_df['IsOpen']]
    if not unselected_hubs.empty:
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            unselected_hubs,
            get_position=['Longitude', 'Latitude'],
            get_color=[128, 128, 128, 160],  # Gray
            get_radius=35000,
            pickable=True,
        ))
    
    # Destinations layer
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        destinations_df,
        get_position=['Longitude', 'Latitude'],
        get_color=[0, 0, 255, 160],  # Blue
        get_radius=25000,
        pickable=True,
    ))
    
    # Add text layers for labels
    text_layers = [
        pdk.Layer(
            "TextLayer",
            pd.concat([
                origins_df.assign(type='Origin'),
                selected_hubs.assign(type='Selected Hub'),
                unselected_hubs.assign(type='Candidate Hub'),
                destinations_df.assign(type='Destination')
            ]),
            get_position=['Longitude', 'Latitude'],
            get_text='City',
            get_size=14,
            get_color=[0, 0, 0, 255],
            get_angle=0,
            text_anchor='"middle"',
            alignment_baseline='"center"',
            pickable=True,
        )
    ]
    
    # Calculate view state
    all_lats = pd.concat([
        origins_df['Latitude'],
        candidate_hubs_df['Latitude'],
        destinations_df['Latitude']
    ])
    all_lons = pd.concat([
        origins_df['Longitude'],
        candidate_hubs_df['Longitude'],
        destinations_df['Longitude']
    ])
    
    center_lat = all_lats.mean()
    center_lon = all_lons.mean()
    
    # Calculate zoom level based on data spread
    lat_range = all_lats.max() - all_lats.min()
    lon_range = all_lons.max() - all_lons.min()
    zoom = 3  # default zoom
    if lat_range > 0 or lon_range > 0:
        zoom = min(
            10,  # max zoom out
            max(
                3,  # min zoom out
                int(6 - max(lat_range, lon_range) / 10)  # adjust divisor to tune zoom
            )
        )

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
        pitch=0,
    )

    # Create the deck
    deck = pdk.Deck(map_style='mapbox://styles/mapbox/light-v9',
        layers=layers + text_layers,
        initial_view_state=view_state,
        tooltip={
            "html": "<b>City:</b> {City}<br/>"
                   "<b>Type:</b> {type}<br/>"
                   "<b>Volume:</b> {volume}<br/>"
                   "<b>Loads:</b> {loads}",
            "style": {
                "backgroundColor": "white",
                "color": "black"
            }
        }
    )

    return {
        'deck': deck,
        'view_state': view_state,
        'connections': connections_viz_df
    }