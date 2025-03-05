import streamlit as st
from utils import show_footer

def main():
    st.title("Doctor Settings")

    if st.session_state.get('doctor_email') is None:
        st.error("Doctor Authentication Required: Please log in to access doctor settings.")
        return

main()
show_footer()
