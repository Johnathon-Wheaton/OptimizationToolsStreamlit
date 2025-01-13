import streamlit as st
import pandas as pd
from src.components.file_handlers import handle_template_download, handle_file_upload
from src.components.parameter_controls import create_parameter_controls, create_editable_dataframe
from src.optimization.facility_pso import optimize_facility_locations_pso
from src.utils.pso_mapping import create_pso_map

def facility_pso_page():
    st.title("Facility Location Optimization (PSO)")
    
    with st.expander("📃 Overview", expanded=True):
        # Model description
        st.markdown("""
        ### Overview
        This tool helps you determine optimal facility locations to minimize total costs while meeting customer demand. Unlike the MILP version, 
        this Particle Swarm Optimization (PSO) approach doesn't require predefined candidate locations - it will find the best locations anywhere 
        within the geographic bounds of your customer network.
        
        #### What this model considers:
        - Fixed costs of opening facilities
        - Transportation costs based on distance
        - Facility capacity constraints
        - Customer demand requirements
        - Load consolidation (units per load)
        
        #### Required Input Data:
        1. **Customers**: List of customer locations with:
            - Demand quantities
            - Location coordinates (latitude/longitude)
            
        #### How it works:
        The PSO algorithm simulates a swarm of particles searching through the solution space to find optimal facility locations. Each particle 
        represents a potential set of facility locations, and the swarm collectively explores the geographic area to minimize total costs.
        """)

    # Data Input Section (expanded by default)
    with st.expander("📥 Data Input", expanded=True):
        # Template download section
        st.subheader("1. Download Template")
        handle_template_download(
            "templates/facility_pso.xlsx",
            "Facility Location PSO"
        )
        
        # File upload section
        st.subheader("2. Upload Data")
        dfs, error = handle_file_upload(["customers"])
        
        if error:
            st.error(error)
            return
            
        if dfs is not None:
            st.success("Data uploaded successfully! Review your data in the table below:")
            
            st.subheader("Customers")
            customers_df = create_editable_dataframe(
                dfs["customers"],
                "customers_table"
            )

    # Parameters Section (expands when data is uploaded)
    parameters_expander = st.expander("⚙️ Parameters", expanded=dfs is not None)
    if dfs is None:
        with parameters_expander:
            st.warning("Please upload your data first.")
    else:
        with parameters_expander:
            st.markdown("Adjust these parameters to fine-tune your optimization:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Facility Parameters")
                facility_params = create_parameter_controls(
                    initial_params={
                        "n_facilities": 3,
                        "facility_capacity": 100000,
                        "fixed_cost": 500000,
                    },
                    param_ranges={
                        "n_facilities": (1, 10, 1),
                        "facility_capacity": (10000, 500000, 10000),
                        "fixed_cost": (10000, 1000000, 10000)
                    }
                )
                
                st.markdown("""
                - **Number of Facilities**: How many facilities to place
                - **Facility Capacity**: Maximum units each facility can handle
                - **Fixed Cost**: One-time cost to open each facility
                """)
            
            with col2:
                st.subheader("Transportation Parameters")
                transport_params = create_parameter_controls(
                    initial_params={
                        "cost_per_km": 1.0,
                        "units_per_load": 100,
                    },
                    param_ranges={
                        "cost_per_km": (0.1, 10.0, 0.1),
                        "units_per_load": (50, 10000, 50)
                    }
                )
                
                st.markdown("""
                - **Cost per KM**: Transportation cost per kilometer
                - **Units per Load**: How many units fit in one shipment
                """)

            st.subheader("PSO Algorithm Parameters")
            col3, col4 = st.columns(2)
            
            with col3:
                pso_params1 = create_parameter_controls(
                    initial_params={
                        "n_particles": 30,
                        "n_iterations": 100,
                        "max_run_time_seconds": 10,
                    },
                    param_ranges={
                        "n_particles": (5, 100, 5),
                        "n_iterations": (10, 500, 10),
                        "max_run_time_seconds": (5, 600, 10)
                    }
                )
                
                st.markdown("""
                - **Number of Particles**: Size of the particle swarm
                - **Number of Iterations**: How long to run the optimization
                """)
            
            with col4:
                pso_params2 = create_parameter_controls(
                    initial_params={
                        "inertia_weight": 0.9,
                        "cognitive_coefficient": 2.0,
                        "social_coefficient": 2.0
                    },
                    param_ranges={
                        "inertia_weight": (0.4, 1.0, 0.1),
                        "cognitive_coefficient": (0.1, 4.0, 0.1),
                        "social_coefficient": (0.1, 4.0, 0.1)
                    }
                )
                
                st.markdown("""
                - **Inertia Weight**: Controls particle momentum
                - **Cognitive Coefficient**: Weight of particle's personal best
                - **Social Coefficient**: Weight of swarm's global best
                """)

            # Combine all parameters
            params = {**facility_params, **transport_params, **pso_params1, **pso_params2}
            
            # Run optimization button
            if st.button("Run Optimization", type="primary"):
                with st.spinner("Optimizing facility locations..."):
                    results = optimize_facility_locations_pso(
                        customers_df,
                        **params
                    )
                    # Store results in session state
                    st.session_state.optimization_results = results
                    # Force the results expander to open
                    st.session_state.show_results = True
                    st.rerun()

    # Results Section (expands when optimization is complete)
    results_expander = st.expander("📊 Results", expanded=st.session_state.get('show_results', False))
    with results_expander:
        if dfs is None:
            st.warning("Please upload your data first.")
        elif 'optimization_results' not in st.session_state:
            st.info("Run the optimization to see results.")
        else:
            results = st.session_state.optimization_results
            
            if results['status'] == 'Optimal':
                # Summary metrics
                st.subheader("Summary")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Cost", f"${results['total_cost']:,.2f}")
                with col2:
                    st.metric("Completed Iterations", f"{results['completed_iterations']}/{params['n_iterations']}")
                with col3:
                    st.metric("Total Time", f"{results['total_time']:.2f} seconds")
                
                # Optimization progress
                st.subheader("Optimization Progress")
                st.line_chart(results['history'].set_index('iteration')['best_score'])
                
                # Detailed results
                st.subheader("Facility Locations")
                st.dataframe(results['facility_locations'])
                
                st.subheader("Customer Assignments")
                st.dataframe(results['assignments'])
                
                # Display map
                st.subheader("Location Map")
                map_deck = create_pso_map(
                    results['facility_locations'],
                    customers_df,
                    results['assignments']
                )
                st.pydeck_chart(map_deck)
                
                st.markdown("""
                **Map Legend:**
                - Blue dots: Customers
                - Green dots: Optimized Facility Locations
                - Purple lines: Transportation Routes
                """)
            else:
                st.error(f"Optimization failed with status: {results['status']}")

if __name__ == "__main__":
    facility_pso_page()