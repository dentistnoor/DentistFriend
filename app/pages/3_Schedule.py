import streamlit as st
from utils import show_footer

def chat():
    st.title("Dental Scheduling System")
    st.markdown("## 🚧 Under Development...")
    st.markdown("The appointment scheduling feature is coming soon")

    with st.sidebar:
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()


chat()
show_footer()
