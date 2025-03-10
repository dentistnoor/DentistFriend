import json
import streamlit as st
from firebase_admin import firestore
from utils import show_footer

# Load default data from JSON file
with open("./app/data.json", "r") as file:
    default_data = json.load(file)


def main():
    st.title("⚙️ Doctor Settings")

    # Check if user is authenticated
    if st.session_state.get("doctor_email") is None:
        st.error("Doctor Authentication Required: Please log in to access settings")
        return

    # Initialize Firestore database client and retrieve doctor information
    database = firestore.client()
    doctor_email = st.session_state.get("doctor_email")
    doctor_settings = load_settings(database, doctor_email)

    # Create tabs for different setting categories
    tab1, tab2 = st.tabs(["Treatment Procedures", "Dental Chart"])

    with tab1:
        show_treatments(database, doctor_email, doctor_settings)

    with tab2:
        show_chart()


def load_settings(database, doctor_email):
    """Load doctor settings from Firestore or create default settings if none exist."""
    try:
        doctor_ref = database.collection("doctors").document(doctor_email)
        settings_doc = doctor_ref.collection("settings").document("config").get()

        # Check if settings document exists
        if settings_doc.exists:
            settings = settings_doc.to_dict()
        else:
            # Create default settings if none exist
            settings = {
                "treatment_procedures": ["Cleaning"],
                "price_estimates": {"Cleaning": 100}
            }
            save_settings(database, doctor_email, settings)

        return settings
    except Exception as e:
        st.error(f"Settings load failed: {e}")


def save_settings(database, doctor_email, settings):
    """Save updated settings to Firestore database."""
    try:
        doctor_ref = database.collection("doctors").document(doctor_email)
        doctor_ref.collection("settings").document("config").set(settings)
    except Exception as e:
        st.error(f"Settings save failed: {e}")


def show_treatments(database, doctor_email, doctor_settings):
    """Display and manage treatment procedures and price settings."""
    st.header("Treatment Procedures Configuration")
    st.info("Manage your treatment procedures and their associated prices")

    # Extract current procedures and prices from settings
    procedures = doctor_settings.get("treatment_procedures", [])
    prices = doctor_settings.get("price_estimates", {})

    # Treatment procedures section
    st.subheader("Treatment Procedures")
    with st.container(border=True):
        if procedures:
            to_delete = []

            # Display existing procedures with option to edit or delete
            for i, procedure in enumerate(procedures):
                cols = st.columns([4, 1])
                with cols[0]:
                    new_name = st.text_input(f"Procedure {i+1}", value=procedure, key=f"procedure_{i}").title()
                    procedures[i] = new_name
                with cols[1]:
                    if st.button("❌", key=f"delete_procedure_{i}"):
                        to_delete.append(i)

            # Handle procedure deletion
            if to_delete:
                for index in sorted(to_delete, reverse=True):
                    procedure_name = procedures[index]
                    procedures.pop(index)
                    if procedure_name in prices:
                        prices.pop(procedure_name)

                # Update settings and save to database
                doctor_settings["treatment_procedures"] = procedures
                doctor_settings["price_estimates"] = prices
                save_settings(database, doctor_email, doctor_settings)
                st.success("Treatment procedures have been successfully updated")
                st.rerun()
        else:
            st.caption("No procedures added yet.")

        # Add new procedure input
        new_procedure = st.text_input("Add New Procedure", key="new_procedure").title()
        if st.button("➕ Add Procedure", use_container_width=True):
            if new_procedure:
                # Check if procedure already exists to avoid duplicates
                if new_procedure not in procedures:
                    procedures.append(new_procedure)
                    prices[new_procedure] = 0
                    doctor_settings["treatment_procedures"] = procedures
                    doctor_settings["price_estimates"] = prices
                    save_settings(database, doctor_email, doctor_settings)
                    st.success(f"New procedure '{new_procedure}' has been successfully added")
                    st.rerun()
                else:
                    st.error("This procedure already exists in your list")

    # Price estimates section
    st.subheader("Price Estimates (in your local currency)")
    with st.container(border=True):
        if procedures:
            # Display price input fields for each procedure
            for procedure in procedures:
                old_price = prices.get(procedure, 0)
                new_price = st.number_input(
                    f"Price for {procedure}",
                    min_value=0.0,
                    value=float(old_price),
                    step=10.0,
                    format="%.2f",
                    key=f"price_{procedure}"
                )

                if new_price != old_price:
                    prices[procedure] = new_price

            # Save updated prices to database
            if st.button("✔️ Save Price", use_container_width=True):
                doctor_settings["price_estimates"] = prices
                save_settings(database, doctor_email, doctor_settings)
                st.success("Price estimates have been successfully updated")
        else:
            st.caption("Add procedures first to set prices.")


def show_chart():
    """Display dental chart configuration options including the standard teeth notation system."""
    st.header("Dental Chart Configuration")
    st.info("⚠️ NOTE: Health conditions cannot be modified at this time (under development)")

    # Information about the dental notation system
    with st.expander("Dental Notation System", expanded=True):
        st.subheader("FDI World Dental Federation Notation (ISO 3950)")
        st.info("""
        This application uses the FDI (Fédération Dentaire Internationale) notation system, also known as ISO 3950.

        This two-digit system divides the mouth into four quadrants:
        - Upper Right (1): teeth 18-11
        - Upper Left (2): teeth 21-28
        - Lower Right (4): teeth 48-41
        - Lower Left (3): teeth 31-38

        The first digit indicates the quadrant, while the second digit indicates the tooth position from the midline.
        """)

        # Visual representation of the dental quadrants
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Upper Jaw**")
            st.markdown("18 17 16 15 14 13 12 11 | 21 22 23 24 25 26 27 28")
        with col2:
            st.markdown("**Lower Jaw**")
            st.markdown("48 47 46 45 44 43 42 41 | 31 32 33 34 35 36 37 38")

    # Display tooth health conditions (read-only)
    st.subheader("Tooth Health Conditions")
    conditions = default_data.get("health_conditions", [])

    with st.container(border=True):
        if conditions:
            # Show each condition in a disabled text input
            for i, condition in enumerate(conditions):
                st.text_input(
                    f"Condition {i+1}",
                    value=condition,
                    key=f"condition_{i}",
                    disabled=True
                )
        else:
            st.caption("No health conditions available.")

    # Future enhancement section
    st.subheader("Dental Chart Customization")
    st.info("⚠️ NOTE: Additional customization options are under development")


main()
show_footer()
