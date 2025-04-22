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
    st.image('assets/header2.jpg', use_container_width=True)
    st.error("NOTE: The application is currently in alpha phase (v0.5). Some features are limited and undergoing development", icon="⚠")

    # Initialize session state for login tracking
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

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

        # Privacy Policy section
        st.divider()
        show_privacy_policy()

        # Support section
        # st.divider()
        # show_support()

        # Team section
        # st.divider()
        # show_team()
    else:
        # Non-logged in user view
        # Create two columns for description and login
        desc_col, auth_col = st.columns([1, 1])

        with desc_col:
            show_info()

        with auth_col:
            tab1, tab2, tab3= st.tabs(["Sign In", "Sign Up", "Reset Password"])

            with tab1:
                sign_in()

            with tab2:
                sign_up()

            with tab3:
                reset_password()

        # Privacy Policy section
        st.divider()
        show_privacy_policy()

        # Support section
        # st.divider()
        # show_support()

        # Team section
        # st.divider()
        # show_team()


def show_info():
    st.markdown("""
    <div style="background-color: #ffffff; border-radius: 6px; padding: 12px; margin-bottom: 14px; border: 1px solid #eaedf2;">
        <h2 style="color: #3d4a41; margin-top: 0; font-size: 22px; font-weight: 600;">What is Dentist Friend?</h2>
        <p style="font-size: 15px; line-height: 1.4; color: #444;">
            Dentist Friend is a comprehensive dental practice management solution that streamlines
            patient treatment, inventory management, and communication for efficient clinic operations.
        </p>
    </div>

    <div style="background-color: #ffffff; border-radius: 6px; padding: 12px; border: 1px solid #eaedf2;">
        <h2 style="color: #3d4a41; margin-top: 0; font-size: 22px; font-weight: 600;">Key Features</h2>
        <ul style="font-size: 15px; line-height: 1.4; padding-left: 18px; color: #444;">
            <li><strong>Patient Management</strong>: Register patients, search records, and manage treatments with dental charts, procedures,
            cost summaries, and PDF export.</li>
            <li><strong>Inventory Management</strong>: Add, remove, and modify inventory items with alerts for low stock and expiring items.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


def show_support():
    st.markdown("## ❤️ Support Dentist Friend")
    st.markdown("""
    Thank you for considering supporting Dentist Friend! Your donations help us improve our services and develop new features.

    ### Donation Options:
    - **UPI**: Dentist Friend@upi

    Every contribution helps us make dental practice management better for everyone. Thank you for your support!
    """)


def show_team():
    st.markdown("## 🛠️ Team")
    team_col1, team_col2 = st.columns(2)

    with team_col1:
        st.image("assets/noor.jpg", caption="Dr. Noor Hebbal", use_container_width=True)
        st.markdown("**Dentist, BDS**")
        st.markdown("Al-Ameen Dental College, Vijayapura (1996-2001)")
        st.markdown("📧 Contact: [noordentist@gmail.com](mailto:noordentist@gmail.com)")

    with team_col2:
        st.image("assets/areeb.jpg", caption="Areeb Ahmed", use_container_width=True)
        st.markdown("**Student Developer, B.E CSE**")
        st.markdown("Dayananda Sagar College of Engineering, Bangaluru (2022-2026)")
        st.markdown("📧 Contact: [hi@areeb.cloud](mailto:hi@areeb.cloud)")


def show_privacy_policy():
    with st.expander("**Privacy Policy**"):
        st.markdown("""
        # Privacy Policy

        Your privacy and security are of utmost importance to us. This policy describes how we collect and use information about you when you use Dentist Friend, including our application and website. If you are one of our customers, you should read this policy in conjunction with our Terms of Service.

        ### 1. Who are we?

        We are Dentist Friend, a dental practice management solution. The processing explained in this policy is carried out by Dentist Friend as the data controller. This means that we are responsible for deciding how we hold and use personal data about you.

        ### 2. How do we collect your data?

        We collect information about you when you:
        - Create an account on our platform
        - Input patient information into our system
        - Use our inventory management features
        - Contact our support team
        - Fill in forms on our website

        We strictly adhere to a data minimization approach and only collect information that is necessary for providing our services.

        ### 3. What data do we collect?

        We collect only essential information needed to provide our services:

        **Personal data**: This includes information that identifies you, such as:
        - Your name, clinic name, and contact details
        - Login credentials
        - Patient records you enter into our system
        - Communication records when you interact with our support team

        **Non-personal data**: We do not collect any additional non-personal data beyond what is strictly necessary for the application to function.

        The data you submit should not include sensitive personal data beyond what is necessary for dental practice management.

        ### 4. How do we use your data?

        We use the information we collect to:
        - Create and maintain your account
        - Provide our dental practice management services
        - Respond to support requests
        - Communicate with you about our services
        - Process payments if you subscribe to a paid plan
        - Ensure compliance with applicable laws and regulations

        We do not use your data for analytics, marketing research, or any purpose beyond providing the core functionality of our platform.

        ### 5. What are our purposes and legal basis for collecting your personal data?

        We collect your personal data because:
        - It's necessary to perform our contract with you
        - You've given consent for specific purposes
        - We have legitimate interests in providing our services

        ### 6. With whom do we share personal data?

        We share your data only in limited circumstances and strictly on a need-to-know basis:

        - **Cloud Service Providers**: We use secure cloud hosting services to store your data
        - **Payment Processors**: For processing subscription payments
        - **Email Service Providers**: To send notifications and communications

        We do not sell, rent, or share your data with third parties for marketing purposes, analytics, or any other purpose beyond what is necessary to provide our services.

        ### 7. For how long do we retain your personal data?

        We keep your personal data for as long as necessary to provide our services or as required by law. If you delete your account, we will remove your personal data from our active systems within 90 days, though some information may remain in backups for legal and technical reasons.

        ### 8. How do we transfer your data?

        Dentist Friend complies with data protection regulations. We implement appropriate safeguards when transferring data, including encryption and access controls.

        ### 9. What are your rights regarding your personal data?

        You have the right to:
        - Access your personal data
        - Correct inaccurate information
        - Request deletion of your data
        - Object to processing of your data
        - Request restriction of processing
        - Data portability
        - Withdraw consent

        To exercise these rights, please contact us at privacy@dentistfriend.in

        ### 10. Security
        
        We implement robust security measures to protect your personal information. This includes encryption, secure data centers, and strict access controls. We prioritize the security of your data and regularly review our security practices to maintain the highest standards. However, no method of transmission over the internet is 100% secure, so while we use industry-best practices, we cannot guarantee absolute security.

        ### 11. Changes to this policy

        We may update this policy periodically. If we make significant changes, we will notify you via email or through our application. Any changes will take effect 30 days after the update date.

        Last revised: April 17, 2025
        """)


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
    name = st.text_input("Name", key="signup_name")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")

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
    email = st.text_input("Email", key="signin_email")
    password = st.text_input("Password", type="password", key="signin_password")

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

    # with col2:
    #     if st.button("Reset Password", icon="🔄", use_container_width=True):
    #         reset_password()


def reset_password():
    email = st.text_input("Enter your email")
    api_key = os.getenv("FIREBASE_API_KEY")

    if st.button("Send Reset Email", icon="🔄", use_container_width=True):
        if not email:
            st.error("Please enter your email address.")
        else:
            endpoint = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
            payload = {
                "requestType": "PASSWORD_RESET",
                "email": email
            }

            response = requests.post(endpoint, json=payload)
            if response.status_code == 200:
                st.success(f"Password reset email sent to {email}.")
            else:
                error_info = response.json().get("error", {}).get("message", "Unknown error")
                st.error(f"Failed to send reset email: {error_info}")


def reset_email():
    # Get the currently stored email from session state
    current_email = st.session_state.get("doctor_email")
    new_email = st.text_input("New Email Address")

    if st.button("Update Email", icon="📧", use_container_width=True):
        if not new_email:
            st.error("Please enter a new email address.")
            return

        try:
            # Fetch the user details using the current email
            user = auth.get_user_by_email(current_email)
            auth.update_user(user.uid, email=new_email)  # Update email in authentication system

            # Retrieve doctor data from Firestore
            doctor_doc = database.collection("doctors").document(current_email).get()
            doctor_data = doctor_doc.to_dict()

            # Update email field in the retrieved data
            doctor_data["email"] = new_email
            database.collection("doctors").document(new_email).set(doctor_data)  # Save with new email

            # Delete the old document associated with the previous email
            database.collection("doctors").document(current_email).delete()

            # Update session state with the new email
            st.session_state["doctor_email"] = new_email
            st.success("Email updated successfully!")
            st.rerun()  # Refresh the app to reflect changes

        except firebase_admin.auth.EmailAlreadyExistsError:
            st.error("Email already in use.")  # Handle case where new email is already taken
        except Exception as e:
            st.error(f"Error: {e}")  # Handle any other unexpected errors


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
