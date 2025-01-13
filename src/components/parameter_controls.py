import streamlit as st
import pandas as pd
from typing import Dict, Any

def create_parameter_controls(
    initial_params: Dict[str, Any],
    param_ranges: Dict[str, tuple]
) -> Dict[str, Any]:
    """Creates parameter control sliders based on initial values and ranges"""
    
    params = {}
    for param_name, initial_value in initial_params.items():
        if param_name in param_ranges:
            min_val, max_val, step_val = param_ranges[param_name]
            params[param_name] = st.slider(
                param_name,
                min_value=min_val,
                max_value=max_val,
                step = step_val,
                value=initial_value
            )
    return params

def create_editable_dataframe(
    df: pd.DataFrame,
    key: str
) -> pd.DataFrame:
    """Creates an editable dataframe"""
    return st.data_editor(df, key=key)