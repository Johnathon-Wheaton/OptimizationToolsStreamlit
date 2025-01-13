import streamlit as st
from src.components.file_handlers import handle_template_download, handle_file_upload
from src.components.parameter_controls import create_parameter_controls
from src.optimization.hub_network import optimize_hub_network
from src.utils.hub_network_mapping import create_hub_network_map

def hub_network_page():
    st.title("Hub Network Optimization")

    with st.expander("📃 Overview", expanded=True):
        st.markdown("""
        ### Overview
        This tool optimizes a hub-and-spoke distribution network by selecting optimal hub locations and determining 
        shipping routes. It allows for both direct shipments and hub-mediated shipments to minimize total costs.
        
        #### What this model considers:
        - Fixed costs of opening hubs
        - Transportation costs based on distance
        - Load consolidation at hubs
        - Direct shipping options
        - Minimum cost per load constraints
        
        #### Required Input Data:
        1. **Origins**: Source locations with:
            - City name
            - Latitude/longitude coordinates
            
        2. **Candidate Hubs**: Potential hub locations with:
            - City name
            - Latitude/longitude coordinates
            - Fixed cost to open
            
        3. **Destinations**: Delivery locations with:
            - City name
            - Latitude/longitude coordinates
            
        4. **Demand**: Origin-destination flow requirements with:
            - Origin city
            - Destination city
            - Demand volume
        """)

    # Data Input Section
    with st.expander("📥 Data Input", expanded=True):
        st.subheader("1. Download Template")
        handle_template_download(
            "templates/hub_network.xlsx",
            "Hub Network"
        )
        
        st.subheader("2. Upload Data")
        dfs, error = handle_file_upload(
            ["origins", "candidate_hubs", "destinations", "demand"]
        )

        if error:
            st.error(error)
            return

        if dfs is not None:
            st.success("Data uploaded successfully!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Origins")
                st.dataframe(dfs["origins"])
                
                st.subheader("Candidate Hubs")
                st.dataframe(dfs["candidate_hubs"])
            
            with col2:
                st.subheader("Destinations")
                st.dataframe(dfs["destinations"])
                
                st.subheader("Demand")
                st.dataframe(dfs["demand"])

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
                st.subheader("Network Parameters")
                network_params = create_parameter_controls(
                    initial_params={
                        "max_hubs": 3,
                        "cost_per_unit_distance": 2.0,
                        "minimum_cost_per_load": 100,
                    },
                    param_ranges={
                        "max_hubs": (0, 10, 1),  # min, max, step
                        "cost_per_unit_distance": (0.1, 10.0, 0.1),
                        "minimum_cost_per_load": (0, 1000, 10)
                    }
                )
                
                st.markdown("""
                - **Max Hubs**: Maximum number of hubs to open
                - **Cost per Unit Distance**: Transportation cost per distance unit
                - **Minimum Cost per Load**: Base cost per shipment
                """)
            
            with col2:
                st.subheader("Solver Parameters")
                solver_params = create_parameter_controls(
                    initial_params={
                        "capacity_per_shipment": 3000,
                        "time_limit": 300,
                        "optimality_gap": 0.01,
                    },
                    param_ranges={
                        "capacity_per_shipment": (100, 10000, 100),
                        "time_limit": (10, 3600, 10),
                        "optimality_gap": (0.001, 0.1, 0.001)
                    }
                )
                
                st.markdown("""
                - **Capacity per Shipment**: Maximum units per load
                - **Time Limit**: Maximum solver runtime in seconds
                - **Optimality Gap**: Relative optimality gap (smaller = more precise)
                """)
            
            params = {**network_params, **solver_params}
            
            # Run optimization button
            if st.button("Run Optimization", type="primary"):
                with st.spinner("Optimizing hub network..."):
                    try:
                        results = optimize_hub_network(
                            dfs["origins"],
                            dfs["candidate_hubs"],
                            dfs["destinations"],
                            dfs["demand"],
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
            
            if results['status'] == 'Optimal':
                # Summary metrics
                st.subheader("Summary")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Cost", f"${results['total_cost']:,.2f}")
                with col2:
                    st.metric("Selected Hubs", 
                             str(results['facilities']['IsOpen'].sum()))
                with col3:
                    st.metric("Solver Time", 
                             f"{results['solver_time']:.1f} sec" if results['solver_time'] else "N/A")

                # Hub selection results
                st.subheader("Selected Hubs")
                selected_hubs = results['facilities'][results['facilities']['IsOpen']]
                st.dataframe(selected_hubs)
                
                # Flow details
                st.subheader("Flow Details")
                
                # Direct flows
                direct_flows = results['connections'][results['connections']['Type'] == 'Direct']
                if not direct_flows.empty:
                    st.subheader("Direct Shipments")
                    st.dataframe(direct_flows)
                
                # Hub flows
                hub_flows = results['connections'][results['connections']['Type'] == 'Hub']
                if not hub_flows.empty:
                    st.subheader("Hub-Mediated Shipments")
                    st.dataframe(hub_flows)
                
                # Display map
                st.subheader("Network Map")
                map_result = create_hub_network_map(
                    results['connections'],
                    results['facilities'],
                    dfs["origins"],
                    dfs["destinations"],
                    dfs["candidate_hubs"]
                )
                st.pydeck_chart(map_result['deck'])
                
                # Map legend
                st.markdown("""
                **Legend:**
                - 🔴 Origins
                - 🟢 Selected Hubs
                - ⚪ Unselected Hubs
                - 🔵 Destinations
                - Purple lines show shipping routes (width indicates volume)
                """)
                
            else:
                st.error(f"Optimization failed with status: {results['status']}")

if __name__ == "__main__":
    hub_network_page()