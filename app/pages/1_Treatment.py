import json
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from firebase_admin import firestore
from utils import show_footer, generate_pdf

# Initialize session state variables
if 'patient_status' not in st.session_state:
    st.session_state.patient_status = False

if 'treatment_record' not in st.session_state:
    st.session_state.treatment_record = []

# Load dental procedures and pricing data
with open('data.json', 'r') as file:
    dental_data = json.load(file)

database = firestore.client()


def validate_color(color):
    """Validate if color value is proper"""
    if color.startswith('#'):
        return len(color) in [4, 7]  # Valid hex color
    return color in {'green', 'red', 'orange', 'gray', 'brown', 'lightgray', 'white', 'black'}


def store_patient(doctor_email, patient_info):
    """Store new patient information in Firestore"""
    doctor_reference = database.collection('doctors').document(doctor_email)
    doctor_reference.collection('patients').document(patient_info["file_id"]).set(patient_info)


def fetch_patient(doctor_email, file_id):
    """Retrieve patient data from Firestore"""
    doctor_reference = database.collection('doctors').document(doctor_email)
    patient_document = doctor_reference.collection('patients').document(file_id).get()
    if patient_document.exists:
        return patient_document.to_dict()
    return None


def modify_treatment(doctor_email, file_id, treatment_record):
    """Update patient's treatment plan"""
    doctor_reference = database.collection('doctors').document(doctor_email)
    patient_document = doctor_reference.collection('patients').document(file_id)
    patient_document.update({'treatment_plan': treatment_record})


def format_date(dt, fmt='%Y-%m-%d'):
    """Format dates consistently"""
    return dt.strftime(fmt)


def create_tooth_svg(tooth_number, condition):
    """Create SVG with proper color mapping and contrast"""
    color_map = {
        "Healthy": "#28a745",  # Darker green for better visibility
        "Cavity": "#dc3545",  # Bootstrap red
        "Root Canal": "#fd7e14",  # Bootstrap orange
        "Extraction": "#6c757d",  # Bootstrap gray
        "Decay": "#8b4513",  # Darker brown
        "Missing": "#e9ecef",  # Light gray
    }

    # Get color with fallback to ensure valid color is always used
    fill_color = color_map.get(condition, "#e9ecef")

    # Determine text color based on background brightness
    text_color = "white" if condition != "Missing" else "black"

    svg_code = f"""
    <div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 1mm;">
        <svg width="50" height="50" style="border:2px solid #dee2e6;">
            <rect width="50" height="50" fill="{fill_color}" />
            <text 
                x="25" 
                y="30" 
                fill="{text_color}" 
                font-size="16" 
                font-weight="bold" 
                text-anchor="middle"
                dominant-baseline="middle"
            >{tooth_number}</text>
        </svg>
    </div>
    """
    return svg_code


def main():
    # Custom CSS for improved styling
    st.markdown("""
        <style>
        .tooth-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin: 0;
            padding: 0;
        }
        .stSelectbox {
            margin: 1mm auto !important;
            font-size: 14px !important;
            text-align: center !important;
        }
        .element-container {
            margin: 0 !important;
            padding: 0 !important;
        }
        .row-widget {
            margin: 0 !important;
            padding: 0 !important;
        }
        .stSelectbox > div > div {
            min-height: 35px !important;
            height: 35px !important;
            line-height: 1.5 !important;
        }
        .dental-chart-grid {
            display: grid;
            grid-template-columns: repeat(8, 1fr);
            gap: 1mm;
            margin: 1mm 0;
        }
        div[data-baseweb="select"] > div {
            font-size: 14px !important;
        }
        .dental-chart-container {
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        }
        .stSelectbox select {
            background-color: white !important;
        }
        .stSelectbox option {
            background-color: white;
            color: black;
        }
        .stSelectbox select:focus option:checked {
            background: #e6e6e6 linear-gradient(0deg, #e6e6e6 0%, #e6e6e6 100%);
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("Dental Treatment Planner")

    if st.session_state.get('doctor_email') is None:
        st.error("Doctor Authentication Required: Please log in to access patient management")
        return

    st.header("Patient Registration")

    column_first, column_second = st.columns(2)
    with column_first:
        patient_fullname = st.text_input("Full Name", placeholder="Enter patient's full name")
        patient_age = st.number_input("Age", min_value=1, max_value=150, step=1)
    with column_second:
        patient_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        file_id = st.text_input("File ID", placeholder="Enter File ID")

    col1, col2 = st.columns(2)
    with col1:
        register_button = st.button("➕ Register Patient")
    with col2:
        search_button = st.button("🔍 Search Patient")

    if register_button:
        if patient_fullname and patient_age and file_id:
            existing_patient = fetch_patient(st.session_state.doctor_email, file_id)
            if existing_patient:
                st.error(f"Registration Error: File ID {file_id} already exists")
            else:
                patient_info = {
                    'name': patient_fullname,
                    'age': patient_age,
                    'gender': patient_gender,
                    'file_id': file_id,
                    'dental_chart': {},
                    'treatment_plan': []
                }
                store_patient(st.session_state.doctor_email, patient_info)
                st.session_state.patient_status = True
                st.session_state.patient_selected = patient_info
                st.session_state.treatment_record = []
                st.success(f"Registration Successful: Patient {patient_fullname} added")
        else:
            st.error("Registration Error: All fields are required")

    if search_button and file_id:
        patient_info = fetch_patient(st.session_state.doctor_email, file_id)
        if patient_info:
            st.success(f"Patient Found: {patient_info['name']}, Age: {patient_info['age']}")
            st.session_state.patient_status = True
            st.session_state.patient_selected = patient_info
            st.session_state.treatment_record = patient_info.get('treatment_plan', [])
        else:
            st.warning("Patient Lookup Failed: No records match this file ID")
            st.session_state.patient_status = False

    if st.session_state.patient_status:
        patient_info = st.session_state.patient_selected
        file_id = patient_info['file_id']

        st.divider()
        st.subheader(f"Active Patient: {patient_info['name']} (ID: {file_id})")

        with st.container(border=True):
            st.header("Dental Chart Assessment")
            dental_chart = patient_info.get('dental_chart', {})

            # Add color legend
            st.markdown("""
                <div style="display: flex; gap: 20px; margin-bottom: 15px; flex-wrap: wrap;">
                    <div style="display: flex; align-items: center;">
                        <div style="width: 20px; height: 20px; background: #28a745; margin-right: 5px;"></div>
                        <span>Healthy</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 20px; height: 20px; background: #dc3545; margin-right: 5px;"></div>
                        <span>Cavity</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 20px; height: 20px; background: #fd7e14; margin-right: 5px;"></div>
                        <span>Root Canal</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 20px; height: 20px; background: #6c757d; margin-right: 5px;"></div>
                        <span>Extraction</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 20px; height: 20px; background: #8b4513; margin-right: 5px;"></div>
                        <span>Decay</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 20px; height: 20px; background: #e9ecef; margin-right: 5px; border: 1px solid #dee2e6;"></div>
                        <span>Missing</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            teeth_map = dental_data['teeth_map'].copy()
            teeth_rows = dental_data['teeth_rows']
            health_conditions = dental_data['health_conditions']
            chart_changed = False

            for teeth_row in teeth_rows:
                columns = st.columns(8)
                for i, tooth_number in enumerate(teeth_row):
                    with columns[i]:
                        with st.container():
                            st.markdown('<div class="tooth-container">', unsafe_allow_html=True)

                            tooth_condition = dental_chart.get(tooth_number, "Healthy")
                            tooth_svg = create_tooth_svg(tooth_number, tooth_condition)
                            st.markdown(tooth_svg, unsafe_allow_html=True)

                            selected_condition = st.selectbox(
                                "",
                                health_conditions,
                                index=health_conditions.index(
                                    tooth_condition) if tooth_condition in health_conditions else 0,
                                key=f"tooth_{tooth_number}",
                                label_visibility="collapsed"
                            )

                            st.markdown('</div>', unsafe_allow_html=True)

                            if tooth_number not in dental_chart or dental_chart[tooth_number] != selected_condition:
                                dental_chart[tooth_number] = selected_condition
                                chart_changed = True

                            if selected_condition != "Healthy":
                                st.session_state.tooth_selected = tooth_number

            if chart_changed:
                doctor_reference = database.collection('doctors').document(st.session_state.doctor_email)
                patient_document = doctor_reference.collection('patients').document(file_id)
                patient_document.update({'dental_chart': dental_chart})
                st.success("Dental chart updated successfully!")

        if st.session_state.treatment_record:
            data_frame = pd.DataFrame(st.session_state.treatment_record)
            st.dataframe(data_frame, use_container_width=True)


if __name__ == "__main__":
    main()
    show_footer()
