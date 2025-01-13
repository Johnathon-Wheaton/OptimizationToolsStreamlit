import pydeck as pdk
import pandas as pd
from typing import Dict

def create_optimization_map(
    facilities_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    transport_df: pd.DataFrame,
    facility_coords: Dict,
    customer_coords: Dict,
    results_df: pd.DataFrame  # Add results_df as a parameter
) -> pdk.Deck:
    """
    Create an interactive map visualization of the optimization results
    """
    # Prepare facilities data
    facilities_map_df = pd.DataFrame({
        'FacilityID': results_df['FacilityID'],
        'lat': [facility_coords[f][0] for f in results_df['FacilityID']],
        'lon': [facility_coords[f][1] for f in results_df['FacilityID']],
        'Selected': results_df['Open']  # Changed from 'Selected' to 'Open' to match optimization output
    })

    # Rest of the function remains the same
    customers_map_df = pd.DataFrame({
        'CustomerID': customers_df['CustomerID'],
        'lat': [customer_coords[c][0] for c in customers_df['CustomerID']],
        'lon': [customer_coords[c][1] for c in customers_df['CustomerID']]
    })

    connections = []
    for _, row in transport_df.iterrows():
        facility = row['FacilityID']
        customer = row['CustomerID']
        connections.append({
            'start_lat': facility_coords[facility][0],
            'start_lon': facility_coords[facility][1],
            'end_lat': customer_coords[customer][0],
            'end_lon': customer_coords[customer][1],
            'amount': row['TransportAmount']
        })
    connections_df = pd.DataFrame(connections)

    layers = [
        pdk.Layer(
            "ScatterplotLayer",
            facilities_map_df,
            get_position=['lon', 'lat'],
            get_color=['(1-Selected) * 225', '(Selected) * 255', '0', '128'],
            get_radius=50000,
            pickable=True,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            customers_map_df,
            get_position=['lon', 'lat'],
            get_color=[0, 0, 255, 128],
            get_radius=25000,
            pickable=True,
        ),
        pdk.Layer(
            "LineLayer",
            connections_df,
            get_source_position=['start_lon', 'start_lat'],
            get_target_position=['end_lon', 'end_lat'],
            get_color=[128, 0, 128, 100],
            get_width=5,
        ),
        pdk.Layer(
            "TextLayer",
            facilities_map_df,
            get_position=['lon', 'lat'],
            get_text='FacilityID',
            get_size=16,
            get_color=[0, 0, 0, 255],
            get_angle=0,
            get_text_anchor='"middle"',
            get_alignment_baseline='"center"',
        ),
        pdk.Layer(
            "TextLayer",
            customers_map_df,
            get_position=['lon', 'lat'],
            get_text='CustomerID',
            get_size=12,
            get_color=[0, 0, 0, 255],
            get_angle=0,
            get_text_anchor='"middle"',
            get_alignment_baseline='"center"',
        )
    ]

    view_state = pdk.ViewState(
        latitude=facilities_map_df['lat'].mean(),
        longitude=facilities_map_df['lon'].mean(),
        zoom=3,
        pitch=0,
    )

    return pdk.Deck(map_style='mapbox://styles/mapbox/light-v9',layers=layers, initial_view_state=view_state)