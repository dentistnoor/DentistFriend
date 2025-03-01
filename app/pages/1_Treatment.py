import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from firebase_admin import firestore
from utils import generate_pdf






if 'patient_registered' not in st.session_state:
    st.session_state.patient_registered = False

if 'treatment_plan' not in st.session_state:
    st.session_state.treatment_plan = []

db = firestore.client()

def save_patient(doctor_email, patient_data):
    doctor_ref = db.collection('doctors').document(doctor_email)
    doctor_ref.collection('patients').document(patient_data["file_number"]).set(patient_data)

def get_patient(doctor_email, file_number):
    doctor_ref = db.collection('doctors').document(doctor_email)
    patient_ref = doctor_ref.collection('patients').document(file_number).get()
    if patient_ref.exists:
        return patient_ref.to_dict()
    return None

def update_patient_treatment(doctor_email, file_number, treatment_plan):
    doctor_ref = db.collection('doctors').document(doctor_email)
    patient_ref = doctor_ref.collection('patients').document(file_number)
    patient_ref.update({'treatment_plan': treatment_plan})

def main():
    st.title("Dental Treatment Plan Generator")

    if st.session_state.get('doctor_email') is None:
        st.error("You need to log in to register a patient.")
        return

    if not st.session_state.patient_registered:
        st.header("Patient Information")

        col1, col2 = st.columns(2)
        with col1:
            patient_name = st.text_input("Full Name", placeholder="Enter patient's full name")
            age = st.number_input("Age", min_value=1, max_value=150, step=1)
        with col2:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            file_number = st.text_input("File Number", placeholder="Enter File number")

        search_button = st.button("Search Patient")
        if search_button and file_number:
            patient_data = get_patient(st.session_state.doctor_email, file_number)
            if patient_data:
                st.success(f"Patient found: {patient_data['name']}, Age: {patient_data['age']}")
                st.session_state.patient_registered = True
                st.session_state.selected_patient = patient_data
                st.session_state.treatment_plan = patient_data.get('treatment_plan', [])
            else:
                st.warning("No patient found with this file number.")

        if st.button("Register Patient"):
            if patient_name and age and file_number:
                patient_data = {
                    'name': patient_name,
                    'age': age,
                    'gender': gender,
                    'file_number': file_number,
                    'treatment_plan': []
                }
                save_patient(st.session_state.doctor_email, patient_data)
                st.session_state.patient_registered = True
                st.session_state.selected_patient = patient_data
                st.success(f"Patient {patient_name} registered successfully!")
            else:
                st.error("Please fill in all the fields to register the patient.")

    if st.session_state.patient_registered:
        patient_data = st.session_state.selected_patient
        file_number = patient_data['file_number']

        with st.container(border=True):
            st.header("Dental Charting")
            teeth = {
                '18': '', '17': '', '16': '', '15': '', '14': '', '13': '', '12': '', '11': '',
                '21': '', '22': '', '23': '', '24': '', '25': '', '26': '', '27': '', '28': '',
                '48': '', '47': '', '46': '', '45': '', '44': '', '43': '', '42': '', '41': '',
                '31': '', '32': '', '33': '', '34': '', '35': '', '36': '', '37': '', '38': ''
            }
            rows = [['18', '17', '16', '15', '14', '13', '12', '11'],
                    ['21', '22', '23', '24', '25', '26', '27', '28'],
                    ['48', '47', '46', '45', '44', '43', '42', '41'],
                    ['31', '32', '33', '34', '35', '36', '37', '38']]

            conditions = ["Healthy", "Decayed", "Filled", "Missing", "Fractured", "Impacted"]
            for row in rows:
                cols = st.columns(8)
                for i, tooth in enumerate(row):
                    with cols[i]:
                        selected_condition = st.selectbox(f"Tooth {tooth}", conditions, key=f"tooth_{tooth}")
                        if selected_condition != "Healthy":
                            st.session_state.selected_tooth = tooth

        with st.container(border=True):
            st.header("Treatment Plan")
            selected_tooth = st.session_state.get("selected_tooth", list(teeth.keys())[0])

            with st.form("treatment_form"):
                col1, col2 = st.columns(2)
                with col1:
                    tooth_number = st.selectbox("Tooth Number", list(teeth.keys()), index=list(teeth.keys()).index(selected_tooth))
                with col2:
                    procedure = st.selectbox("Procedure", [
                        "Filling", "Root Canal Treatment", "Crown", "Extraction", "Denture", "Implant", "Scaling"
                    ])
                cost_estimates = {
                    "Filling": 150, "Root Canal Treatment": 800, "Crown": 1000, "Extraction": 200,
                    "Denture": 1500, "Implant": 3000, "Scaling": 100
                }
                procedure_cost = cost_estimates.get(procedure, 0)

                if st.form_submit_button("Add to Treatment Plan"):
                    existing = [item for item in st.session_state.treatment_plan if item['Tooth'] == tooth_number and item['Procedure'] == procedure]
                    if not existing:
                        new_treatment = {
                            'Tooth': tooth_number, 'Procedure': procedure, 'Cost': procedure_cost, 'Status': 'Pending'
                        }
                        st.session_state.treatment_plan.append(new_treatment)

                        updated_treatment_plan = st.session_state.selected_patient.get('treatment_plan', [])
                        updated_treatment_plan.append(new_treatment)
                        update_patient_treatment(st.session_state.doctor_email, file_number, updated_treatment_plan)

                        st.success("Procedure added and saved to patient record!")
                    else:
                        st.error("This procedure already exists for the selected tooth")

        if st.session_state.treatment_plan:
            df = pd.DataFrame(st.session_state.treatment_plan)
            st.dataframe(df, use_container_width=True)

            st.subheader("Cost Estimation")
            total_cost = df['Cost'].sum()

            apply_discount = st.number_input("Apply Discount", min_value=0, step=1, format="%d")
            apply_vat = st.checkbox("Apply 15% VAT")

            vat_amount = total_cost * 0.15 if apply_vat else 0
            discount_amount = apply_discount
            discount_amount = min(discount_amount, total_cost)
            final_total = total_cost - discount_amount + vat_amount

            cost_summary = pd.DataFrame({
                "Total Cost": [f"SAR {total_cost:.2f}"],
                "Discount": [f"-SAR {discount_amount:.2f}"],
                "VAT (15%)": [f"+SAR {vat_amount:.2f}"],
                "Final Total": [f"SAR {final_total:.2f}"]
            })

            st.table(cost_summary)

            st.subheader("Progress Tracking")
            for index, row in df.iterrows():
                status = st.selectbox(
                    f"Status for {row['Procedure']} on Tooth {row['Tooth']}",
                    ["Pending", "In Progress", "Completed"],
                    key=f"status_{index}_{row['Tooth']}_{row['Procedure']}"
                )
                df.at[index, 'Status'] = status

            st.subheader("Treatment Timeline")
            start_date = st.date_input("Start Date", datetime.today())
            for index, row in df.iterrows():
                duration = st.number_input(
                    f"Duration (days) for {row['Procedure']} on Tooth {row['Tooth']}",
                    min_value=1,
                    value=7,
                    key=f"duration_{index}_{row['Tooth']}_{row['Procedure']}"
                )
                df.at[index, 'End Date'] = start_date + timedelta(days=duration)

            st.table(df[['Tooth', 'Procedure', 'Status', 'End Date']])

            st.subheader("Upload X-Ray Image")
            xray_image = st.file_uploader("Upload X-Ray Image", type=["jpg", "png", "jpeg"])
            xray_image_path = None
            if xray_image:
                xray_image_path = f"xray_{patient_name or 'unknown'}.png"
                with open(xray_image_path, "wb") as f:
                    f.write(xray_image.getbuffer())
                st.image(xray_image, caption="Uploaded X-Ray Image", use_column_width=True)

            if st.button("Generate PDF Report"):
                try:
                    pdf_path = generate_pdf(patient_name or "Unknown Patient", df.to_dict('records'), total_cost, xray_image_path)
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"{patient_name or 'unknown'}_treatment_plan.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"An error occurred while generating the PDF: {e}")
                finally:
                    if xray_image_path and os.path.exists(xray_image_path):
                        os.remove(xray_image_path)
        else:
            st.info("No procedures added to the treatment plan yet")

if __name__ == "__main__":
    main()
