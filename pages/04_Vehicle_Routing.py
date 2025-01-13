import streamlit as st
import pandas as pd
import numpy as np
from src.components.file_handlers import handle_template_download, handle_file_upload
from src.components.parameter_controls import create_parameter_controls
from src.optimization.vrp import solve_vrp
from src.utils.vrp_mapping import create_vrp_map

def vrp_page():
    st.title("Vehicle Routing Optimization")

    # Overview Section
    with st.expander("📃 Overview", expanded=True):
        st.markdown("""
        ### Overview
        This tool helps you optimize delivery routes for a fleet of vehicles, considering various constraints such as:
        - Vehicle capacity limits
        - Time windows for deliveries
        - Service times at each location
        - Travel times between locations
        
        #### What this model considers:
        - Multiple vehicles starting from a central depot
        - Customer locations and demands
        - Optional time windows for deliveries
        - Optional vehicle capacity constraints
        - Service time at each delivery point
        
        #### Required Input Data:
        1. **Locations**: List of all locations including:
            - Depot (Location_ID = 0)
            - Customer locations with demands
            - Coordinates (latitude/longitude)
            - Optional time windows (start and end times)
            - Service time at each location
        
        #### How it works:
        The model uses Google's OR-Tools to find optimal routes that minimize total travel time while satisfying all constraints.
        """)

    # Data Input Section
    with st.expander("📥 Data Input", expanded=True):
        st.subheader("1. Download Template")
        handle_template_download(
            "templates/vrp.xlsx",
            "Vehicle Routing"
        )
        
        st.subheader("2. Upload Data")
        dfs, error = handle_file_upload(["locations"])
        
        if error:
            st.error(error)
            return
            
        if dfs is not None:
            st.success("Data uploaded successfully! Review your data in the table below:")
            
            locations_df = dfs["locations"]
            st.dataframe(locations_df)

    # Parameters Section
    parameters_expander = st.expander("⚙️ Parameters", expanded=dfs is not None)
    if dfs is None:
        with parameters_expander:
            st.warning("Please upload your data first.")
    else:
        with parameters_expander:
            st.markdown("Adjust these parameters to fine-tune your optimization:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Vehicle Parameters")
                vehicle_params = create_parameter_controls(
                    initial_params={
                        "num_vehicles": 3,
                    },
                    param_ranges={
                        "num_vehicles": (1, 20, 1)  # min, max, step
                    }
                )
                
                # Capacity constraints
                use_capacity = st.checkbox("Use vehicle capacity constraints", value=True)
                if use_capacity:
                    capacity_params = create_parameter_controls(
                        initial_params={
                            "vehicle_capacity": 100,
                        },
                        param_ranges={
                            "vehicle_capacity": (10, 1000, 10)
                        }
                    )
                    vehicle_params.update(capacity_params)
                vehicle_params['use_capacity'] = use_capacity
            
            with col2:
                st.subheader("Solver Parameters")
                solver_params = create_parameter_controls(
                    initial_params={
                        "max_run_time_seconds": 30,
                    },
                    param_ranges={
                        "max_run_time_seconds": (10, 300, 10)
                    }
                )
            
            params = {**vehicle_params, **solver_params}
            
            # Check if time windows exist in data
            has_time_windows = not (locations_df['Time_Window_Start'].isna().all() or 
                                  locations_df['Time_Window_End'].isna().all())
            
            if has_time_windows:
                st.info("Time window constraints detected in the data and will be used in the optimization.")
            else:
                st.info("No time window constraints found in the data.")
            
            # Run optimization button
            if st.button("Run Optimization", type="primary"):
                with st.spinner("Optimizing routes..."):
                    try:
                        results = solve_vrp(
                            locations_df,
                            **params
                        )
                        
                        # Store results in session state
                        st.session_state.optimization_results = results
                        # Force the results expander to open
                        st.session_state.show_results = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Optimization failed: {str(e)}")

    # Results Section
    results_expander = st.expander("📊 Results", expanded=st.session_state.get('show_results', False))
    with results_expander:
        if dfs is None:
            st.warning("Please upload your data first.")
        elif 'optimization_results' not in st.session_state:
            st.info("Run the optimization to see results.")
        else:
            results = st.session_state.optimization_results
            
            if results['status'] == 'SUCCESS':
                # Summary metrics
                st.subheader("Summary")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Distance", f"{results['total_distance']:.1f} km")
                with col2:
                    st.metric("Total Time", f"{results['total_time']:.1f} min")
                with col3:
                    st.metric("Vehicles Used", str(len(results['routes'])))
                
                # Route details
                # Route details section in the Results expander
                st.subheader("Route Details")
                route_tabs = st.tabs([f"Route {i+1}" for i in range(len(results['route_info']))])
                for i, (tab, route_info) in enumerate(zip(route_tabs, results['route_info'])):
                    with tab:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Distance", f"{route_info['distance']:.1f} km")
                            st.metric("Total Time", f"{route_info['total_time']:.1f} min")
                        with col2:
                            if params['use_capacity']:
                                st.metric("Load", f"{route_info['load']:.1f}")
                            st.write("Stops:", route_info['locations'])
                
                # Display map
                st.subheader("Route Map")
                map_result = create_vrp_map(
                    locations_df,
                    results['routes']
                )
                st.pydeck_chart(map_result['deck'])
                
                # Map legend
                st.subheader("Legend")
                for i, color in enumerate(map_result['vehicle_colors']):
                    st.markdown(
                        f'<span style="color: rgb{tuple(color)};">■</span> Vehicle {i+1}', 
                        unsafe_allow_html=True
                    )
                st.markdown(
                    '<span style="color: rgb(200, 30, 0);">●</span> Delivery Location', 
                    unsafe_allow_html=True
                )
                st.markdown(
                    '<span style="color: rgb(0, 255, 0);">●</span> Depot', 
                    unsafe_allow_html=True
                )
            else:
                st.error(f"Optimization failed with status: {results['status']}")

if __name__ == "__main__":
    vrp_page()