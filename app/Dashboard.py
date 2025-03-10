import hashlib
import datetime
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
from utils import show_footer

# Configure Streamlit page settings
st.set_page_config(
    page_title="Dental Flow",
    page_icon="🦷",
    layout="wide",
    # initial_sidebar_state="collapsed"
)

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-config.json")
    firebase_admin.initialize_app(cred)

database = firestore.client()


def main():
    st.title("🦷 Dental Flow")
    st.error("NOTE: The application is currently in alpha phase (v0.5). Some features are limited and undergoing development", icon="⚠️")

    # Initialize session state for login tracking
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    # Display content based on login status
    if st.session_state["logged_in"]:
        # Logged-in user view
        current_date = datetime.datetime.now()
        date_str = current_date.strftime("%A, %B %d, %Y")
        time_str = current_date.strftime("%H:%M %p")

        st.subheader(f"Welcome, Dr. {st.session_state['doctor_name']}!")
        st.caption(f"{date_str} | {time_str}")

        show_nav()

        # Logout, Reset Password, and Delete Account buttons
        st.divider()
        st.markdown("### Account Settings")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("Logout", icon="↩️", use_container_width=True):
                st.session_state.clear()  # Clear session state on logout
                st.rerun()  # Refresh the app

        with col2:
            if st.button("Reset Password", icon="🔄", use_container_width=True):
                reset_password()

        with col3:
            if st.button("Reset Email", icon="📧", use_container_width=True):
                reset_email()

        with col4:
            if st.button("Delete Account", icon="🗑️", use_container_width=True):
                delete_account()

        # Support section
        st.divider()
        show_support()

        # Team section
        st.divider()
        show_team()
    else:
        # Non-logged in user view
        show_info()
        st.divider()

        # Authentication section
        action = st.selectbox("Choose Action", ["Sign In", "Sign Up"])

        if action == "Sign Up":
            sign_up()
        else:
            sign_in()

        st.divider()
        show_support()

        # Team section for non-logged in users
        st.divider()
        show_team()


def show_info():
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            """
            ## What is Dental Flow?

            **Dental Flow** is an advanced dental practice management solution designed specifically 
            for dental professionals in rural or remote areas where access to such systems is limited 
            or prohibitively expensive. This comprehensive platform streamlines various aspects of 
            dental practice management, making it easier for dentists to manage patient treatment plans, 
            inventory, and communication smoothly.

            ### Key Features
            - **Patient Management:** Register new patients, search for existing patients, and manage 
              detailed treatment plans, including dental chart assessments, treatment procedures, 
              cost summaries, scheduling, and PDF generation.
            - **Inventory Management:** Add, remove, and modify inventory items with alerts for low stock 
              and expiring items.
            - **Direct Messaging:** Secure communication for appointment reminders, treatment discussions, 
              and follow-ups.
            """
        )

    with col2:
        st.image("assets/logo.jpg", caption="Demo Video Coming Soon")


def show_support():
    st.markdown("## ❤️ Support Dental Flow")
    st.markdown("""
    Thank you for considering supporting Dental Flow! Your donations help us improve our services and develop new features.

    ### Donation Options:
    - **UPI**: dentalflow@upi

    Every contribution helps us make dental practice management better for everyone. Thank you for your support!
    """)


def show_team():
    st.markdown("## 🛠️ Team")
    team_col1, team_col2 = st.columns(2)

    with team_col1:
        st.image("assets/noor.jpg", caption="Dr. Noor Hebbal", use_container_width=True)
        st.markdown("**Bachelor of Dental Surgery**")
        st.markdown("Al-Ameen Dental College, Vijayapura (1996-2001)")
        st.markdown("📧 Contact: [noordentist@gmail.com](mailto:noordentist@gmail.com)")

    with team_col2:
        st.image("assets/areeb.jpg", caption="Areeb Ahmed", use_container_width=True)
        st.markdown("**Student Developer, B.E CSE**")
        st.markdown("Dayananda Sagar College of Engineering, Bangaluru (2022-2026)")
        st.markdown("📧 Contact: [hi@areeb.cloud](mailto:hi@areeb.cloud)")


def show_nav():
    st.markdown("### Quick Access")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("📋 Treatment", use_container_width=True):
            st.switch_page("pages/1_Treatment.py")

    with col2:
        if st.button("📦 Inventory", use_container_width=True):
            st.switch_page("pages/2_Inventory.py")

    with col3:
        if st.button("💬 Chat", use_container_width=True):
            st.switch_page("pages/3_Chat.py")

    with col4:
        if st.button("📞 Contact", use_container_width=True):
            st.switch_page("pages/4_Contact.py")

    with col5:
        if st.button("⚙️ Settings", use_container_width=True):
            st.switch_page("pages/5_Settings.py")

    st.info("First-time user? Configure your settings to get started")


def sign_up():
    st.subheader("Create a New Account")
    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up", icon="🔒", use_container_width=True):
        try:
            # Create user in Firebase Authentication
            user = auth.create_user(email=email, password=password)

            # Store user details in Firestore
            database.collection("doctors").document(email).set({
                "name": name,
                "email": email,
                "uid": user.uid,
                "password_hash": hashlib.sha256(password.encode()).hexdigest()
            })

            st.success("Account created successfully! You can now sign in.")
        except firebase_admin.auth.EmailAlreadyExistsError:
            st.warning("Email already in use. Please choose a different email.")
        except Exception as e:
            st.error(f"Error: {e}")


def sign_in():
    st.subheader("Sign In to Your Account")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)  # Split into two columns

    with col1:
        if st.button("Log In", icon="🔓", use_container_width=True):
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                try:
                    # Check if user exists in Firestore
                    doctor_doc = database.collection("doctors").document(email).get()
                    if doctor_doc.exists:
                        doctor_data = doctor_doc.to_dict()
                        stored_hash = doctor_data.get("password_hash", "")

                        # Check if entered password matches stored hash
                        entered_hash = hashlib.sha256(password.encode()).hexdigest()
                        if entered_hash == stored_hash:
                            doctor_name = doctor_data.get("name", "")

                            st.success(f"Welcome, Dr. {doctor_name}!")
                            st.session_state["logged_in"] = True
                            st.session_state["doctor_name"] = doctor_name
                            st.session_state["doctor_email"] = email

                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
                    else:
                        st.error("User not found. Please check your email or create an account.")
                except Exception as e:
                    st.error(f"Error: {e}")

    with col2:
        if st.button("Reset Password", icon="🔄", use_container_width=True):
            reset_password()


def reset_password():
    st.error("This feature is currently development")
    # email = st.text_input("Enter your email")
    # if st.button("Send Reset Email", icon="🔄", use_container_width=True):
    #     if not email:
    #         st.error("Please enter your email address.")
    #     else:
    #         try:
    #             # TODO: https://firebase.google.com/docs/auth/admin/email-action-links
    #             action_code_settings = auth.ActionCodeSettings(
    #                 url="http://127.0.0.1:8501",
    #             )
    #             auth.generate_password_reset_link(email, action_code_settings)
    #             st.success("Password reset email sent. Check your inbox.")
    #         except firebase_admin.auth.UserNotFoundError:
    #             st.error("Email not found.")
    #         except Exception as e:
    #             st.error(f"Error: {e}")


# TODO: Change email address in Firestore and Firebase Authentication
def reset_email():
    st.error("This feature is currently development")


def delete_account():
    email = st.session_state.get("doctor_email")
    if st.button("Confirm Deletion", icon="⚠️", use_container_width=True):
        try:
            # Delete document from Firestore
            database.collection("doctors").document(email).delete()

            # Delete user from Firebase Authentication
            user = auth.get_user_by_email(email)
            auth.delete_user(user.uid)

            st.success("Account deleted successfully!")
            st.session_state.clear()  # Clear session state
            st.rerun()  # Refresh the app
        except firebase_admin.auth.UserNotFoundError:
            st.error("User not found.")
        except Exception as e:
            st.error(f"Error: {e}")


if __name__ == "__main__":
    main()
    show_footer()
