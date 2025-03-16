# ============================
# File: config_utils.py
# ============================
import json
import os

def load_config():
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
        return config
    except FileNotFoundError:
        raise Exception("Config file not found. Please ensure config.json exists in the project directory.")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON format in config file.")
    except Exception as e:
        raise Exception(f"Error loading configuration: {str(e)}")


# ============================
# File: main_app.py
# ============================
import time
import re
import os
import streamlit as st
import firebase_admin
import requests
from firebase_admin import firestore, credentials
from config_utils import load_config

# Initialize Firebase (if not already initialized)
if not firebase_admin._apps:
    firebase_config_path = os.path.join(os.path.dirname(__file__), 'firebase-config.json')
    cred = credentials.Certificate(firebase_config_path)
    firebase_admin.initialize_app(cred)

database = firestore.client()

# Load configuration settings
try:
    config = load_config()
    if not config.get('FIREBASE_API_KEY') or not config.get('FIREBASE_AUTH_DOMAIN'):
        st.error("Missing required Firebase configuration. Please check your config.json file.")
        st.stop()
    FIREBASE_API_KEY = config['FIREBASE_API_KEY']
    FIREBASE_AUTH_DOMAIN = config['FIREBASE_AUTH_DOMAIN']
except Exception as e:
    st.error(f"Configuration Error: {str(e)}")
    st.write("Please ensure config.json exists and contains valid Firebase configuration.")
    st.stop()

# Configure Streamlit page settings
st.set_page_config(
    page_title="DentalEase",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================
# Authentication Functions
# ============================
def sign_in(email, password):
    url = f"{FIREBASE_AUTH_DOMAIN}/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            st.session_state["logged_in"] = True
            st.session_state["doctor_email"] = data.get('email')
            st.session_state["doctor_name"] = data.get('displayName', "Doctor")
            return True, "Logged in successfully!"
        else:
            return False, "Invalid email or password."
    except Exception as e:
        return False, f"An error occurred: {str(e)}"

def sign_up(name, email, password):
    url = f"{FIREBASE_AUTH_DOMAIN}/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "displayName": name,
        "returnSecureToken": True
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            id_token = response.json().get('idToken')
            update_url = f"{FIREBASE_AUTH_DOMAIN}/accounts:update?key={FIREBASE_API_KEY}"
            update_payload = {
                "idToken": id_token,
                "displayName": name,
                "returnSecureToken": True
            }
            update_response = requests.post(update_url, json=update_payload)
            if update_response.status_code == 200:
                return True, "Account created successfully!"
            else:
                return False, "Account created but failed to set name."
        else:
            error_message = response.json().get('error', {}).get('message', 'Unknown error')
            return False, f"Signup failed: {error_message}"
    except Exception as e:
        return False, f"An error occurred: {str(e)}"

def reset_password(email):
    url = f"{FIREBASE_AUTH_DOMAIN}/accounts:sendOobCode?key={FIREBASE_API_KEY}"
    payload = {
        "requestType": "PASSWORD_RESET",
        "email": email
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return True, "Password reset email sent!"
        else:
            return False, "Email not found."
    except Exception as e:
        return False, f"An error occurred: {str(e)}"


# ============================
# Input Validation Functions
# ============================
def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_password(password):
    return len(password) >= 6

def validate_name(name):
    return bool(name.strip()) and len(name) >= 2 and all(char.isalpha() or char.isspace() for char in name)


# ============================
# Navigation and Page Functions
# ============================
def navigate_to_treatment():
    st.session_state.page = "treatment_planner"
    st.rerun()

def navigate_to_login():
    st.session_state.page = "login"
    st.rerun()

def show_treatment_planner():
    st.title("Treatment Planner")
    with st.sidebar:
        st.button("Logout", on_click=logout)
    st.write("Welcome to the Treatment Planner!")
    # Add additional treatment planner components here

def logout():
    st.session_state.clear()
    navigate_to_login()


# ============================
# Main Application Flow
# ============================
def main():
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # Navigation logic
    if st.session_state.page == "treatment_planner":
        if not st.session_state.logged_in:
            navigate_to_login()
        else:
            show_treatment_planner()
            return

    st.title("DentalEase - Login / Registration")

    if st.session_state.logged_in:
        st.success("Already logged in.")
        st.button("Go to Treatment Planner", on_click=navigate_to_treatment, key="nav_treatment")
        return

    tabs = st.tabs(["Login", "Sign Up", "Reset Password"])

    with tabs[0]:
        with st.form("login_form", clear_on_submit=True):
            st.markdown("### Login to Your Account")
            email = st.text_input("Email Address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Login")
            if submit:
                if not email or not password:
                    st.error("Please fill in all fields.")
                elif not validate_email(email):
                    st.error("Please enter a valid email address.")
                else:
                    success, message = sign_in(email, password)
                    if success:
                        st.success(message)
                        time.sleep(1)
                        navigate_to_treatment()
                    else:
                        st.error(message)

    with tabs[1]:
        with st.form("signup_form", clear_on_submit=True):
            st.markdown("### Create New Account")
            name = st.text_input("Full Name", key="signup_name")
            email = st.text_input("Email Address", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
            submit = st.form_submit_button("Sign Up")
            if submit:
                if not name or not email or not password or not confirm_password:
                    st.error("Please fill in all fields.")
                elif not validate_name(name):
                    st.error("Please enter a valid name (minimum 2 characters, letters only).")
                elif not validate_email(email):
                    st.error("Please enter a valid email address.")
                elif not validate_password(password):
                    st.error("Password must be at least 6 characters long.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    success, message = sign_up(name, email, password)
                    if success:
                        st.success(message)
                        time.sleep(1)
                    else:
                        st.error(message)

    with tabs[2]:
        with st.form("reset_form", clear_on_submit=True):
            st.markdown("### Reset Password")
            email = st.text_input("Email Address", key="reset_email")
            submit = st.form_submit_button("Send Reset Link")
            if submit:
                if not email:
                    st.error("Please enter your email address.")
                elif not validate_email(email):
                    st.error("Please enter a valid email address.")
                else:
                    success, message = reset_password(email)
                    if success:
                        st.success(message)
                        time.sleep(1)
                    else:
                        st.error(message)

if __name__ == "__main__":
    main()
