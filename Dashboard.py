import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(
    page_title='Dental Flow',
    layout='wide',
    initial_sidebar_state='collapsed'
)

if not firebase_admin._apps:
    cred = credentials.Certificate('firebase-config.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()


def check_doctor_exists(email):
    doctor_ref = db.collection('doctors').document(email)
    return doctor_ref.get().exists


def save_doctor(name, email, password):
    doctor_ref = db.collection('doctors').document(email)
    doctor_ref.set({'name': name, 'email': email, 'password': password})


def verify_doctor(email, password):
    doctor_ref = db.collection('doctors').document(email)
    doc = doctor_ref.get()

    if doc.exists and doc.to_dict().get('password') == password:
        return True
    return False


def reset_password(email):
    new_password = st.text_input("New Password", type='password', key="reset_password")
    confirm_password = st.text_input("Confirm Password", type='password', key="confirm_reset_password")

    if new_password == confirm_password:
        doctor_ref = db.collection('doctors').document(email)
        doctor_ref.update({'password': new_password})
        st.success("Password has been reset successfully!")
    else:
        st.error("Passwords do not match.")


def signup():
    st.subheader("Create a New Account")
    name = st.text_input("Name", key="signup_name")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type='password', key="signup_password")

    if st.button("Signup"):
        if check_doctor_exists(email):
            st.warning("Doctor already exists. Please choose a different email.")
        else:
            save_doctor(name, email, password)
            st.success("Account created successfully! You can now log in.")


def login():
    st.subheader("Login to Your Account")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type='password', key="login_password")

    if st.button("Login"):
        if verify_doctor(email, password):
            st.success(f"Welcome, {email}!")
            st.session_state['logged_in'] = True
            st.session_state['doctor_email'] = email
            st.switch_page("pages/1_Treatment.py")
        else:
            st.error("Invalid email or password.")


def main():
    st.title("Dental Flow")

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        st.subheader(f"Welcome, {st.session_state['email']}!")
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['email'] = None
    else:
        choice = st.selectbox("Choose Action", ["Login", "Signup"])

        if choice == "Signup":
            signup()
        else:
            login()

            # Password Reset Option
            if st.button("Forgot Password"):
                reset_password(st.session_state['email'])


if __name__ == '__main__':
    main()