import streamlit as st
from src.components.file_handlers import handle_template_download, handle_file_upload
from src.components.parameter_controls import create_parameter_controls, create_editable_dataframe
from src.optimization.facility_milp import optimize_facility_locations
from src.utils.milp_mapping import create_optimization_map

def facility_milp_page():
    st.title("Facility Location Optimization (MILP)")
    
    with st.expander("📃 Overview", expanded=True):
        # Model description
        st.markdown("""
        ### Overview
        This tool helps you determine which facilities to open from a set of candidate locations to minimize total costs while meeting customer demand. It uses Mixed Integer Linear Programming (MILP) to solve the problem.
        
        #### What this model considers:
        - Fixed costs of opening facilities
        - Transportation costs based on distance
        - Facility capacity constraints
        - Customer demand requirements
        
        #### Required Input Data:
        1. **Facilities**: List of potential facility locations with:
            - Fixed costs to open each facility
            - Maximum capacity per facility
            - Location coordinates (latitude/longitude)
        
        2. **Customers**: List of customer locations with:
            - Demand quantities
            - Location coordinates (latitude/longitude)
        
        3. **Distances**: Matrix of distances between each facility and customer
        """)

    # Data Input Section (expanded by default)
    with st.expander("📥 Data Input", expanded=True):
        # Template download section
        st.subheader("1. Download Template")
        handle_template_download(
            "templates/facility_milp.xlsx",
            "Facility Location MILP"
        )
        
        # File upload section
        st.subheader("2. Upload Data")
        dfs, error = handle_file_upload(["facilities", "customers", "distances"])
        
        if error:
            st.error(error)
            return
            
        if dfs is not None:
            st.success("Data uploaded successfully! Review your data in the tables below:")
            
            # Create editable tables
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Facilities")
                facilities_df = create_editable_dataframe(
                    dfs["facilities"],
                    "facilities_table"
                )
            
            with col2:
                st.subheader("Customers")
                customers_df = create_editable_dataframe(
                    dfs["customers"],
                    "customers_table"
                )
            
            st.subheader("Distances")
            distances_df = create_editable_dataframe(
                dfs["distances"],
                "distances_table"
            )

    # Parameters Section (expands when data is uploaded)
    parameters_expander = st.expander("⚙️ Parameters", expanded=dfs is not None)
    if dfs is None:
        with parameters_expander:
            st.warning("Please upload your data first.")
    else:
        with parameters_expander:
            st.markdown("""
            Adjust these parameters to fine-tune your optimization:
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Cost Parameters")
                params = create_parameter_controls(
                    initial_params={
                        "facility_fixed_cost_multiplier": 1.0,
                        "cost_per_unit_distance": 1.0,
                    },
                    param_ranges={
                        "facility_fixed_cost_multiplier": (0.1, 10.0,0.1),
                        "cost_per_unit_distance": (0.1, 10.0,0.1),
                    }
                )
                
                st.markdown("""
                - **Facility Fixed Cost Multiplier**: Adjusts the weight of facility opening costs
                - **Cost per Unit Distance**: Adjusts the weight of transportation costs
                """)
            
            with col2:
                st.subheader("Solver Parameters")
                solver_params = create_parameter_controls(
                    initial_params={
                        "mip_gap": 0.01,
                        "max_run_time_seconds": 5
                    },
                    param_ranges={
                        "mip_gap": (0.005, 0.1,0.005),
                        "max_run_time_seconds": (5, 600,5)
                    }
                )
                
                st.markdown("""
                - **MIP Gap**: Maximum allowed gap between solution and best bound (smaller = more precise but slower)
                - **Max Runtime**: Maximum time in seconds to spend solving (longer allows for better solutions)
                """)
            
            params.update(solver_params)
            
            # Run optimization button
            if st.button("Run Optimization", type="primary"):
                with st.spinner("Optimizing facility locations..."):
                    results = optimize_facility_locations(
                        facilities_df,
                        customers_df,
                        distances_df,
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
                
                # Detailed results
                st.subheader("Selected Facilities")
                st.dataframe(results['results'])
                
                st.subheader("Transportation Plan")
                st.dataframe(results['transport'])
                
                # Create facility and customer coordinate dictionaries
                facility_coords = dict(zip(facilities_df['FacilityID'], 
                                        zip(facilities_df['Latitude'], 
                                            facilities_df['Longitude'])))
                customer_coords = dict(zip(customers_df['CustomerID'], 
                                        zip(customers_df['Latitude'], 
                                            customers_df['Longitude'])))
                
                # Display map
                st.subheader("Location Map")
                map_deck = create_optimization_map(
                    facilities_df,
                    customers_df,
                    results['transport'],
                    facility_coords,
                    customer_coords,
                    results['results']
                )
                st.pydeck_chart(map_deck)
            else:
                st.error(f"Optimization failed with status: {results['status']}")

if __name__ == "__main__":
    facility_milp_page()