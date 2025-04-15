import json
import streamlit as st
from firebase_admin import firestore
from utils import show_footer, get_currency_symbol

# Load default data from JSON file
with open("app/data.json", "r") as file:
    default_data = json.load(file)


def main():
    st.title("⚙️ Doctor Settings")

    # Check if user is authenticated
    if st.session_state.get("doctor_email") is None:
        st.error("Doctor Authentication Required: Please log in to access settings")
        return

    with st.sidebar:
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    database = firestore.client()
    doctor_email = st.session_state.get("doctor_email")
    doctor_settings = load_settings(database, doctor_email)

    # Create tabs for different setting categories
    tab1, tab2, tab3 = st.tabs(["Treatment Procedures", "Dental Chart", "Currency Settings"])

    with tab1:
        show_treatments(database, doctor_email, doctor_settings)

    with tab2:
        show_chart()

    with tab3:
        show_currency(database, doctor_email, doctor_settings)


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
                "price_estimates": {"Cleaning": 100},
                "currency": "SAR"
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

    # Display existing procedures with their prices
    if procedures:
        for i, procedure in enumerate(procedures):
            cols = st.columns([4, 3, 1])
            with cols[0]:
                st.text(f"Procedure {i+1}")
                new_name = st.text_input(
                    "",
                    value=procedure, 
                    key=f"procedure_{i}",
                    label_visibility="collapsed"
                ).title()
                procedures[i] = new_name

            with cols[1]:
                st.text(f"Price ({doctor_settings.get('currency', 'SAR')})")
                price = prices.get(procedure, 0)
                new_price = st.number_input(
                    "",
                    min_value=0.0,
                    value=float(price),
                    step=10.0,
                    format="%.2f",
                    key=f"price_{procedure}",
                    label_visibility="collapsed"
                )
                if new_price != price:
                    prices[procedure] = new_price

            with cols[2]:
                if st.button("❌", key=f"delete_procedure_{i}"):
                    procedures.pop(i)
                    if procedure in prices:
                        prices.pop(procedure)

                    # Update settings and save to database
                    doctor_settings["treatment_procedures"] = procedures
                    doctor_settings["price_estimates"] = prices
                    save_settings(database, doctor_email, doctor_settings)
                    st.success("Treatment procedure removed successfully")
                    st.rerun()
    else:
        st.caption("No procedures added yet.")

    # Add new procedure section
    with st.expander("Add New Procedure", expanded=True):
        st.subheader("Create a New Procedure")

        cols = st.columns([1, 1])
        with cols[0]:
            st.text("Procedure Name")
            new_procedure = st.text_input(
                "",
                key="new_procedure",
                label_visibility="collapsed"
            ).title()

        with cols[1]:
            st.text(f"Price ({doctor_settings.get('currency', 'SAR')})")
            new_price = st.number_input(
                "",
                min_value=0.0,
                value=0.0,
                step=10.0,
                format="%.2f",
                key="new_procedure_price",
                label_visibility="collapsed"
            )

        if st.button("Save Procedure", use_container_width=True):
            if new_procedure:
                # Check if procedure already exists to avoid duplicates
                if new_procedure not in procedures:
                    procedures.append(new_procedure)
                    prices[new_procedure] = new_price
                    doctor_settings["treatment_procedures"] = procedures
                    doctor_settings["price_estimates"] = prices
                    save_settings(database, doctor_email, doctor_settings)
                    st.success(f"New procedure '{new_procedure}' has been successfully added")
                    st.rerun()
                else:
                    st.error("This procedure already exists in your list")
            else:
                st.error("Please enter a procedure name")


def show_chart():
    """Display dental chart configuration options including the standard teeth notation system."""
    st.header("Dental Chart Configuration")
    st.info("Customize your dental chart settings and health conditions")

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
    st.error("NOTE: Health conditions cannot be modified at this time (under development)", icon="⚠️")
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

    st.subheader("Dental Chart Customization")
    st.error("NOTE: Additional customization options are under development", icon="⏳")


def show_currency(database, doctor_email, doctor_settings):
    """Display and manage currency settings."""
    st.header("Currency Settings")
    st.info("Set your preferred currency for price estimates")

    current_currency = doctor_settings.get("currency", "SAR")
    currency_options = {
        "SAR": "Saudi Riyal (SAR)",
        "INR": "Indian Rupee (₹)"
    }

    # Display currency selection
    with st.container(border=True):
        selected_currency = st.selectbox(
            "Select Currency",
            options=list(currency_options.keys()),
            format_func=lambda x: currency_options[x],
            index=list(currency_options.keys()).index(current_currency) if current_currency in currency_options else 0
        )

        # Save button for currency changes
        if st.button("✔️ Save Currency Preference", use_container_width=True):
            if selected_currency != current_currency:
                doctor_settings["currency"] = selected_currency
                save_settings(database, doctor_email, doctor_settings)
                st.success(f"Currency updated to {currency_options[selected_currency]}")
                st.rerun()


main()
show_footer()
