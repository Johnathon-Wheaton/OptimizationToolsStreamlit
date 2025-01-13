import streamlit as st

st.set_page_config(
    page_title="Optimization Tools",
    page_icon="",
    layout="wide"
)

def main():
    st.title("Optimization Tools")
    st.write("""
    Welcome to the Supply Chain Optimization Suite. This application provides various 
    tools for optimizing facility locations and vehicle routing problems.
    
    Select a tool from the sidebar to get started.
    """)

if __name__ == "__main__":
    main()