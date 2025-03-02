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

database = firestore.client()

def store_patient(doctor_email, patient_info):
    doctor_reference = database.collection('doctors').document(doctor_email)
    doctor_reference.collection('patients').document(patient_info["file_id"]).set(patient_info)

def fetch_patient(doctor_email, file_id):
    doctor_reference = database.collection('doctors').document(doctor_email)
    patient_document = doctor_reference.collection('patients').document(file_id).get()
    if patient_document.exists:
        return patient_document.to_dict()
    return None

def modify_treatment(doctor_email, file_id, treatment_record):
    doctor_reference = database.collection('doctors').document(doctor_email)
    patient_document = doctor_reference.collection('patients').document(file_id)
    patient_document.update({'treatment_plan': treatment_record})

def main():
    st.title("Dental Treatment Plan Generator")

    if st.session_state.get('doctor_email') is None:
        st.error("Doctor Authentication Required: Please log in to access patient management")
        return

    st.header("Patient Registration Form")

    column_first, column_second = st.columns(2)
    with column_first:
        patient_fullname = st.text_input("Full Name", placeholder="Enter patient's full name")
        patient_age = st.number_input("Age", min_value=1, max_value=150, step=1)
    with column_second:
        patient_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        file_id = st.text_input("File ID", placeholder="Enter File ID")

    col1, col2 = st.columns(2)
    with col1:
        search_button = st.button("Search Patient", key="search_patient_btn")
    with col2:
        register_button = st.button("Register Patient", key="register_patient_btn")

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

    if register_button:
        if patient_fullname and patient_age and file_id:
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
            st.success(f"Registration Successful: Patient {patient_fullname} added to database")
        else:
            st.error("Registration Error: All fields are required to complete registration")
            st.session_state.patient_status = False

    if st.session_state.patient_status:
        patient_info = st.session_state.patient_selected
        file_id = patient_info['file_id']

        st.markdown("---")
        st.subheader(f"Active Patient: {patient_info['name']} (ID: {file_id})")

        with st.container(border=True):
            st.header("Dental Chart Assessment")

            dental_chart = patient_info.get('dental_chart', {})
            teeth_map = {
                '18': '', '17': '', '16': '', '15': '', '14': '', '13': '', '12': '', '11': '',
                '21': '', '22': '', '23': '', '24': '', '25': '', '26': '', '27': '', '28': '',
                '48': '', '47': '', '46': '', '45': '', '44': '', '43': '', '42': '', '41': '',
                '31': '', '32': '', '33': '', '34': '', '35': '', '36': '', '37': '', '38': ''
            }

            for tooth in teeth_map:
                if tooth in dental_chart:
                    teeth_map[tooth] = dental_chart[tooth]

            teeth_rows = [['18', '17', '16', '15', '14', '13', '12', '11'],
                    ['21', '22', '23', '24', '25', '26', '27', '28'],
                    ['48', '47', '46', '45', '44', '43', '42', '41'],
                    ['31', '32', '33', '34', '35', '36', '37', '38']]

            health_conditions = ["Healthy", "Decayed", "Filled", "Missing", "Fractured", "Impacted"]

            chart_changed = False
            for teeth_row in teeth_rows:
                column_array = st.columns(8)
                for i, tooth_number in enumerate(teeth_row):
                    with column_array[i]:
                        default_index = 0
                        if tooth_number in dental_chart:
                            try:
                                default_index = health_conditions.index(dental_chart[tooth_number])
                            except ValueError:
                                default_index = 0

                        selected_condition = st.selectbox(
                            f"Tooth {tooth_number}",
                            health_conditions,
                            index=default_index,
                            key=f"tooth_{tooth_number}"
                        )

                        if tooth_number not in dental_chart or dental_chart[tooth_number] != selected_condition:
                            dental_chart[tooth_number] = selected_condition
                            chart_changed = True

                        if selected_condition != "Healthy":
                            st.session_state.tooth_selected = tooth_number

            if chart_changed:
                doctor_reference = database.collection('doctors').document(st.session_state.doctor_email)
                patient_document = doctor_reference.collection('patients').document(file_id)
                patient_document.update({'dental_chart': dental_chart})
                st.session_state.patient_selected['dental_chart'] = dental_chart
                st.success("Dental chart updated successfully!")

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

                submit_button = st.form_submit_button("Add Procedure")
                if submit_button:
                    existing_procedures = [item for item in st.session_state.treatment_record if item['Tooth'] == tooth_identifier and item['Procedure'] == treatment_procedure]
                    if not existing_procedures:
                        today_str = datetime.today().strftime('%Y-%m-%d')
                        end_date_str = (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')

                        new_procedure = {
                            'Tooth': tooth_identifier,
                            'Procedure': treatment_procedure,
                            'Cost': procedure_price,
                            'Status': 'Pending',
                            'Duration': 7,
                            'Start Date': today_str,
                            'End Date': end_date_str
                        }
                        st.session_state.treatment_record.append(new_procedure)
                        modify_treatment(st.session_state.doctor_email, file_id, st.session_state.treatment_record)
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

            with st.expander("Treatment Progress Monitoring", expanded=True):
                with st.form("update_treatment_progress"):
                    status_updates = {}

                    for index_position, row_data in data_frame.iterrows():
                        tooth = row_data['Tooth']
                        procedure = row_data['Procedure']
                        key_id = f"{tooth}_{procedure}"

                        status_value = st.selectbox(
                            f"Status for {procedure} on Tooth {tooth}",
                            ["Pending", "In Progress", "Completed"],
                            index=["Pending", "In Progress", "Completed"].index(row_data['Status']),
                            key=f"status_{key_id}"
                        )
                        status_updates[key_id] = status_value

                    submit_progress = st.form_submit_button("Update Treatment Progress")
                    if submit_progress:
                        updated_treatments = []
                        for item in st.session_state.treatment_record:
                            tooth = item['Tooth']
                            procedure = item['Procedure']
                            key_id = f"{tooth}_{procedure}"

                            item['Status'] = status_updates.get(key_id, item['Status'])
                            updated_treatments.append(item)

                        st.session_state.treatment_record = updated_treatments
                        modify_treatment(st.session_state.doctor_email, file_id, updated_treatments)
                        st.success("Treatment progress updated successfully!")

            with st.expander("Treatment Schedule Timeline", expanded=True):
                with st.form("update_treatment_timeline"):
                    today = datetime.today()

                    default_start_date = today
                    if not data_frame.empty and 'Start Date' in data_frame.columns:
                        try:
                            first_date = data_frame['Start Date'].iloc[0]
                            if isinstance(first_date, str):
                                default_start_date = datetime.strptime(first_date, '%Y-%m-%d')
                            else:
                                default_start_date = today
                        except (ValueError, TypeError):
                            default_start_date = today

                    start_date = st.date_input("Start Date", value=default_start_date)

                    duration_updates = {}
                    for index_position, row_data in data_frame.iterrows():
                        tooth = row_data['Tooth']
                        procedure = row_data['Procedure']
                        key_id = f"{tooth}_{procedure}"

                        default_duration = 7
                        if 'Duration' in row_data:
                            try:
                                default_duration = int(row_data['Duration'])
                            except (ValueError, TypeError):
                                default_duration = 7

                        duration_days = st.number_input(
                            f"Duration (days) for {procedure} on Tooth {tooth}",
                            min_value=1,
                            value=default_duration,
                            key=f"duration_{key_id}"
                        )
                        duration_updates[key_id] = duration_days

                    submit_timeline = st.form_submit_button("Update Schedule")
                    if submit_timeline:
                        updated_treatments = []
                        start_date_str = start_date.strftime('%Y-%m-%d')

                        for item in st.session_state.treatment_record:
                            tooth = item['Tooth']
                            procedure = item['Procedure']
                            key_id = f"{tooth}_{procedure}"

                            item['Duration'] = duration_updates.get(key_id, item.get('Duration', 7))

                            item['Start Date'] = start_date_str
                            end_date = start_date + timedelta(days=item['Duration'])
                            item['End Date'] = end_date.strftime('%Y-%m-%d')

                            updated_treatments.append(item)

                        st.session_state.treatment_record = updated_treatments
                        modify_treatment(st.session_state.doctor_email, file_id, updated_treatments)
                        st.success("Treatment schedule updated successfully!")

            if not data_frame.empty:
                st.subheader("Treatment Schedule Overview")
                display_df = data_frame.copy()

                required_columns = ['Tooth', 'Procedure', 'Status', 'Start Date', 'End Date']
                for col in required_columns:
                    if col not in display_df.columns:
                        if col == 'Start Date':
                            display_df[col] = datetime.today().strftime('%Y-%m-%d')
                        elif col == 'End Date':
                            display_df[col] = (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')
                        else:
                            display_df[col] = "N/A"

                st.table(display_df[required_columns])

            st.subheader("Dental Imaging Upload")
            image_file = st.file_uploader("Upload X-Ray Image", type=["jpg", "png", "jpeg"])
            image_path = None
            if image_file:
                image_path = f"xray_{patient_info['name'] or 'unknown'}.png"
                with open(image_path, "wb") as file_handler:
                    file_handler.write(image_file.getbuffer())
                st.image(image_file, caption="Uploaded X-Ray Image", use_column_width=True)

            if st.button("Generate Treatment Report"):
                try:
                    pdf_path = generate_pdf(patient_info['name'] or "Unknown Patient", data_frame.to_dict('records'), total_price, image_path)
                    with open(pdf_path, "rb") as file_handler:
                        pdf_content = file_handler.read()
                    st.download_button(
                        label="Download Treatment Report",
                        data=pdf_content,
                        file_name=f"{patient_info['name'] or 'unknown'}_treatment_plan.pdf",
                        mime="application/pdf"
                    )
                except Exception as error_message:
                    st.error(f"Report Generation Error: {error_message}")
                finally:
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)

        else:
            st.info("Empty Treatment Plan: No procedures have been added yet")

    if st.session_state.patient_status:
        if st.button("Clear Current Patient"):
            st.session_state.patient_status = False
            st.session_state.treatment_record = []
            st.rerun()

if __name__ == "__main__":
    main()
