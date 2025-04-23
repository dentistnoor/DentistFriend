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
    tab1, tab2, tab3, tab4 = st.tabs(["Treatment Procedures", "Dental Chart", "Currency Settings", "Profile Settings"])

    with tab1:
        show_treatments(database, doctor_email, doctor_settings)

    with tab2:
        show_chart(database, doctor_email, doctor_settings)

    with tab3:
        show_currency(database, doctor_email, doctor_settings)

    with tab4:
        show_profile(database, doctor_email)


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
                "health_conditions": ["Healthy"],
                "condition_colors": {"Healthy": "#4CAF50"},
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
                st.write("")
                st.write("")
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

        if st.button("✔️ Save Procedure", use_container_width=True):
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


def show_chart(database, doctor_email, doctor_settings):
    """Display health conditions and dental chart settings."""
    st.header("Dental Chart Configuration")
    st.info("Customize your dental chart settings and health conditions")

    # Load current health conditions and colors
    health_conditions = doctor_settings.get("health_conditions", ["Healthy"])
    condition_colors = doctor_settings.get("condition_colors", {"Healthy": "#4CAF50"})

    st.subheader("Tooth Health Conditions")
    with st.container(border=True):
        if health_conditions:
            for i, condition in enumerate(health_conditions):
                cols = st.columns([5, 2, 1])

                with cols[0]:
                    new_condition = st.text_input(
                        f"Condition {i+1}",
                        value=condition,
                        key=f"condition_{i}"
                    ).strip()
                    health_conditions[i] = new_condition

                with cols[1]:
                    current_color = condition_colors.get(condition, "#FFFFFF")
                    new_color = st.color_picker(
                        "Color",
                        value=current_color,
                        key=f"color_{i}"
                    )
                    condition_colors[condition] = new_color

                with cols[2]:
                    if i > 0:  # Only show delete button for non-first conditions
                        # Add vertical spacing to align with inputs
                        st.write("")
                        st.write("")
                        if st.button("❌", key=f"delete_condition_{i}"):
                            health_conditions.pop(i)
                            if condition in condition_colors:
                                condition_colors.pop(condition)

                            doctor_settings["health_conditions"] = health_conditions
                            doctor_settings["condition_colors"] = condition_colors
                            save_settings(database, doctor_email, doctor_settings)
                            st.success("Health condition removed successfully")
                            st.rerun()
        else:
            st.caption("No health conditions defined. Add at least one condition.")

    with st.expander("Add New Health Condition", expanded=True):
        cols = st.columns([5, 2])

        with cols[0]:
            new_condition = st.text_input(
                "New Health Condition",
                key="new_health_condition"
            ).strip()

        with cols[1]:
            new_color = st.color_picker(
                "Select color",
                value="#808080",  # Default gray for new conditions
                key="new_condition_color"
            )

        if st.button("✔️ Add Health Condition", use_container_width=True):
            if new_condition:
                if new_condition.lower() not in [c.lower() for c in health_conditions]:
                    health_conditions.append(new_condition)
                    condition_colors[new_condition] = new_color

                    doctor_settings["health_conditions"] = health_conditions
                    doctor_settings["condition_colors"] = condition_colors
                    save_settings(database, doctor_email, doctor_settings)
                    st.success(f"New health condition '{new_condition}' added successfully")
                    st.rerun()
                else:
                    st.error("This health condition already exists")
            else:
                st.error("Please enter a health condition name")

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


def show_profile(database, doctor_email):
    """Display and manage doctor profile settings."""
    st.header("Profile Settings")
    st.info("Update your profile information")

    try:
        # Get current doctor information
        doctor_ref = database.collection("doctors").document(doctor_email)
        doctor_doc = doctor_ref.get()

        if doctor_doc.exists:
            doctor_data = doctor_doc.to_dict()
            current_name = doctor_data.get("name", "")

            # Display form to edit doctor name
            with st.container(border=True):
                st.subheader("Your Information")
                new_name = st.text_input("Doctor Name", value=current_name)

                if st.button("✔️ Update Profile", use_container_width=True):
                    if new_name != current_name:
                        # Update name in Firestore
                        doctor_ref.update({"name": new_name})
                        # Update session state
                        st.session_state["doctor_name"] = new_name
                        st.success("Profile updated successfully!")
                        st.rerun()
        else:
            st.error("Doctor profile not found. Please contact support.")
    except Exception as e:
        st.error(f"Error loading profile: {e}")


main()
show_footer()
