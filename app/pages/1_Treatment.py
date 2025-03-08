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
    """Update patient's treatment plan in Firestore"""
    doctor_reference = database.collection('doctors').document(doctor_email)
    patient_document = doctor_reference.collection('patients').document(file_id)
    patient_document.update({'treatment_plan': treatment_record})


def format_date(dt, fmt='%Y-%m-%d'):
    """Format dates consistently"""
    return dt.strftime(fmt)


def create_tooth_svg(tooth_number, condition):
    """Create SVG representation of a tooth with minimal styling"""
    color_map = {
        "Healthy": "green",
        "Cavity": "red",
        "Root Canal": "orange",
        "Extraction": "gray",
        "Decay": "brown",
        "Missing": "lightgray",
    }
    color = color_map.get(condition, "lightgray")
    svg_code = f"""
        <svg width="40" height="40" style="border:1px solid black; margin:0;">
            <rect width="40" height="40" fill="{color}" />
            <text x="20" y="25" fill="white" font-size="12" font-weight="bold" text-anchor="middle">{tooth_number}</text>
        </svg>
    """
    return svg_code


def main():
    st.title("Dental Treatment Planner")

    # Add custom styling
    st.markdown("""
        <style>
        .dropdown-container { margin-top: 1mm !important; }
        .custom-svg { margin-bottom: 1mm; display: flex; justify-content: center; }
        </style>
    """, unsafe_allow_html=True)

    # Authentication check
    if st.session_state.get('doctor_email') is None:
        st.error("Doctor Authentication Required: Please log in to access patient management")
        return

    st.header("Patient Registration")

    # Patient registration form
    with st.form("patient_registration_form"):
        col1, col2 = st.columns(2)
        with col1:
            patient_fullname = st.text_input("Full Name", placeholder="Enter patient's full name")
            patient_age = st.number_input("Age", min_value=1, max_value=150, step=1)
        with col2:
            patient_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            file_id = st.text_input("File ID", placeholder="Enter File ID")

        submit_registration = st.form_submit_button("Register Patient")

        if submit_registration and patient_fullname and patient_age and file_id:
            existing_patient = fetch_patient(st.session_state.doctor_email, file_id)
            if existing_patient:
                st.error(f"File ID {file_id} already exists in the database.")
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
                st.success(f"Patient {patient_fullname} has been registered.")

    # Patient search form
    with st.form("patient_search_form"):
        search_id = st.text_input("Search Patient by File ID")
        search_button = st.form_submit_button("Search Patient")
        if search_button and search_id:
            patient_info = fetch_patient(st.session_state.doctor_email, search_id)
            if patient_info:
                st.success(f"Patient found: {patient_info['name']}, Age {patient_info['age']}")
                st.session_state.patient_status = True
                st.session_state.patient_selected = patient_info
                st.session_state.treatment_record = patient_info.get('treatment_plan', [])
            else:
                st.warning("No patient found with the given ID.")

    # If a patient is selected
    if st.session_state.patient_status:
        patient_info = st.session_state.patient_selected
        file_id = patient_info['file_id']

        st.subheader(f"Active Patient: {patient_info['name']} (ID: {file_id})")

        # Dental Chart Assessment
        with st.container():
            st.header("Dental Chart Assessment")
            dental_chart = patient_info.get('dental_chart', {})
            teeth_map = dental_data['teeth_map']
            health_conditions = dental_data['health_conditions']
            teeth_rows = dental_data['teeth_rows']

            with st.form("dental_chart_form"):
                chart_updated = False
                # Display Teeth Chart with Dropdown
                for row in teeth_rows:
                    tooth_columns = st.columns(len(row))
                    for idx, tooth in enumerate(row):
                        with tooth_columns[idx]:
                            tooth_condition = dental_chart.get(tooth, "Healthy")
                            svg_code = create_tooth_svg(tooth, tooth_condition)
                            st.markdown(f'<div class="custom-svg">{svg_code}</div>', unsafe_allow_html=True)
                            selected_condition = st.selectbox(
                                "",
                                health_conditions,
                                index=health_conditions.index(tooth_condition),
                                key=f"dropdown_{tooth}"
                            )
                            if tooth not in dental_chart or dental_chart[tooth] != selected_condition:
                                dental_chart[tooth] = selected_condition
                                chart_updated = True

                submit_chart = st.form_submit_button("Update Dental Chart")
                if submit_chart and chart_updated:
                    doc_ref = database.collection('doctors').document(st.session_state.doctor_email)
                    patient_record = doc_ref.collection('patients').document(file_id)
                    patient_record.update({'dental_chart': dental_chart})
                    st.session_state.patient_selected['dental_chart'] = dental_chart
                    st.success("Dental chart updated successfully!")

        # Treatment plan creation section
        with st.container():
            st.header("Treatment Plan")
            tooth_selected = st.session_state.get("tooth_selected", list(teeth_map.keys())[0])

            with st.form("treatment_form"):
                col1, col2 = st.columns(2)
                with col1:
                    tooth_identifier = st.selectbox("Tooth Number", list(teeth_map.keys()),
                                                    index=list(teeth_map.keys()).index(tooth_selected))
                with col2:
                    treatment_procedure = st.selectbox("Procedure", dental_data['treatment_procedures'])

                col3, col4 = st.columns(2)
                with col3:
                    treatment_date = st.date_input("Treatment Date", value=datetime.today())
                with col4:
                    duration_days = st.number_input("Duration (days)", min_value=1, value=7)

                price_estimates = dental_data['price_estimates']
                procedure_price = price_estimates.get(treatment_procedure, 0)

                submit_treatment = st.form_submit_button("Add Treatment")
                if submit_treatment:
                    existing_procedures = [item for item in st.session_state.treatment_record
                                           if item['Tooth'] == tooth_identifier and
                                           item['Procedure'] == treatment_procedure]
                    if not existing_procedures:
                        end_date = treatment_date + timedelta(days=duration_days)
                        new_procedure = {
                            'Tooth': tooth_identifier,
                            'Procedure': treatment_procedure,
                            'Cost': procedure_price,
                            'Status': 'Pending',
                            'Duration': duration_days,
                            'Start Date': treatment_date.strftime('%Y-%m-%d'),
                            'End Date': end_date.strftime('%Y-%m-%d')
                        }
                        st.session_state.treatment_record.append(new_procedure)
                        modify_treatment(st.session_state.doctor_email, file_id, st.session_state.treatment_record)
                        st.success("Procedure added to treatment plan")
                    else:
                        st.error("This procedure already exists for the selected tooth")

        # Display treatment plan and progress tracking
        if st.session_state.treatment_record:
            data_frame = pd.DataFrame(st.session_state.treatment_record)

            # Treatment Progress and Schedule combined section
            with st.expander("Treatment Progress & Schedule", expanded=True):
                with st.form("update_treatment_progress"):
                    updated_treatments = []
                    for index, row in data_frame.iterrows():
                        st.markdown(f"**{row['Procedure']} - Tooth {row['Tooth']}**")
                        col1, col2 = st.columns(2)

                        with col1:
                            status = st.selectbox(
                                "Status",
                                ["Pending", "In Progress", "Completed"],
                                index=["Pending", "In Progress", "Completed"].index(row['Status']),
                                key=f"status_{index}"
                            )

                        with col2:
                            try:
                                current_date = datetime.strptime(row['Start Date'], '%Y-%m-%d')
                            except:
                                current_date = datetime.today()

                            new_date = st.date_input(
                                "Schedule Date",
                                value=current_date,
                                key=f"date_{index}"
                            )

                        duration = row.get('Duration', 7)
                        try:
                            duration = int(duration)
                        except:
                            duration = 7

                        updated_treatment = row.to_dict()
                        updated_treatment.update({
                            'Status': status,
                            'Start Date': new_date.strftime('%Y-%m-%d'),
                            'End Date': (new_date + timedelta(days=duration)).strftime('%Y-%m-%d')
                        })
                        updated_treatments.append(updated_treatment)

                        st.markdown("---")

                    submit_progress = st.form_submit_button("Update Progress")
                    if submit_progress:
                        st.session_state.treatment_record = updated_treatments
                        modify_treatment(st.session_state.doctor_email, file_id, updated_treatments)
                        st.success("Treatment progress updated successfully")

            # Display current treatment plan
            st.subheader("Current Treatment Plan")
            display_columns = ['Tooth', 'Procedure', 'Status', 'Start Date', 'End Date', 'Cost']
            st.dataframe(data_frame[display_columns], use_container_width=True)

            # Cost Summary Section
            st.subheader("Cost Summary")
            total_price = data_frame['Cost'].sum()

            with st.form("cost_calculation_form"):
                discount_amount = st.number_input("Discount Amount", min_value=0, step=1, format="%d")
                tax_apply = st.checkbox("Apply 15% VAT")

                calculate_cost = st.form_submit_button("Calculate Total")
                if calculate_cost:
                    tax_calculation = total_price * 0.15 if tax_apply else 0
                    discount_calculation = min(discount_amount, total_price)
                    final_calculation = total_price - discount_calculation + tax_calculation

                    cost_details = pd.DataFrame({
                        "Total Cost": [f"SAR {total_price:.2f}"],
                        "Discount": [f"-SAR {discount_calculation:.2f}"],
                        "VAT (15%)": [f"+SAR {tax_calculation:.2f}"],
                        "Final Total": [f"SAR {final_calculation:.2f}"]
                    })
                    st.table(cost_details)
                    st.info("NOTE: SAR = Saudi Arabian Riyal")

            # Report Generation Section
            if st.button("Generate Treatment Report"):
                try:
                    pdf_path = generate_pdf(
                        st.session_state["doctor_email"],
                        patient_info['name'],
                        data_frame.to_dict('records'),
                        discount_calculation,
                        tax_calculation,
                        final_calculation
                    )
                    with open(pdf_path, "rb") as file:
                        pdf_content = file.read()
                        st.download_button(
                            "Download Report",
                            pdf_content,
                            f"{patient_info['name']}_treatment_plan.pdf",
                            "application/pdf"
                        )
                except Exception as e:
                    st.error(f"Error generating report: {e}")

        # Patient Management Options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Patient"):
                st.session_state.patient_status = False
                st.session_state.treatment_record = []
                st.rerun()

        with col2:
            if st.button("Edit Patient"):
                with st.form("edit_patient_form"):
                    st.text_input("Name", value=patient_info['name'], key="edit_name")
                    st.number_input("Age", value=patient_info['age'], key="edit_age")
                    st.selectbox("Gender", ["Male", "Female", "Other"],
                                 index=["Male", "Female", "Other"].index(patient_info['gender']),
                                 key="edit_gender")

                    if st.form_submit_button("Update Patient"):
                        doc_ref = database.collection('doctors').document(st.session_state.doctor_email)
                        doc_ref.collection('patients').document(file_id).update({
                            'name': st.session_state.edit_name,
                            'age': st.session_state.edit_age,
                            'gender': st.session_state.edit_gender
                        })
                        st.success("Patient information updated")
                        st.rerun()

    show_footer()


if __name__ == "__main__":
    main()
