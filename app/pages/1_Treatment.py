import json
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from firebase_admin import firestore
from utils import show_footer, generate_pdf

# Initialize session state variables to track patient status and treatment records
if 'patient_status' not in st.session_state:
    st.session_state.patient_status = False

if 'treatment_record' not in st.session_state:
    st.session_state.treatment_record = []

# Load dental procedures and pricing data from config file
with open('./app/data.json', 'r') as file:
    dental_data = json.load(file)

database = firestore.client()


def store_patient(doctor_email, patient_info):
    """Store new patient information in Firestore under the doctor's collection"""
    doctor_reference = database.collection('doctors').document(doctor_email)
    doctor_reference.collection('patients').document(patient_info["file_id"]).set(patient_info)


def fetch_patient(doctor_email, file_id):
    """Retrieve patient data from Firestore using doctor email and patient file ID"""
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


def main():
    st.title("Dental Treatment Planner")

    # Authentication check - prevent access without login
    if st.session_state.get('doctor_email') is None:
        st.error("Doctor Authentication Required: Please log in to access patient management")
        return

    st.header("Patient Registration")

    # Patient registration form - split into two columns for better layout
    column_first, column_second = st.columns(2)
    with column_first:
        patient_fullname = st.text_input("Full Name", placeholder="Enter patient's full name")
        patient_age = st.number_input("Age", min_value=1, max_value=150, step=1)
    with column_second:
        patient_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        file_id = st.text_input("File ID", placeholder="Enter File ID")

    # Action buttons layout
    col1, col2 = st.columns(2)
    with col1:
        register_button = st.button("➕ Register Patient", use_container_width=True)
    with col2:
        search_button = st.button("🔍 Search Patient", use_container_width=True)

    # Patient registration logic - validates and stores new patient data
    if register_button:
        if patient_fullname and patient_age and file_id:
            # Check if patient with same ID already exists to prevent duplicates
            existing_patient = fetch_patient(st.session_state.doctor_email, file_id)
            if existing_patient:
                st.error(f"Registration Error: File ID {file_id} already exists in the database")
                st.session_state.patient_status = False
            else:
                # Create new patient record with empty dental chart and treatment plan
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

    # Patient search functionality - uses file_id to find existing patient
    if search_button and file_id:
        patient_info = fetch_patient(st.session_state.doctor_email, file_id)
        if patient_info:
            st.success(f"Patient Found: {patient_info['name']}, Age: {patient_info['age']}")
            st.session_state.patient_status = True
            st.session_state.patient_selected = patient_info
            # Load existing treatment plan if available
            st.session_state.treatment_record = patient_info.get('treatment_plan', [])
        else:
            st.warning("Patient Lookup Failed: No records match this file ID")
            st.session_state.patient_status = False

    # Display patient details and treatment options when a patient is active
    if st.session_state.patient_status:
        patient_info = st.session_state.patient_selected
        file_id = patient_info['file_id']

        st.divider()
        st.subheader(f"Active Patient: {patient_info['name']} (ID: {file_id})")

        # Option to clear patient data or edit patient record
        if st.session_state.patient_status:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Clear Current Patient", use_container_width=True):
                    # Reset patient-related session state variables
                    st.session_state.patient_status = False
                    st.session_state.treatment_record = []
                    st.rerun()  # Refresh the app
            with col2:
                if st.button("✏️ Edit Patient Record", use_container_width=True):
                    st.write("Edit patient record functionality is currently under development")

        # Dental chart assessment tool - visual representation of patient's dental health
        with st.container(border=True):
            st.header("Dental Chart Assessment")

            # Get existing dental chart or initialize empty dict
            dental_chart = patient_info.get('dental_chart', {})
            teeth_map = dental_data['teeth_map'].copy()

            # Merge existing dental chart data with teeth map
            for tooth in teeth_map:
                if tooth in dental_chart:
                    teeth_map[tooth] = dental_chart[tooth]

            teeth_rows = dental_data['teeth_rows']
            health_conditions = dental_data['health_conditions']

            # Interactive dental chart with selectable conditions for each tooth
            # Creates a visual grid representation of all teeth
            chart_changed = False
            for teeth_row in teeth_rows:
                # Create columns for each tooth in the row (8 teeth per row for standard dental chart)
                column_array = st.columns(8)
                for i, tooth_number in enumerate(teeth_row):
                    with column_array[i]:
                        # Set default selection to current condition or "Healthy"
                        default_index = 0
                        if tooth_number in dental_chart:
                            try:
                                default_index = health_conditions.index(dental_chart[tooth_number])
                            except ValueError:
                                default_index = 0

                        # Dropdown selector for tooth condition
                        selected_condition = st.selectbox(
                            f"Tooth {tooth_number}",
                            health_conditions,
                            index=default_index,
                            key=f"tooth_{tooth_number}"
                        )

                        # Track changes to dental chart
                        if tooth_number not in dental_chart or dental_chart[tooth_number] != selected_condition:
                            dental_chart[tooth_number] = selected_condition
                            chart_changed = True

                        # Auto-select unhealthy teeth for potential treatment
                        if selected_condition != "Healthy":
                            st.session_state.tooth_selected = tooth_number

            # Save dental chart changes to database
            if chart_changed:
                doctor_reference = database.collection('doctors').document(st.session_state.doctor_email)
                patient_document = doctor_reference.collection('patients').document(file_id)
                patient_document.update({'dental_chart': dental_chart})
                st.session_state.patient_selected['dental_chart'] = dental_chart
                st.success("Dental chart updated successfully!")

        # Treatment plan creation section - allows adding treatments for specific teeth
        with st.container(border=True):
            st.header("Treatment Plan")
            # Default to previously selected tooth or first tooth in map
            tooth_selected = st.session_state.get("tooth_selected", list(teeth_map.keys())[0])

            # Form to add new treatment procedures
            with st.form("treatment_form"):
                column_first, column_second = st.columns(2)
                with column_first:
                    # Pre-select the tooth that was marked as unhealthy (if any)
                    tooth_identifier = st.selectbox("Tooth Number", list(teeth_map.keys()), index=list(teeth_map.keys()).index(tooth_selected))
                with column_second:
                    treatment_procedure = st.selectbox("Procedure", dental_data['treatment_procedures'])

                # Get cost from price estimates in data.json
                price_estimates = dental_data['price_estimates']
                procedure_price = price_estimates.get(treatment_procedure, 0)

                submit_button = st.form_submit_button("➕ Add Procedure")
                if submit_button:
                    # Check for duplicate procedures - prevent adding same procedure to same tooth
                    existing_procedures = [item for item in st.session_state.treatment_record if item['Tooth'] == tooth_identifier and item['Procedure'] == treatment_procedure]
                    if not existing_procedures:
                        # Calculate default dates for treatment timeline
                        today_str = datetime.today().strftime('%Y-%m-%d')
                        end_date_str = (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')

                        # Create new treatment record with default schedule
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
                        # Update treatment plan in database
                        modify_treatment(st.session_state.doctor_email, file_id, st.session_state.treatment_record)
                        st.success("Procedure added to treatment plan")
                    else:
                        st.error("This procedure already exists for the selected tooth")

        # Display treatment plan and cost summary if procedures exist
        if st.session_state.treatment_record:
            # Convert treatment record list to DataFrame for display
            data_frame = pd.DataFrame(st.session_state.treatment_record)
            st.dataframe(data_frame, use_container_width=True)

            # Cost calculation section with discount and tax options
            st.subheader("Cost Summary")
            total_price = data_frame['Cost'].sum()

            # Discount and VAT controls
            discount_amount = st.number_input("Discount Amount", min_value=0, step=1, format="%d")
            tax_apply = st.checkbox("Apply 15% VAT")

            # Calculate final price with VAT and discount
            tax_calculation = total_price * 0.15 if tax_apply else 0
            discount_calculation = discount_amount
            # Ensure discount can't exceed total price
            discount_calculation = min(discount_calculation, total_price)
            final_calculation = total_price - discount_calculation + tax_calculation

            # Display cost breakdown in table format
            cost_details = pd.DataFrame({
                "Total Cost": [f"SAR {total_price:.2f}"],
                "Discount": [f"-SAR {discount_calculation:.2f}"],
                "VAT (15%)": [f"+SAR {tax_calculation:.2f}"],
                "Final Total": [f"SAR {final_calculation:.2f}"]
            })

            st.table(cost_details)
            st.info("NOTE: SAR = Saudi Arabian Riyal")

            # Treatment status tracking system - allows updating progress for each procedure
            with st.expander("Treatment Progress", expanded=True):
                with st.form("update_treatment_progress"):
                    status_updates = {}

                    # Generate status controls for each procedure in the treatment plan
                    for index_position, row_data in data_frame.iterrows():
                        tooth = row_data['Tooth']
                        procedure = row_data['Procedure']
                        # Create unique key for each tooth-procedure combination
                        key_id = f"{tooth}_{procedure}"

                        # Status dropdown with current status pre-selected
                        status_value = st.selectbox(
                            f"Status for {procedure} on Tooth {tooth}",
                            ["Pending", "In Progress", "Completed"],
                            index=["Pending", "In Progress", "Completed"].index(row_data['Status']),
                            key=f"status_{key_id}"
                        )
                        status_updates[key_id] = status_value

                    submit_progress = st.form_submit_button("📋 Update Progress")
                    if submit_progress:
                        # Apply status updates to all treatments
                        updated_treatments = []
                        for item in st.session_state.treatment_record:
                            tooth = item['Tooth']
                            procedure = item['Procedure']
                            key_id = f"{tooth}_{procedure}"

                            # Update status based on user selection
                            item['Status'] = status_updates.get(key_id, item['Status'])
                            updated_treatments.append(item)

                        # Save updated statuses to session and database
                        st.session_state.treatment_record = updated_treatments
                        modify_treatment(st.session_state.doctor_email, file_id, updated_treatments)
                        st.success("Treatment progress updated")

            # Treatment scheduling interface - allows setting duration and start dates
            with st.expander("Treatment Schedule", expanded=True):
                with st.form("update_treatment_timeline"):
                    today = datetime.today()

                    # Determine default start date from existing data or use today
                    # Logic handles different data formats and potential errors
                    default_start_date = today
                    if not data_frame.empty and 'Start Date' in data_frame.columns:
                        try:
                            first_date = data_frame['Start Date'].iloc[0]
                            if isinstance(first_date, str):
                                # Convert string date to datetime object
                                default_start_date = datetime.strptime(first_date, '%Y-%m-%d')
                            else:
                                default_start_date = today
                        except (ValueError, TypeError):
                            # Fallback to today's date on parsing errors
                            default_start_date = today

                    start_date = st.date_input("Start Date", value=default_start_date)

                    # Adjust duration for each procedure individually
                    duration_updates = {}
                    for index_position, row_data in data_frame.iterrows():
                        tooth = row_data['Tooth']
                        procedure = row_data['Procedure']
                        key_id = f"{tooth}_{procedure}"

                        # Get current duration or use default 7-day period
                        default_duration = 7
                        if 'Duration' in row_data:
                            try:
                                default_duration = int(row_data['Duration'])
                            except (ValueError, TypeError):
                                default_duration = 7

                        # Allow setting duration for each treatment
                        duration_days = st.number_input(
                            f"Duration (days) for {procedure} on Tooth {tooth}",
                            min_value=1,
                            value=default_duration,
                            key=f"duration_{key_id}"
                        )
                        duration_updates[key_id] = duration_days

                    submit_timeline = st.form_submit_button("📅 Update Schedule")
                    if submit_timeline:
                        # Apply schedule updates to all treatments
                        updated_treatments = []
                        start_date_str = start_date.strftime('%Y-%m-%d')

                        for item in st.session_state.treatment_record:
                            tooth = item['Tooth']
                            procedure = item['Procedure']
                            key_id = f"{tooth}_{procedure}"

                            # Apply duration updates from form inputs
                            item['Duration'] = duration_updates.get(key_id, item.get('Duration', 7))

                            # Set start date and calculate end date based on duration
                            item['Start Date'] = start_date_str
                            end_date = start_date + timedelta(days=item['Duration'])
                            item['End Date'] = end_date.strftime('%Y-%m-%d')

                            updated_treatments.append(item)

                        # Save updated schedule to session and database
                        st.session_state.treatment_record = updated_treatments
                        modify_treatment(st.session_state.doctor_email, file_id, updated_treatments)
                        st.success("Treatment schedule updated")

            # Display treatment timeline overview as a table
            if not data_frame.empty:
                st.subheader("Treatment Schedule Overview")
                display_df = data_frame.copy()

                # Ensure all required columns exist, fill with defaults if missing
                required_columns = ['Tooth', 'Procedure', 'Status', 'Start Date', 'End Date']
                for col in required_columns:
                    if col not in display_df.columns:
                        # Set appropriate defaults for missing columns
                        if col == 'Start Date':
                            display_df[col] = datetime.today().strftime('%Y-%m-%d')
                        elif col == 'End Date':
                            display_df[col] = (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')
                        else:
                            display_df[col] = "N/A"

                # Show simplified view with just the key scheduling information
                st.table(display_df[required_columns])

            # Dental imaging and report generation section
            st.subheader("Dental Imaging")
            st.info("⚠️ Dental imaging and PDF report generation features are currently under development")

            # X-ray image upload functionality - saves uploaded image to file system
            image_file = st.file_uploader("Upload X-Ray Image", type=["jpg", "png", "jpeg"])
            image_path = None
            if image_file:
                # Save uploaded image with patient name in filename
                image_path = f"xray_{patient_info['name'] or 'unknown'}.png"
                with open(image_path, "wb") as file_handler:
                    file_handler.write(image_file.getbuffer())
                # Display the uploaded image in the app
                st.image(image_file, caption="Uploaded X-Ray Image", use_container_width=True)

            # PDF report generation - creates and downloads treatment plan as PDF
            if st.button("📄 Generate Treatment Report", use_container_width=True):
                try:
                    pdf_path = generate_pdf(
                        st.session_state["doctor_email"],
                        patient_info['name'] or "Unknown Patient",
                        data_frame.to_dict('records'),
                        discount_calculation,
                        tax_calculation,
                        final_calculation,
                        image_path
                    )

                    # Read generated PDF for download
                    with open(pdf_path, "rb") as file_handler:
                        pdf_content = file_handler.read()

                    # Create download button for the PDF file
                    file_name = f"{patient_info['name'] or 'unknown'}_treatment_plan.pdf"
                    st.download_button(
                        label="Download Treatment Report",
                        use_container_width=True,
                        data=pdf_content,
                        file_name=file_name,
                        mime="application/pdf"
                    )

                    st.success(f"Treatment report generated successfully: {file_name}")
                except Exception as error_message:
                    st.error(f"Report Generation Error: {error_message}")
                # finally:
                #     if os.path.exists(pdf_path):
                #         os.remove(pdf_path)

        else:
            st.info("No procedures have been added to the treatment plan yet")


main()
show_footer()
