import streamlit as st
from Dashboard import show_support
from utils import show_footer

def chat():
    st.title("Dental Chat System")
    st.markdown("## 🚧 Under Development...")
    st.markdown("The Doctor-Patient Chat feature is coming soon.")

    st.divider()
    show_support()

chat()
show_footer()
