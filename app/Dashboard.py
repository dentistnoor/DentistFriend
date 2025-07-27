import os
import hashlib
import requests
import datetime
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv
from utils import show_footer, custom_css

# Configure Streamlit page settings
st.set_page_config(
    page_title="Dentist Friend",
    page_icon="🦷",
    layout="wide",
    # initial_sidebar_state="collapsed"
)

# Load environment variables from .env file
load_dotenv()

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-config.json")
    firebase_admin.initialize_app(cred)

database = firestore.client()

custom_css()

def main():
    st.image('assets/header.jpg', use_container_width=True)
    st.error("NOTE: The application is currently in alpha phase (v0.5). Some features are limited and undergoing development", icon="⚠")

    # Initialize session state for login tracking
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    # UI flow tracking
    if "show_reset_password" not in st.session_state:
        st.session_state["show_reset_password"] = False
    if "show_reset_email" not in st.session_state:
        st.session_state["show_reset_email"] = False
    if "show_delete_account" not in st.session_state:
        st.session_state["show_delete_account"] = False

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
                st.session_state["show_reset_password"] = True
                st.session_state["show_reset_email"] = False
                st.session_state["show_delete_account"] = False
                st.rerun()  # Force a rerun to show the reset password form

        with col3:
            if st.button("Change Email", icon="📧", use_container_width=True):
                st.session_state["show_reset_email"] = True
                st.session_state["show_reset_password"] = False
                st.session_state["show_delete_account"] = False
                st.rerun()  # Force a rerun to show the reset email form

        with col4:
            if st.button("Delete Account", icon="🗑️", use_container_width=True):
                st.session_state["show_delete_account"] = True
                st.session_state["show_reset_password"] = False
                st.session_state["show_reset_email"] = False
                st.rerun()  # Force a rerun to show the delete account form

        # Show appropriate form based on user selection
        if st.session_state["show_reset_password"]:
            with st.container():
                st.divider()
                reset_password()

        if st.session_state["show_reset_email"]:
            with st.container():
                st.divider()
                reset_email()

        if st.session_state["show_delete_account"]:
            with st.container():
                st.divider()
                delete_account()

    else:
        # Non-logged in user view
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Check if we should show reset password form instead of login/signup
            if st.session_state["show_reset_password"]:
                reset_password()
                if st.button("Back to Login", use_container_width=True):
                    st.session_state["show_reset_password"] = False
                    st.rerun()
            else:
                tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

                with tab1:
                    sign_in()

                with tab2:
                    sign_up()


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
        if st.button("📅 Schedule", use_container_width=True):
            st.switch_page("pages/3_Schedule.py")

    with col4:
        if st.button("📞 Contact", use_container_width=True):
            st.switch_page("pages/4_Contact.py")

    with col5:
        if st.button("⚙️ Settings", use_container_width=True):
            st.switch_page("pages/5_Settings.py")

    st.info("First-time user? Configure your settings to get started")


def sign_up():
    st.subheader("Create a New Account")
    
    with st.form("signup_form"):
        name = st.text_input("Name", key="signup_name")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        
        signup_submitted = st.form_submit_button("Sign Up", icon="🔒", use_container_width=True)

    if signup_submitted:
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
    
    with st.form("signin_form"):
        email = st.text_input("Email", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")
        
        col1, col2 = st.columns(2)  # Split into two columns

        with col1:
            login_submitted = st.form_submit_button("Log In", icon="🔓", use_container_width=True)

        with col2:
            forgot_password = st.form_submit_button("Forgot Password?", use_container_width=True)

    # Handle login submission
    if login_submitted:
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

    # Handle forgot password
    if forgot_password:
        st.session_state["show_reset_password"] = True
        st.rerun()


def reset_password():
    st.subheader("Reset Password")
    api_key = os.getenv("FIREBASE_API_KEY")

    email = st.text_input("Email address", key="reset_email")
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Send Reset Link", key="send_reset", use_container_width=True):
            if not email:
                st.error("Please enter your email address")
                return

            url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
            payload = {
                "requestType": "PASSWORD_RESET",
                "email": email
            }

            with st.spinner("Processing request..."):
                try:
                    response = requests.post(url, json=payload)

                    if response.status_code == 200:
                        st.success("✅ Password reset email sent!")
                        st.info(f"Please check {email} for the reset link (including spam folder)")
                    else:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get("message", "Unknown error")

                        if error_message == "EMAIL_NOT_FOUND":
                            st.error("No account found with this email address")
                        else:
                            st.error(f"Error: {error_message}")

                except Exception as e:
                    st.error(f"Request failed: {str(e)}")

    with col2:
        if st.button("Cancel", key="cancel_reset", use_container_width=True):
            st.session_state["show_reset_password"] = False
            st.rerun()


def reset_email():
    st.subheader("Change Email Address")

    current_email = st.session_state.get("doctor_email")
    st.info(f"Current email: {current_email}")

    new_email = st.text_input("New Email Address", key="new_email_input")
    password = st.text_input("Confirm your password", type="password", key="confirm_password_email_change")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Update Email", key="update_email_btn", use_container_width=True):
            if not new_email:
                st.error("Please enter a new email address.")
                return

            if not password:
                st.error("Please confirm your password.")
                return

            # First verify the password
            try:
                doctor_doc = database.collection("doctors").document(current_email).get()
                if doctor_doc.exists:
                    doctor_data = doctor_doc.to_dict()
                    stored_hash = doctor_data.get("password_hash", "")
                    entered_hash = hashlib.sha256(password.encode()).hexdigest()

                    if entered_hash != stored_hash:
                        st.error("Incorrect password. Email change canceled.")
                        return
                else:
                    st.error("User data not found. Please try logging in again.")
                    return

                with st.spinner("Updating your email address..."):
                    # Get current user object
                    user = auth.get_user_by_email(current_email)

                    try:
                        # Update email in Firebase Authentication
                        auth.update_user(user.uid, email=new_email)
                        # Update Firestore document
                        doctor_data["email"] = new_email

                        # Update Firestore document with new email and delete old one
                        database.collection("doctors").document(new_email).set(doctor_data)
                        database.collection("doctors").document(current_email).delete()

                        # Update session state
                        st.session_state["doctor_email"] = new_email
                        st.success("✅ Email address updated successfully!")
                        st.info(f"Your account is now associated with {new_email}")

                        # Hide the form after successful update
                        st.session_state["show_reset_email"] = False
                        st.rerun()

                    except firebase_admin.auth.EmailAlreadyExistsError:
                        st.error("This email is already associated with another account.")
                    except Exception as e:
                        st.error(f"Failed to update email: {str(e)}")

            except Exception as e:
                st.error(f"Error accessing user data: {str(e)}")

    with col2:
        if st.button("Cancel", key="cancel_email_change", use_container_width=True):
            st.session_state["show_reset_email"] = False
            st.rerun()


def delete_account():
    st.subheader("Delete Account")
    email = st.session_state.get("doctor_email")

    st.warning("Warning: Account deletion is permanent", icon="⚠️")
    password = st.text_input("Please enter your password to confirm", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Permanently Delete My Account", use_container_width=True):
            try:
                # Confirm password before deletion
                doc = database.collection("doctors").document(email).get()
                stored_hash = doc.to_dict().get("password_hash", "")
                entered_hash = hashlib.sha256(password.encode()).hexdigest()

                if entered_hash != stored_hash:
                    st.error("Incorrect password.")
                    return

                # Delete from both Firestore and Firebase Auth
                user = auth.get_user_by_email(email)
                database.collection("doctors").document(email).delete()
                auth.delete_user(user.uid)

                # Clear session state and show success message
                st.success("Account deleted successfully.")
                st.session_state.clear()
                st.rerun()

            except firebase_admin.auth.UserNotFoundError:
                st.error("User not found in authentication.")
            except Exception as e:
                st.error(f"Error during deletion: {str(e)}")

    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state["show_delete_account"] = False
            st.rerun()


if __name__ == "__main__":
    main()
    show_footer()
