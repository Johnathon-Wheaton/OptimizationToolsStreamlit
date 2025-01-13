import streamlit as st
import pandas as pd
from typing import Tuple, Optional

def handle_template_download(template_path: str, template_name: str):
    """Handles template download functionality"""
    with open(template_path, 'rb') as template_file:
        template_bytes = template_file.read()
        
    st.download_button(
        label=f"Download {template_name} Template",
        data=template_bytes,
        file_name=f"{template_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def handle_file_upload(
    allowed_sheets: list[str]
) -> Tuple[Optional[dict[str, pd.DataFrame]], Optional[str]]:
    """Handles file upload and validation"""
    uploaded_file = st.file_uploader("Upload your populated template", type=['xlsx'])
    
    if uploaded_file is not None:
        try:
            # Read all required sheets
            dfs = {}
            xl = pd.ExcelFile(uploaded_file)
            
            # Validate required sheets exist
            missing_sheets = set(allowed_sheets) - set(xl.sheet_names)
            if missing_sheets:
                return None, f"Missing required sheets: {missing_sheets}"
                
            # Read each sheet
            for sheet in allowed_sheets:
                dfs[sheet] = pd.read_excel(uploaded_file, sheet_name=sheet)
                
            return dfs, None
            
        except Exception as e:
            return None, f"Error processing file: {str(e)}"
            
    return None, None