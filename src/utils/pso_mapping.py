import pydeck as pdk
import pandas as pd
from typing import Dict, List

def create_pso_map(
    facility_locations_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    assignments_df: pd.DataFrame
) -> pdk.Deck:
    """Create an interactive map visualization for PSO results"""
    
    # Create customer layer
    customer_layer = pdk.Layer(
        "ScatterplotLayer",
        data=customers_df.to_dict('records'),
        get_position=['Longitude', 'Latitude'],
        get_color=[0, 0, 255, 128],
        get_radius=25000,
        pickable=True
    )

    # Create facility layer
    facility_layer = pdk.Layer(
        "ScatterplotLayer",
        data=facility_locations_df.to_dict('records'),
        get_position=['Longitude', 'Latitude'],
        get_color=[0, 255, 0, 128],
        get_radius=50000,
        pickable=True
    )

    # Create customer labels
    customer_text_layer = pdk.Layer(
        "TextLayer",
        data=customers_df.to_dict('records'),
        get_position=['Longitude', 'Latitude'],
        get_text='CustomerID',
        get_size=12,
        get_color=[0, 0, 0, 255],
        get_angle=0,
        get_text_anchor='"middle"',
        get_alignment_baseline='"center"',
    )

    # Create connection layer
    connections = []
    for _, assignment in assignments_df.iterrows():
        if assignment['FacilityID'] is not None:
            customer_row = customers_df[customers_df['CustomerID'] == assignment['CustomerID']].iloc[0]
            facility_row = facility_locations_df[facility_locations_df['FacilityID'] == assignment['FacilityID']].iloc[0]
            
            connections.append({
                'source': [customer_row['Longitude'], customer_row['Latitude']],
                'target': [facility_row['Longitude'], facility_row['Latitude']],
                'customerID': assignment['CustomerID'],
                'facilityID': assignment['FacilityID']
            })

    connection_layer = pdk.Layer(
        "LineLayer",
        data=connections,
        get_source_position='source',
        get_target_position='target',
        get_color=[128, 0, 128, 100],
        get_width=5,
        pickable=True
    )

    # Set view state
    view_state = pdk.ViewState(
        latitude=customers_df['Latitude'].mean(),
        longitude=customers_df['Longitude'].mean(),
        zoom=3,
        pitch=0
    )

    return pdk.Deck(map_style='mapbox://styles/mapbox/light-v9',
        layers=[connection_layer, customer_layer, facility_layer, customer_text_layer],
        initial_view_state=view_state,
    )