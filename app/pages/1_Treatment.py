import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from firebase_admin import firestore
from utils import generate_pdf

if 'patient_status' not in st.session_state:
    st.session_state.patient_status = False

if 'treatment_record' not in st.session_state:
    st.session_state.treatment_record = []

data_base = firestore.client()

def store_patient(doctor_email, patient_info):
    doctor_reference = data_base.collection('doctors').document(doctor_email)
    doctor_reference.collection('patients').document(patient_info["file_id"]).set(patient_info)

def fetch_patient(doctor_email, file_id):
    doctor_reference = data_base.collection('doctors').document(doctor_email)
    patient_document = doctor_reference.collection('patients').document(file_id).get()
    if patient_document.exists:
        return patient_document.to_dict()
    return None

def modify_treatment(doctor_email, file_id, treatment_record):
    doctor_reference = data_base.collection('doctors').document(doctor_email)
    patient_document = doctor_reference.collection('patients').document(file_id)
    patient_document.update({'treatment_plan': treatment_record})

def main():
    st.title("Dental Treatment Plan Generator")

    if st.session_state.get('doctor_email') is None:
        st.error("Doctor Authentication Required: Please log in to access patient management")
        return

    if not st.session_state.patient_status:
        st.header("Patient Registration Form")

        column_first, column_second = st.columns(2)
        with column_first:
            patient_fullname = st.text_input("Full Name", placeholder="Enter patient's full name")
            patient_age = st.number_input("Age", min_value=1, max_value=150, step=1)
        with column_second:
            patient_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            file_id = st.text_input("File ID", placeholder="Enter File ID")

        search_button = st.button("Search Patient")
        if search_button and file_id:
            patient_info = fetch_patient(st.session_state.doctor_email, file_id)
            if patient_info:
                st.success(f"Patient Found: {patient_info['name']}, Age: {patient_info['age']}")
                st.session_state.patient_status = True
                st.session_state.patient_selected = patient_info
                st.session_state.treatment_record = patient_info.get('treatment_plan', [])
            else:
                st.warning("Patient Lookup Failed: No records match this file ID")

        if st.button("Register Patient"):
            if patient_fullname and patient_age and file_id:
                patient_info = {
                    'name': patient_fullname,
                    'age': patient_age,
                    'gender': patient_gender,
                    'file_id': file_id,
                    'treatment_plan': []
                }
                store_patient(st.session_state.doctor_email, patient_info)
                st.session_state.patient_status = True
                st.session_state.patient_selected = patient_info
                st.success(f"Registration Successful: Patient {patient_fullname} added to database")
            else:
                st.error("Registration Error: All fields are required to complete registration")

    if st.session_state.patient_status:
        patient_info = st.session_state.patient_selected
        file_id = patient_info['file_id']

        with st.container(border=True):
            st.header("Dental Chart Assessment")
            teeth_map = {
                '18': '', '17': '', '16': '', '15': '', '14': '', '13': '', '12': '', '11': '',
                '21': '', '22': '', '23': '', '24': '', '25': '', '26': '', '27': '', '28': '',
                '48': '', '47': '', '46': '', '45': '', '44': '', '43': '', '42': '', '41': '',
                '31': '', '32': '', '33': '', '34': '', '35': '', '36': '', '37': '', '38': ''
            }
            teeth_rows = [['18', '17', '16', '15', '14', '13', '12', '11'],
                    ['21', '22', '23', '24', '25', '26', '27', '28'],
                    ['48', '47', '46', '45', '44', '43', '42', '41'],
                    ['31', '32', '33', '34', '35', '36', '37', '38']]

            health_conditions = ["Healthy", "Decayed", "Filled", "Missing", "Fractured", "Impacted"]
            for teeth_row in teeth_rows:
                column_array = st.columns(8)
                for i, tooth_number in enumerate(teeth_row):
                    with column_array[i]:
                        selected_condition = st.selectbox(f"Tooth {tooth_number}", health_conditions, key=f"tooth_{tooth_number}")
                        if selected_condition != "Healthy":
                            st.session_state.tooth_selected = tooth_number

        with st.container(border=True):
            st.header("Treatment Plan Creation")
            tooth_selected = st.session_state.get("tooth_selected", list(teeth_map.keys())[0])

            with st.form("treatment_form"):
                column_first, column_second = st.columns(2)
                with column_first:
                    tooth_identifier = st.selectbox("Tooth Number", list(teeth_map.keys()), index=list(teeth_map.keys()).index(tooth_selected))
                with column_second:
                    treatment_procedure = st.selectbox("Procedure", [
                        "Filling", "Root Canal Treatment", "Crown", "Extraction", "Denture", "Implant", "Scaling"
                    ])
                price_estimates = {
                    "Filling": 150, "Root Canal Treatment": 800, "Crown": 1000, "Extraction": 200,
                    "Denture": 1500, "Implant": 3000, "Scaling": 100
                }
                procedure_price = price_estimates.get(treatment_procedure, 0)

                if st.form_submit_button("Add Procedure"):
                    existing_procedures = [item for item in st.session_state.treatment_record if item['Tooth'] == tooth_identifier and item['Procedure'] == treatment_procedure]
                    if not existing_procedures:
                        new_procedure = {
                            'Tooth': tooth_identifier, 'Procedure': treatment_procedure, 'Cost': procedure_price, 'Status': 'Pending'
                        }
                        st.session_state.treatment_record.append(new_procedure)

                        updated_procedures = st.session_state.patient_selected.get('treatment_plan', [])
                        updated_procedures.append(new_procedure)
                        modify_treatment(st.session_state.doctor_email, file_id, updated_procedures)

                        st.success("Procedure Addition Successful: Treatment added to patient record")
                    else:
                        st.error("Duplicate Treatment: This procedure already exists for the selected tooth")

        if st.session_state.treatment_record:
            data_frame = pd.DataFrame(st.session_state.treatment_record)
            st.dataframe(data_frame, use_container_width=True)

            st.subheader("Treatment Cost Calculation")
            total_price = data_frame['Cost'].sum()

            discount_amount = st.number_input("Discount Amount", min_value=0, step=1, format="%d")
            tax_apply = st.checkbox("Apply 15% VAT")

            tax_calculation = total_price * 0.15 if tax_apply else 0
            discount_calculation = discount_amount
            discount_calculation = min(discount_calculation, total_price)
            final_calculation = total_price - discount_calculation + tax_calculation

            cost_details = pd.DataFrame({
                "Total Cost": [f"SAR {total_price:.2f}"],
                "Discount": [f"-SAR {discount_calculation:.2f}"],
                "VAT (15%)": [f"+SAR {tax_calculation:.2f}"],
                "Final Total": [f"SAR {final_calculation:.2f}"]
            })

            st.table(cost_details)

            st.subheader("Treatment Progress Monitoring")
            for index_position, row_data in data_frame.iterrows():
                status_value = st.selectbox(
                    f"Status for {row_data['Procedure']} on Tooth {row_data['Tooth']}",
                    ["Pending", "In Progress", "Completed"],
                    key=f"status_{index_position}_{row_data['Tooth']}_{row_data['Procedure']}"
                )
                data_frame.at[index_position, 'Status'] = status_value

            st.subheader("Treatment Schedule Timeline")
            start_date = st.date_input("Start Date", datetime.today())
            for index_position, row_data in data_frame.iterrows():
                duration_days = st.number_input(
                    f"Duration (days) for {row_data['Procedure']} on Tooth {row_data['Tooth']}",
                    min_value=1,
                    value=7,
                    key=f"duration_{index_position}_{row_data['Tooth']}_{row_data['Procedure']}"
                )
                data_frame.at[index_position, 'End Date'] = start_date + timedelta(days=duration_days)

            st.table(data_frame[['Tooth', 'Procedure', 'Status', 'End Date']])

            st.subheader("Dental Imaging Upload")
            image_file = st.file_uploader("Upload X-Ray Image", type=["jpg", "png", "jpeg"])
            image_path = None
            if image_file:
                image_path = f"xray_{patient_fullname or 'unknown'}.png"
                with open(image_path, "wb") as file_handler:
                    file_handler.write(image_file.getbuffer())
                st.image(image_file, caption="Uploaded X-Ray Image", use_column_width=True)

            if st.button("Generate Treatment Report"):
                try:
                    pdf_path = generate_pdf(patient_fullname or "Unknown Patient", data_frame.to_dict('records'), total_price, image_path)
                    with open(pdf_path, "rb") as file_handler:
                        pdf_content = file_handler.read()
                    st.download_button(
                        label="Download Treatment Report",
                        data=pdf_content,
                        file_name=f"{patient_fullname or 'unknown'}_treatment_plan.pdf",
                        mime="application/pdf"
                    )
                except Exception as error_message:
                    st.error(f"Report Generation Error: {error_message}")
                finally:
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)
        else:
            st.info("Empty Treatment Plan: No procedures have been added yet")

if __name__ == "__main__":
    main()
