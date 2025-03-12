import json
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from firebase_admin import firestore
from utils import format_date, show_footer, generate_pdf, render_chart

# Initialize session state variables to track patient status and treatment records
if "patient_status" not in st.session_state:
    st.session_state.patient_status = False

if "treatment_record" not in st.session_state:
    st.session_state.treatment_record = []

# Load dental chart data from config file (teeth map, teeth rows, health conditions)
with open("app/data.json", "r") as file:
    dental_data = json.load(file)

# Initialize Firestore database client
database = firestore.client()


def store_patient(doctor_email, patient_info):
    """Store new patient information in Firestore under the doctor's collection"""
    try:
        doctor_reference = database.collection("doctors").document(doctor_email)
        doctor_reference.collection("patients").document(patient_info["file_id"]).set(patient_info)
        return True
    except Exception as e:
        st.error(f"Database Error: Failed to store patient - {str(e)}")
        return False


def fetch_patient(doctor_email, file_id):
    """Retrieve patient data from Firestore using doctor email and patient file ID"""
    try:
        doctor_reference = database.collection("doctors").document(doctor_email)
        patient_document = doctor_reference.collection("patients").document(file_id).get()
        if patient_document.exists:
            return patient_document.to_dict()
        return None
    except Exception as e:
        st.error(f"Database Error: Failed to fetch patient - {str(e)}")
        return None


def modify_patient(doctor_email, file_id, patient_data):
    """Update basic patient information in Firestore"""
    try:
        doctor_reference = database.collection("doctors").document(doctor_email)
        patient_document = doctor_reference.collection("patients").document(file_id)
        patient_document.update(patient_data)
        return True
    except Exception as e:
        st.error(f"Database Error: Failed to modify patient - {str(e)}")
        return False


def modify_treatment(doctor_email, file_id, treatment_record):
    """Update patient's treatment plan in Firestore"""
    try:
        doctor_reference = database.collection("doctors").document(doctor_email)
        patient_document = doctor_reference.collection("patients").document(file_id)
        patient_document.update({"treatment_plan": treatment_record})
        return True
    except Exception as e:
        st.error(f"Database Error: Failed to modify treatment - {str(e)}")
        return False


def load_settings(doctor_email):
    """Load doctor settings from Firestore including treatment procedures and prices"""
    try:
        doctor_ref = database.collection("doctors").document(doctor_email)
        settings_doc = doctor_ref.collection("settings").document("config").get()

        # If settings exist, return them
        if settings_doc.exists:
            return settings_doc.to_dict()
        else:
            # Return default settings if none exist
            return {
                "treatment_procedures": ["Cleaning"],
                "price_estimates": {"Cleaning": 100}
            }
    except Exception as e:
        st.error(f"Failed to load doctor settings: {str(e)}")


def main():
    st.title("Dental Treatment Planner")

    # Authentication check - prevent access without login
    if st.session_state.get("doctor_email") is None:
        st.error("Doctor Authentication Required: Please log in to access patient management")
        return

    # Load doctor-specific settings from Firestore
    doctor_email = st.session_state.get("doctor_email")
    doctor_settings = load_settings(doctor_email)

    # Merge doctor's treatment procedures and price estimates with dental_data
    dental_data["treatment_procedures"] = doctor_settings.get("treatment_procedures", ["Cleaning"])
    dental_data["price_estimates"] = doctor_settings.get("price_estimates", {"Cleaning": 100})

    st.header("Patient Registration")

    # Patient registration form - split into two columns for better layout
    column_first, column_second = st.columns(2)
    with column_first:
        patient_fullname = st.text_input("Full Name", placeholder="Enter patient's full name", key="reg_fullname")
        patient_age = st.number_input("Age", min_value=1, max_value=150, step=1, key="reg_age")
    with column_second:
        patient_gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="reg_gender")
        file_id = st.text_input("File ID", placeholder="Enter File ID", key="reg_file_id")

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
                    "name": patient_fullname,
                    "age": patient_age,
                    "gender": patient_gender,
                    "file_id": file_id,
                    "dental_chart": {},
                    "treatment_plan": []
                }
                if store_patient(st.session_state.doctor_email, patient_info):
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
            st.session_state.treatment_record = patient_info.get("treatment_plan", [])

            # Initialize tooth condition session state variables for existing dental chart
            dental_chart = patient_info.get("dental_chart", {})
            for tooth, condition in dental_chart.items():
                st.session_state[f"tooth_condition_{tooth}"] = condition
        else:
            st.warning("Patient Lookup Failed: No records match this file ID")
            st.session_state.patient_status = False

    # Display patient details and treatment options when a patient is active
    if st.session_state.patient_status:
        patient_info = st.session_state.patient_selected
        file_id = patient_info["file_id"]

        st.divider()
        st.subheader(f"Active Patient: {patient_info['name']} (ID: {file_id})")

        # Option to clear patient data or edit patient record
        if st.session_state.patient_status:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Clear Current Patient", use_container_width=True, key="clear_patient"):
                    # Reset patient-related session state variables
                    st.session_state.patient_status = False
                    st.session_state.treatment_record = []

                    # Clear tooth condition session state variables
                    for key in list(st.session_state.keys()):
                        if key.startswith("tooth_condition_"):
                            del st.session_state[key]

                    st.rerun()  # Refresh the app
            with col2:
                if st.button("✏️ Edit Patient Record", use_container_width=True, key="edit_patient_btn"):
                    st.session_state.edit_patient = True

        # Patient edit form - displays when edit button is clicked
        if st.session_state.get("edit_patient", False):
            with st.container(border=True):
                st.subheader("Edit Patient Information")

                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    updated_name = st.text_input("Full Name", value=patient_info.get("name", ""), key="edit_name")
                    updated_age = st.number_input("Age", value=patient_info.get("age", 1), min_value=1, max_value=150, step=1, key="edit_age")
                with edit_col2:
                    gender_options = ["Male", "Female", "Other"]
                    current_gender_index = gender_options.index(patient_info.get("gender", "Male")) if patient_info.get("gender") in gender_options else 0
                    updated_gender = st.selectbox("Gender", gender_options, index=current_gender_index, key="edit_gender")
                    st.text_input("File ID (cannot be changed)", value=file_id, disabled=True, key="edit_file_id")

                edit_buttons_col1, edit_buttons_col2 = st.columns(2)
                with edit_buttons_col1:
                    if st.button("✔️ Save", use_container_width=True, key="save_patient_changes"):
                        if updated_name and updated_age:
                            # Collect updated patient information
                            updated_info = {
                                "name": updated_name,
                                "age": updated_age,
                                "gender": updated_gender
                            }
                            if modify_patient(st.session_state.doctor_email, file_id, updated_info):
                                patient_info.update(updated_info)
                                st.session_state.patient_selected = patient_info
                                st.session_state.edit_patient = False
                                st.success("Patient information updated successfully!")
                                st.rerun()
                        else:
                            st.error("Update Error: Name and age cannot be empty")
                with edit_buttons_col2:
                    if st.button("❌ Cancel", use_container_width=True, key="cancel_edit_patient"):
                        st.session_state.edit_patient = False
                        st.rerun()

        # Dental chart assessment tool - visual representation of patient's dental health
        dental_chart = patient_info.get("dental_chart", {})
        updated_chart, chart_changed = render_chart(dental_data, dental_chart)

        # Save dental chart changes to database if changes were made
        if chart_changed:
            try:
                doctor_reference = database.collection("doctors").document(st.session_state.doctor_email)
                patient_document = doctor_reference.collection("patients").document(file_id)
                patient_document.update({"dental_chart": updated_chart})
                st.session_state.patient_selected["dental_chart"] = updated_chart
                st.success("Dental chart updated successfully!")
            except Exception as e:
                st.error(f"Chart Update Error: {str(e)}")

        # Treatment plan creation section - allows adding treatments for specific teeth
        with st.container(border=True):
            st.header("Treatment Plan")
            # Default to previously selected tooth or first tooth in map
            teeth_map = dental_data["teeth_map"].copy()
            tooth_selected = st.session_state.get("tooth_selected", list(teeth_map.keys())[0])

            # Form to add new treatment procedures
            with st.form("treatment_form"):
                column_first, column_second = st.columns(2)
                with column_first:
                    # Pre-select the tooth that was marked as unhealthy (if any)
                    tooth_identifier = st.selectbox("Tooth Number", list(teeth_map.keys()), 
                                                   index=list(teeth_map.keys()).index(tooth_selected), key="add_tooth")
                with column_second:
                    treatment_procedure = st.selectbox("Procedure", dental_data["treatment_procedures"], key="add_procedure")

                # Get cost from price estimates in doctor settings
                price_estimates = dental_data["price_estimates"]
                procedure_price = price_estimates.get(treatment_procedure, 0)

                submit_button = st.form_submit_button("➕ Add Procedure", use_container_width=True)
                if submit_button:
                    # Check for duplicate procedures - prevent adding same procedure to same tooth
                    existing_procedures = [item for item in st.session_state.treatment_record 
                                          if item["Tooth"] == tooth_identifier and item["Procedure"] == treatment_procedure]
                    if not existing_procedures:
                        # Calculate default dates for treatment timeline
                        today = datetime.today()
                        today_str = today.strftime("%Y-%m-%d")
                        end_date = today + timedelta(days=7)
                        end_date_str = end_date.strftime("%Y-%m-%d")

                        # Create new treatment record with default schedule
                        new_procedure = {
                            "Tooth": tooth_identifier,
                            "Procedure": treatment_procedure,
                            "Cost": procedure_price,
                            "Status": "Pending",
                            "Duration": 7,
                            "Start Date": today_str,
                            "End Date": end_date_str
                        }
                        st.session_state.treatment_record.append(new_procedure)
                        # Update treatment plan in database
                        if modify_treatment(st.session_state.doctor_email, file_id, st.session_state.treatment_record):
                            st.success("Procedure added to treatment plan")
                    else:
                        st.error("This procedure already exists for the selected tooth")

        # Treatment management section - allows editing and updating treatment procedures
        if st.session_state.treatment_record:
            with st.container(border=True):
                st.subheader("Treatment Management")

                df = pd.DataFrame(st.session_state.treatment_record)

                # Form for managing treatment procedures - status, duration, etc.
                with st.form("treatment_management"):
                    st.write("**Treatment Procedures**")

                    # Create header row for the treatment management table
                    col_headers = st.columns([2, 3, 2, 3, 2, 1])
                    with col_headers[0]:
                        st.write("**Tooth**")
                    with col_headers[1]:
                        st.write("**Procedure**")
                    with col_headers[2]:
                        st.write("**Status**")
                    with col_headers[3]:
                        st.write("**Start Date**")
                    with col_headers[4]:
                        st.write("**Duration (days)**")
                    with col_headers[5]:
                        st.write("**Action**")

                    procedures_to_delete = []

                    # Generate row controls for each procedure in the treatment plan
                    for i, row in df.iterrows():
                        tooth = row["Tooth"]
                        procedure = row["Procedure"]
                        key_id = f"{tooth}_{procedure}_{i}"

                        cols = st.columns([2, 3, 2, 3, 2, 1])

                        with cols[0]:
                            st.write(f"Tooth {tooth}")

                        with cols[1]:
                            # Procedure selector with current procedure pre-selected
                            new_procedure = st.selectbox(
                                "Procedure",
                                dental_data["treatment_procedures"],
                                index=dental_data["treatment_procedures"].index(procedure) 
                                    if procedure in dental_data["treatment_procedures"] else 0,
                                key=f"procedure_{key_id}",
                                label_visibility="collapsed"
                            )

                        with cols[2]:
                            # Status selector with current status pre-selected
                            new_status = st.selectbox(
                                "Status",
                                ["Pending", "In Progress", "Completed"],
                                index=["Pending", "In Progress", "Completed"].index(row["Status"]),
                                key=f"status_{key_id}",
                                label_visibility="collapsed"
                            )

                        with cols[3]:
                            # Individual start date for each procedure
                            # Parse the existing date or use today's date as default
                            default_date = datetime.today()
                            if "Start Date" in row and row["Start Date"]:
                                try:
                                    default_date = datetime.strptime(row["Start Date"], "%Y-%m-%d")
                                except (ValueError, TypeError):
                                    pass  # Use today's date if parsing fails

                            procedure_start_date = st.date_input(
                                "Start Date",
                                value=default_date,
                                key=f"start_date_{key_id}",
                                label_visibility="collapsed"
                            )

                        with cols[4]:
                            # Duration control for treatment length
                            new_duration = st.number_input(
                                "Duration",
                                min_value=1,
                                value=int(row.get("Duration", 7)),
                                step=1,
                                key=f"duration_{key_id}",
                                label_visibility="collapsed"
                            )

                        with cols[5]:
                            # Action selector - keep (✓) or delete (✗) the procedure
                            delete_item = st.selectbox(
                                "Action",
                                ["✓", "✗"],
                                key=f"delete_{key_id}",
                                label_visibility="collapsed"
                            )
                            if delete_item == "✗":
                                procedures_to_delete.append(i)

                    submit_management = st.form_submit_button("📋 Update Treatment Management", use_container_width=True)

                    # Process form submission - update all treatments
                    if submit_management:
                        updated_treatments = []

                        # Create updated treatment list excluding deleted procedures
                        for i, item in enumerate(st.session_state.treatment_record):
                            if i in procedures_to_delete:
                                continue

                            tooth = item["Tooth"]
                            procedure = item["Procedure"]
                            key_id = f"{tooth}_{procedure}_{i}"

                            # Get updated procedure from form inputs
                            new_procedure = st.session_state[f"procedure_{key_id}"]

                            # Update price if procedure changed
                            price_estimates = dental_data["price_estimates"]
                            procedure_price = price_estimates.get(new_procedure, item["Cost"]) if new_procedure != procedure else item["Cost"]

                            # Get individual start date for this procedure
                            start_date = st.session_state[f"start_date_{key_id}"]
                            start_date_str = start_date.strftime("%Y-%m-%d")

                            # Create updated procedure record
                            updated_procedure = {
                                "Tooth": tooth,
                                "Procedure": new_procedure,
                                "Cost": procedure_price,
                                "Status": st.session_state[f"status_{key_id}"],
                                "Duration": st.session_state[f"duration_{key_id}"],
                                "Start Date": start_date_str
                            }

                            # Calculate end date based on duration
                            start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
                            end_date = start_date_obj + timedelta(days=updated_procedure["Duration"])
                            updated_procedure["End Date"] = end_date.strftime("%Y-%m-%d")

                            updated_treatments.append(updated_procedure)

                        # Save updated treatments to session state and database
                        st.session_state.treatment_record = updated_treatments

                        if modify_treatment(st.session_state.doctor_email, file_id, updated_treatments):
                            st.rerun()

                # Display treatment schedule overview as a table
                st.write("**Treatment Schedule Overview**")
                schedule_df = pd.DataFrame(st.session_state.treatment_record)

                if not schedule_df.empty:
                    # Format dates for better readability
                    if "Start Date" in schedule_df.columns:
                        schedule_df["Start Date"] = schedule_df["Start Date"].apply(format_date)
                    if "End Date" in schedule_df.columns:
                        schedule_df["End Date"] = schedule_df["End Date"].apply(format_date)

                    # Ensure all required columns exist, fill with defaults if missing
                    display_cols = ["Tooth", "Procedure", "Status", "Start Date", "End Date"]
                    for col in display_cols:
                        if col not in schedule_df.columns:
                            schedule_df[col] = "N/A"

                    st.table(schedule_df[display_cols])

            # Dental imaging section - allows uploading X-ray images
            st.subheader("Dental Imaging")
            st.info("NOTE: Uploading multiple images is not supported yet", icon="📢")

            # X-ray image upload functionality
            image_file = st.file_uploader("Upload X-Ray Image", type=["jpg", "png", "jpeg"], key="xray_upload")
            image_path = None
            if image_file:
                try:
                    file_extension = image_file.name.split(".")[-1].lower()
                    image_path = f"xray_{patient_info['name'] or 'unknown'}.{file_extension}"
                    with open(image_path, "wb") as file_handler:
                        file_handler.write(image_file.getbuffer())
                    # st.image(image_file, caption="Uploaded X-Ray Image", use_container_width=True)
                except Exception as e:
                    st.error(f"Image Upload Error: {str(e)}")

            # Cost summary calculation
            total_price = sum(item["Cost"] for item in st.session_state.treatment_record)
            discount_calculation = 0
            tax_calculation = 0
            final_calculation = total_price

            # Cost summary display
            st.header("Cost Summary")
            with st.container(border=True):
                if st.session_state.treatment_record:
                    cost_df = pd.DataFrame(st.session_state.treatment_record)

                    st.write("**Procedure Cost Details:**")
                    procedure_details = cost_df[["Tooth", "Procedure", "Cost"]]

                    # Format cost as string with 2 decimal places
                    procedure_details = procedure_details.copy()
                    procedure_details["Cost"] = procedure_details["Cost"].astype(float).apply(lambda x: f"{x:.2f}")

                    st.table(procedure_details)

                    # Calculate total price and apply discounts/taxes
                    total_price = sum(item["Cost"] for item in st.session_state.treatment_record)
                    discount_amount = st.number_input("Discount Amount", min_value=0.0, step=1.0, 
                                                     format="%.2f", key="discount_amount")
                    tax_apply = st.checkbox("Apply VAT (15%)", key="tax_apply")

                    # Calculate final price with VAT and discount
                    tax_calculation = total_price * 0.15 if tax_apply else 0
                    discount_calculation = min(discount_amount, total_price)
                    final_calculation = total_price - discount_calculation + tax_calculation

                    # Display cost breakdown in table format
                    st.write("**Final Cost Summary:**")
                    cost_summary = {
                        "Description": ["Total Treatment Cost", "Discount", "VAT (15%)", "Final Total"],
                        "Amount": [
                            f"{total_price:.2f}",
                            f"-{discount_calculation:.2f}",
                            f"+{tax_calculation:.2f}",
                            f"{final_calculation:.2f}"
                        ]
                    }

                    summary_df = pd.DataFrame(cost_summary)
                    st.table(summary_df)
                else:
                    st.info("No procedures have been added to the treatment plan yet")

            # PDF report generation - creates and downloads treatment plan as PDF
            if st.button("📄 Generate Treatment Report", use_container_width=True, key="generate_report"):
                if not st.session_state.treatment_record:
                    st.warning("Cannot generate report: No treatment procedures have been added")
                else:
                    try:
                        # Generate PDF report with treatment details and cost summary
                        pdf_path = generate_pdf(
                            st.session_state.get("doctor_name", "Doctor"),
                            patient_info["name"] or "Unknown Patient",
                            st.session_state.treatment_record,
                            discount_calculation,
                            tax_calculation,
                            total_price,
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
                            mime="application/pdf",
                            key="download_report"
                        )

                        st.success(f"Treatment report generated successfully: {file_name}")
                    except Exception as error_message:
                        st.error(f"Report Generation Error: {error_message}")
        else:
            st.info("No procedures have been added to the treatment plan yet")


main()
show_footer()
