import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Configure Streamlit page settings
st.set_page_config(
    page_title="Dental Flow",
    page_icon="🦷",
    layout="wide",
    # initial_sidebar_state="collapsed"
)

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("../firebase-config.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()


def main():
    st.title("Dental Flow")

    # Initialize session state for login tracking
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        st.subheader(f"Welcome, Dr. {st.session_state['doctor_email']}!")
        if st.button("Logout"):
            st.session_state.clear()  # Clear session state on logout
            st.rerun()  # Refresh the app
    else:
        action = st.selectbox("Choose Action", ["Sign In", "Sign Up"])

        if action == "Sign Up":
            sign_up()
        else:
            sign_in()

        # Reset password button
        if st.button("Reset Password", icon="🔄"):
            reset_password()


def sign_up():
    st.subheader("Create a New Account")
    name = st.text_input("Name", key="signup_name")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")

    if st.button("Log In", icon="🔒"):
        try:
            # Create user in Firebase Authentication
            user = auth.create_user(email=email, password=password)

            # Store user details in Firestore
            db.collection("doctors").document(email).set({
                "name": name,
                "email": email,
                "uid": user.uid
            })

            st.success("Account created successfully! You can now sign in.")
        except firebase_admin.auth.EmailAlreadyExistsError:
            st.warning("Email already in use. Please choose a different email.")
        except Exception as e:
            st.error(f"Error: {e}")


def sign_in():
    st.subheader("Sign In to Your Account")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Log In", icon="🔓"):
        try:
            # Verify user exists in Firebase Authentication
            user = auth.get_user_by_email(email)

            # Store session details
            st.success(f"Welcome, {email}!")
            st.session_state["logged_in"] = True
            st.session_state["doctor_email"] = email

            # Redirect to treatment page
            st.switch_page("pages/1_Treatment.py")
        except firebase_admin.auth.UserNotFoundError:
            st.error("Invalid email or password.")
        except Exception as e:
            st.error(f"Error: {e}")


def reset_password():
    email = st.text_input("Enter your email", key="reset_email")
    if st.button("Send Reset Email", icon="🔄"):
        try:
            auth.generate_password_reset_link(email)  # Send password reset email
            st.success("Password reset email sent. Check your inbox.")
        except firebase_admin.auth.UserNotFoundError:
            st.error("Email not found.")
        except Exception as e:
            st.error(f"Error: {e}")


if __name__ == "__main__":
    main()
