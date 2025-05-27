import os
import smtplib
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from firebase_admin import firestore
from dotenv import load_dotenv
from utils import format_date, show_footer

load_dotenv()

database = firestore.client()
doctor_email = st.session_state["doctor_email"] if "doctor_email" in st.session_state else None
stock_collection = database.collection("doctors").document(doctor_email).collection("stock") if doctor_email else None


def fetch_stock():
    """Fetch all inventory items from Firestore database"""
    stock_documents = stock_collection.stream()
    return {doc.id: doc.to_dict() for doc in stock_documents}


def store_stock(item_name, item_quantity, expiry_date, low_threshold=5, category="", location=""):
    """Store or update inventory item in Firestore database"""
    item_doc = stock_collection.document(item_name).get()
    if item_doc.exists:
        st.warning(f"Item '{item_name.split('_')[0]}' with the same expiry date already exists. Please edit the existing item instead.")
        return False

    stock_collection.document(item_name).set({
        "quantity": item_quantity,
        "expiry_date": expiry_date,
        "low_threshold": low_threshold,
        "category": category,
        "location": location
    }, merge=True)
    return True


def modify_stock(item_name, quantity_remove):
    """Decrease quantity or remove item from inventory"""
    item_reference = stock_collection.document(item_name)
    item_document = item_reference.get()

    if item_document.exists:
        item_data = item_document.to_dict()
        current_quantity = item_data["quantity"]

        # Update quantity if there are enough units
        item_reference.update({"quantity": current_quantity - quantity_remove})
        st.success(f"Quantity Updated: {quantity_remove} units of '{item_name}' removed")

        # Immediately update the inventory data in session state
        st.session_state.inventory_data = fetch_stock()


def import_inventory(file):
    """Process imported CSV or Excel file and add items to inventory"""
    try:
        # Determine file type and read accordingly
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return False, "Unsupported file format. Please upload a CSV or Excel file."

        # Check if the file has the required columns
        required_columns = ["Item", "Quantity", "Expiry Date", "Low Threshold"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"

        # Process each row and add to inventory
        success_count = 0
        error_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Extract values and convert to appropriate types
                item_name = str(row["Item"]).strip().lower()
                quantity = int(row["Quantity"])

                expiry_date = row["Expiry Date"]
                if isinstance(expiry_date, str):
                    try:
                        # Standard format "Month DD, YYYY"
                        expiry_date = datetime.strptime(expiry_date, "%B %d, %Y").strftime("%Y-%m-%d")
                    except ValueError:
                        errors.append(f"Row {index+1}: Invalid date format for {item_name}. Use 'Month DD, YYYY' format.")
                        error_count += 1
                        continue
                else:
                    # Convert pandas timestamp to string format
                    expiry_date = pd.Timestamp(expiry_date).strftime("%Y-%m-%d")

                # Get low threshold from the required column
                try:
                    low_threshold = int(row["Low Threshold"])
                    if low_threshold < 1:
                        errors.append(f"Row {index+1}: Low Threshold must be at least 1 for {item_name}")
                        error_count += 1
                        continue
                except (ValueError, TypeError):
                    errors.append(f"Row {index+1}: Invalid Low Threshold value for {item_name}")
                    error_count += 1
                    continue
                
                # Generate a unique item ID based on name and expiry date
                item_id = f"{item_name}_{expiry_date}"

                # Get optional columns if they exist
                category = str(row.get("Category", "")).strip() if "Category" in df.columns else ""
                location = str(row.get("Location", "")).strip() if "Location" in df.columns else ""
                
                # Add item to inventory
                success = store_stock(item_id, quantity, expiry_date, low_threshold, category, location)
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"Row {index+1}: Item '{item_name}' with expiry date {expiry_date} already exists")

            except Exception as e:
                error_count += 1
                errors.append(f"Row {index+1}: {str(e)}")

        # Return import results
        if error_count == 0:
            return True, f"Successfully imported {success_count} items."
        else:
            error_details = "\n".join(errors[:5])  # Show first 5 errors
            if len(errors) > 5:
                error_details += f"\n...and {len(errors) - 5} more errors."
            return success_count > 0, f"Imported {success_count} items with {error_count} errors.\n{error_details}"

    except Exception as e:
        return False, f"Error processing file: {str(e)}"


def send_alert(email, expiry_items, days_threshold):
    """Send email alert for items nearing expiry"""
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    current_date = datetime.now().strftime("%B %d, %Y")
    # Sort items by days left (most urgent first)
    expiry_items = sorted(expiry_items, key=lambda x: x['Days Left'])

    # Generate HTML table rows for items
    items_html = ""
    for item in expiry_items:
        if item['Days Left'] <= 7:
            row_color = "#FFCCCC"  # Light red for very urgent
        elif item['Days Left'] <= 14:
            row_color = "#FFEEBB"  # Light yellow for urgent
        else:
            row_color = "#FFFFFF"  # White for normal

        items_html += f"""
        <tr style="background-color: {row_color};">
            <td style="padding: 8px; border: 1px solid #ddd;">{item['Item']}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{item['Quantity']}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{item['Expiry Date']}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center; font-weight: bold;">{item['Days Left']}</td>
        </tr>
        """

    # Prepare HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dentist Friend - Dental Supply Alert</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #2c3e50; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">Dental Supply Alert</h1>
            <p style="margin: 5px 0 0 0; font-size: 14px;">{current_date}</p>
        </div>

        <div style="background-color: #f9f9f9; padding: 20px; border-left: 1px solid #ddd; border-right: 1px solid #ddd;">
            <p>Hello Dr. {st.session_state['doctor_name']},</p>
            <p>The following items in your inventory are <strong>expiring within {days_threshold} days</strong>:</p>

            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; background-color: white;">
                <thead>
                    <tr style="background-color: #3498db; color: white;">
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Item</th>
                        <th style="padding: 10px; text-align: center; border: 1px solid #ddd;">Quantity</th>
                        <th style="padding: 10px; text-align: center; border: 1px solid #ddd;">Expiry Date</th>
                        <th style="padding: 10px; text-align: center; border: 1px solid #ddd;">Days Left</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <div style="margin-top: 20px; padding: 15px; background-color: #e8f4f8; border-radius: 5px; border-left: 4px solid #3498db;">
                <p style="margin: 0; font-size: 15px;">Please review these items and take appropriate action to avoid supply shortages.</p>
            </div>
        </div>

        <div style="background-color: #ecf0f1; padding: 15px; font-size: 13px; text-align: center; border-radius: 0 0 5px 5px;">
            <p style="margin: 0;">This is an automated message from your Dentist Friend.</p>
            <p style="margin: 5px 0 0 0;">Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """

    # Create a MIME message
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Dental Supply Alert: Items Expiring Within {days_threshold} Days"
    message["From"] = ADMIN_EMAIL
    message["To"] = email

    # Create plain text version of the email
    plain_text = f"""
Hello,

This is an automated alert from your Dentist Friend.

The following items in your inventory are expiring within {days_threshold} days:

"""
    # Add items to plain text separately to avoid backslash issues
    for item in expiry_items:
        plain_text += f"- {item['Item']}: {item['Quantity']} units, expires in {item['Days Left']} days ({item['Expiry Date']})\n"

    plain_text += """
Please review these items and take appropriate action.

Regards,
Dentist Friend
"""

    # Attach both plaintext and HTML versions
    message.attach(MIMEText(plain_text, "plain"))
    message.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(user=ADMIN_EMAIL, password=ADMIN_PASSWORD)
        server.sendmail(from_addr=ADMIN_EMAIL, to_addrs=email, msg=message.as_string())
        server.quit()
        return "Email alert sent successfully"
    except Exception as e:
        return str(e)


def main():
    st.title("Dental Supply Tracker")

    # Authentication check
    if st.session_state.get("doctor_email") is None:
        st.error("Doctor Authentication Required: Please log in to access the inventory system")
        return

    with st.sidebar:
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Initialize inventory data in session state if not already present
    if 'inventory_data' not in st.session_state:
        st.session_state.inventory_data = fetch_stock()

    # Create the main tabs
    tab_inventory, tab_alerts, tab_reports = st.tabs(["Inventory", "Alerts", "Reports"])

    # Tab 1: Inventory
    with tab_inventory:
        # Refresh inventory data on each run to ensure it's up-to-date
        st.session_state.inventory_data = fetch_stock()
        display_inventory()

    # Tab 2: Alerts
    with tab_alerts:
        display_alerts()

    # Tab 3: Reports
    with tab_reports:
        display_reports()


def display_inventory():
    """Display and manage the inventory tab"""
    st.header("Current Inventory")

    # Display full inventory table first
    show_inventory()

    # Inventory management options below the table
    st.subheader("Inventory Management")

    # Create two columns for Add and Edit operations
    col_add, col_edit = st.columns(2)
    with col_add:
        with st.container(border=True):
            st.subheader("Add Inventory", divider="blue")
            add_items()

    with col_edit:
        with st.container(border=True):
            st.subheader("Edit Inventory", divider="orange")
            edit_inventory()

    with st.container(border=True):
        st.subheader("Import Inventory", divider="green")

        # Excel file uploader
        uploaded_file = st.file_uploader(
            "Upload CSV or Excel File",
            type=['csv', 'xlsx', 'xls'],
            help="Upload a CSV or Excel file containing inventory data."
        )

        if uploaded_file:
            st.info(f"File '{uploaded_file.name}' uploaded. Click 'Import Data' to process it.")

            # Display a sample of the uploaded file
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_preview = pd.read_csv(uploaded_file, nrows=5)
                    uploaded_file.seek(0)  # Reset file pointer after reading
                else:  # Excel file
                    df_preview = pd.read_excel(uploaded_file, nrows=5)
                    uploaded_file.seek(0)  # Reset file pointer after reading

                st.write("Preview of uploaded data: (first 5 rows)")
                st.dataframe(df_preview, use_container_width=True)
            except Exception as e:
                st.error(f"Error previewing file: {str(e)}")

        # Import button
        if st.button("🔼 Import Data", use_container_width=True) and uploaded_file:
            with st.spinner("Importing data..."):
                success, message = import_inventory(uploaded_file)
                if success:
                    st.success(message)
                    # Force refresh of inventory data
                    st.session_state.inventory_data = fetch_stock()
                    # Reset email sent flag when adding new items that might trigger alerts
                    st.session_state["email_alert_sent"] = False
                    st.rerun()
                else:
                    st.error(message)


def display_alerts():
    """Display alerts tab with expiry and low stock warnings"""
    st.header("Inventory Alerts")

    # Initialize email alert related session states
    doctor_doc = database.collection("doctors").document(doctor_email).get()
    if doctor_doc.exists:
        doctor_data = doctor_doc.to_dict()
        if "alert_email" in doctor_data and doctor_data["alert_email"]:
            st.session_state["enable_email_alerts"] = True
            st.session_state["alert_email"] = doctor_data["alert_email"]
    else:
        st.error("Doctor profile not found. Please ensure you are logged in correctly.")
        return

    # Track if we already sent an email this session to avoid spam
    if "email_alert_sent" not in st.session_state:
        st.session_state["email_alert_sent"] = False

    # Use inventory data from session state
    inventory_data = st.session_state.inventory_data

    if not inventory_data:
        st.info("No inventory items found. Please add items in the Inventory tab.")
        return

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Low Stock Alerts", divider="red")
            # Default low stock threshold for the global slider
            global_threshold = st.slider("Global Low Stock Threshold", min_value=1, max_value=50, value=5)

            # Find items below threshold quantity (using item-specific threshold when available)
            low_stock_items = []
            for item_id, details in inventory_data.items():
                # Get the item-specific threshold or use the global one
                item_threshold = details.get("low_threshold", global_threshold)
                if details["quantity"] <= item_threshold:
                    # Extract base name from item_id
                    item_name = item_id.split('_')[0] if '_' in item_id else item_id
                    expiry_date = details["expiry_date"]
                    low_stock_items.append({
                        "Item": item_name.title(),
                        "Quantity": details["quantity"],
                        "Threshold": item_threshold,
                        "Expiry Date": format_date(expiry_date)
                    })

            if low_stock_items:
                st.markdown("### 🚨 Low Stock Items")
                low_stock_df = pd.DataFrame(low_stock_items)
                st.dataframe(low_stock_df, use_container_width=True)

                # Create a visualization of low stock items
                fig = px.bar(
                    low_stock_df,
                    x="Item",
                    y="Quantity",
                    title="Items Below Threshold",
                    color="Quantity",
                    color_continuous_scale="Reds_r",
                    hover_data=["Threshold", "Expiry Date"]
                )
                fig.update_layout(xaxis_title="Item", yaxis_title="Quantity")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ All items have sufficient quantity")

    with col2:
        with st.container(border=True):
            st.subheader("Expiry Alerts", divider="orange")
            # Expiry alert settings and display
            days_threshold = st.slider("Days Until Expiry Warning", min_value=1, max_value=180, value=30)

            # Calculate days until expiry for each item
            today = datetime.today().date()
            expiry_items = []

            for item, details in inventory_data.items():
                try:
                    expiry_date = datetime.strptime(details["expiry_date"], "%Y-%m-%d").date()
                    days_until_expiry = (expiry_date - today).days

                    # Add items expiring within threshold days
                    if days_until_expiry <= days_threshold:
                        # Extract base name from item
                        item_name = item.split('_')[0] if '_' in item else item
                        expiry_items.append({
                            "Item": item_name.title(),
                            "Quantity": details["quantity"],
                            "Expiry Date": format_date(details["expiry_date"]),
                            "Days Left": days_until_expiry
                        })
                except ValueError as e:
                    st.error(f"Date format error for item '{item}': {str(e)}")
                    continue

            # Check if we need to send email alerts
            if expiry_items and st.session_state.get("enable_email_alerts", False) and not st.session_state["email_alert_sent"]:
                alert_email = st.session_state.get("alert_email")
                if alert_email:
                    result = send_alert(alert_email, expiry_items, days_threshold)
                    if "successfully" in result:
                        st.session_state["email_alert_sent"] = True
                        st.success(f"Email alert sent to {alert_email}")
                    else:
                        st.error(f"Failed to send email alert: {result}")

            if expiry_items:
                st.markdown("### ⚠️ Items Near Expiry")
                expiry_df = pd.DataFrame(expiry_items)
                expiry_df = expiry_df.sort_values("Days Left")
                st.dataframe(expiry_df, use_container_width=True)

                # Create a visualization for expiry alerts
                if len(expiry_df) > 0:
                    fig = px.bar(
                        expiry_df,
                        x="Item",
                        y="Days Left",
                        title=f"Items Expiring Within {days_threshold} Days",
                        color="Days Left",
                        color_continuous_scale="RdYlGn",
                    )
                    fig.update_layout(xaxis_title="Item", yaxis_title="Days Until Expiry")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ No items are nearing expiration")
                # Reset email sent flag when there are no items to alert about
                st.session_state["email_alert_sent"] = False

    with st.container(border=True):
        st.subheader("Alert Settings", divider="green")

        # Check if email alerts are enabled
        previous_email_alert_state = st.session_state.get("enable_email_alerts", False)
        enable_email_alerts = st.checkbox("Enable Email Alerts", value=previous_email_alert_state)

        # Check if the checkbox state has changed
        if enable_email_alerts and not previous_email_alert_state:
            # Initialize alert_email in session state if not already present
            if "alert_email" not in st.session_state:
                # Default to doctor's email if available
                st.session_state["alert_email"] = st.session_state.get("doctor_email", "")

            # Set the document in Firestore as soon as alert is enabled
            if doctor_email:
                try:
                    database.collection("doctors").document(doctor_email).set({
                        "alert_email": st.session_state["alert_email"]
                    }, merge=True)
                except Exception as e:
                    st.error(f"Failed to save alert settings: {str(e)}")
            else:
                st.error("Cannot save alert settings: No doctor email available")

            # Reset email sent flag when enabling alerts
            st.session_state["email_alert_sent"] = False

        # If user disables email alerts, remove the alert_email from Firestore
        if not enable_email_alerts and previous_email_alert_state:
            if doctor_email:
                try:
                    database.collection("doctors").document(doctor_email).update({
                        "alert_email": firestore.DELETE_FIELD
                    })
                except Exception as e:
                    st.error(f"Failed to update alert settings: {str(e)}")
            else:
                st.error("Cannot update alert settings: No doctor email available")

        st.session_state["enable_email_alerts"] = enable_email_alerts

        # Show email configuration only if alerts are enabled
        if enable_email_alerts:
            col1, col2 = st.columns([3, 1])
            with col1:
                alert_email = st.text_input(
                    "Alert Email",
                    value=st.session_state.get("alert_email", ""),
                    placeholder="Enter email for alerts"
                )

            with col2:
                if st.button("Update Email", use_container_width=True):
                    if not alert_email or "@" not in alert_email:
                        st.error("Please enter a valid email address")
                    else:
                        # Save the new alert email to session state
                        st.session_state["alert_email"] = alert_email

                        # Update the alert email in Firestore
                        if doctor_email:
                            try:
                                database.collection("doctors").document(doctor_email).set({
                                    "alert_email": alert_email
                                }, merge=True)
                                # Reset email sent flag when changing email
                                st.session_state["email_alert_sent"] = False
                                st.success(f"Email updated: Alerts will be sent to {alert_email}")
                            except Exception as e:
                                st.error(f"Failed to update email: {str(e)}")
                        else:
                            st.error("Cannot save email settings: No doctor email available")

            # Add a button to manually send test alert
            if st.button("Send Test Alert", use_container_width=True):
                if not alert_email or "@" not in alert_email:
                    st.error("Please enter a valid email address")
                elif expiry_items:
                    try:
                        result = send_alert(alert_email, expiry_items, days_threshold)
                        if "successfully" in result:
                            st.success(f"Test email alert sent to {alert_email}")
                        else:
                            st.error(f"Failed to send test email alert: {result}")
                    except Exception as e:
                        st.error(f"Error sending test email: {str(e)}")
                else:
                    st.warning("No items are near expiry. Add items that will expire soon to test the alert.")


def display_reports():
    """Display reports tab with analytics and export options"""
    st.header("Inventory Reports")

    # Use inventory data from session state
    inventory_data = st.session_state.inventory_data

    if inventory_data:
        # Prepare data for visualization
        today = datetime.today().date()
        inventory_records = []

        st.subheader("Summary Statistics", divider="blue")

        # Calculate total items, units, and items expiring soon
        total_items = len(inventory_data)
        total_units = sum(item["quantity"] for item in inventory_data.values())
        expiring_soon = sum(1 for item, details in inventory_data.items()
                            if (datetime.strptime(details["expiry_date"], "%Y-%m-%d").date() - today).days <= 30)

        # Create metrics row
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            st.metric("Total Items", total_items)
        with metric_col2:
            st.metric("Total Units", total_units)
        with metric_col3:
            st.metric("Expiring Soon (30 days)", expiring_soon)

        st.subheader("Inventory Visualizations", divider="green")

        for item_id, details in inventory_data.items():
            # Extract base name from item_id
            item_name = item_id.split('_')[0] if '_' in item_id else item_id
            item_name = item_name.capitalize()

            # Format the expiry date
            expiry_date = datetime.strptime(details["expiry_date"], "%Y-%m-%d").date()
            formatted_date = expiry_date.strftime("%b %d, %Y")

            # Create display name for charts
            display_name = f"{item_name} ({formatted_date})"
            days_until_expiry = (expiry_date - today).days

            inventory_records.append({
                "Item": item_name.title(),  # Base name for grouping
                "Display Name": display_name,  # Formatted name with date
                "Quantity": details["quantity"],
                "Category": details.get("category", ""),
                "Location": details.get("location", ""),
                "Days Until Expiry": days_until_expiry
            })

        viz_df = pd.DataFrame(inventory_records)

        # Create a dashboard with visualizations
        col1, col2 = st.columns(2)
        with col1:
            # Top items by quantity
            top_items = viz_df.sort_values("Quantity", ascending=False).head(10)
            fig1 = px.bar(
                top_items,
                x="Display Name",
                y="Quantity",
                title="Top Items by Quantity",
                color="Quantity",
                color_continuous_scale="Blues"
            )
            fig1.update_layout(
                xaxis_title="Item",
                yaxis_title="Quantity",
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            # Items closest to expiry
            if len(viz_df) > 0 and "Days Until Expiry" in viz_df.columns:
                expiry_sorted = viz_df.sort_values("Days Until Expiry").head(10)
                fig2 = px.bar(
                    expiry_sorted,
                    x="Display Name",
                    y="Days Until Expiry",
                    title="Items Closest to Expiry",
                    color="Days Until Expiry",
                    color_continuous_scale="RdYlGn",
                )
                fig2.update_layout(
                    xaxis_title="Item",
                    yaxis_title="Days Until Expiry",
                )
                st.plotly_chart(fig2, use_container_width=True)

        # Add pie chart for inventory distribution
        if len(inventory_data) > 0:
            st.subheader("Inventory Distribution")

            # For pie chart, use the display name with formatted date
            fig3 = px.pie(
                viz_df,
                values="Quantity",
                names="Display Name",
                title="Inventory Distribution by Item",
                hole=0.4
            )
            # Make the chart responsive to varying display sizes
            fig3.update_traces(textposition='inside', textinfo='percent+label')
            # Set margins to give the chart more room
            fig3.update_layout(margin=dict(t=50, b=50))

            st.plotly_chart(fig3, use_container_width=True)

        # Generate inventory records for export
        if 'inventory_records' in st.session_state:
            report_df = pd.DataFrame(st.session_state.inventory_records)

            # Export options
            st.subheader("Export Options", divider="blue")

            export_df = report_df.copy()
            export_df['Low Threshold'] = [st.session_state.inventory_data.get(item_id, {}).get('low_threshold', 5) 
                                          for item_id in report_df['ID']]

            if 'ID' in export_df.columns:
                export_df = export_df.drop(columns=['ID'])

            export_col1, export_col2 = st.columns(2)
            with export_col1:
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download CSV Report",
                    data=csv,
                    file_name=f"inventory_report_{datetime.today().strftime('%Y-%m-%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with export_col2:
                json_data = export_df.to_json(orient="records")
                st.download_button(
                    label="📄 Download JSON Report",
                    data=json_data,
                    file_name=f"inventory_report_{datetime.today().strftime('%Y-%m-%d')}.json",
                    mime="application/json",
                    use_container_width=True
                )
    else:
        st.info("No inventory data available. Add items in the Inventory tab to generate reports.")


def show_inventory():
    """Display the current inventory status with conditional formatting"""
    # Always refresh inventory data from session state
    inventory_data = st.session_state.inventory_data

    if inventory_data:
        st.session_state.inventory_records = []
        for item_id, details in inventory_data.items():
            # Extract base name from item_id
            item_name = item_id.split('_')[0] if '_' in item_id else item_id

            # Calculate days until expiry
            today = datetime.today().date()
            expiry_date = datetime.strptime(details["expiry_date"], "%Y-%m-%d").date()
            days_until_expiry = (expiry_date - today).days
            quantity = details["quantity"]

            # Get the item-specific threshold
            item_threshold = details.get("low_threshold", 5)

            # Determine status
            status = "Normal"
            if days_until_expiry <= 30:
                status = "Expiring Soon"
            if quantity <= item_threshold:
                status = "Low Stock"
            if days_until_expiry <= 0:
                status = "Expired"
            if quantity == 0:
                status = "Out of Stock"

            st.session_state.inventory_records.append({
                "Item": item_name.title(),
                "Quantity": details["quantity"],
                "Category": details.get("category", ""),
                "Location": details.get("location", ""),
                "Expiry Date": format_date(details["expiry_date"]),
                "Days Until Expiry": days_until_expiry,
                "Status": status,
                "ID": item_id  # Store the original ID for reference
            })

        # Create DataFrame and sort by status priority
        inventory_df = pd.DataFrame(st.session_state.inventory_records)

        # Custom sorting function to prioritize alerts
        def status_priority(status):
            priorities = {"Expired": 0, "Out of Stock": 1, "Low Stock": 2, "Expiring Soon": 3, "Normal": 4}
            return priorities.get(status, 4)

        # Sort the DataFrame by status priority
        inventory_df["Status Priority"] = inventory_df["Status"].apply(status_priority)
        inventory_df = inventory_df.sort_values("Status Priority")
        display_df = inventory_df.drop(columns=["Status Priority", "ID"])

        # Initialize the active filter in session state if it doesn't exist
        if "active_filter" not in st.session_state:
            st.session_state.active_filter = "All Items"

        # Apply filter to the DataFrame
        if st.session_state.active_filter != "All Items":
            filtered_df = display_df[display_df["Status"] == st.session_state.active_filter]
        else:
            filtered_df = display_df

        # Reset index to show proper sequential numbering starting at 1
        filtered_df = filtered_df.reset_index(drop=True)
        # Add 1 to the index to start from 1 instead of 0
        filtered_df.index = filtered_df.index + 1

        # Display filtered data with conditional formatting
        st.dataframe(
            filtered_df,
            use_container_width=True,
            column_config={
                "Quantity": st.column_config.NumberColumn(
                    "Quantity",
                    help="Number of units in stock",
                    format="%d"
                ),
                "Category": st.column_config.TextColumn(
                    "Category",
                    help="Item category classification"
                ),
                "Location": st.column_config.TextColumn(
                    "Location", 
                    help="Physical storage location"
                ),
                "Days Until Expiry": st.column_config.NumberColumn(
                    "Days Until Expiry",
                    help="Days remaining until item expires",
                    format="%d days"
                ),
                "Status": st.column_config.TextColumn(
                    "Status",
                    help="Inventory status indicator"
                )
            },
            height=400
        )

        st.write("### Filter Inventory")
        filter_col1, filter_col2, filter_col3, filter_col4, filter_col5, filter_col6 = st.columns(6)

        # Display filter status
        if st.session_state.active_filter != "All Items":
            st.info(f"Showing {len(filtered_df)} items with status: {st.session_state.active_filter}")
        else:
            st.info(f"Showing all {len(filtered_df)} items")

        # Button styling function to highlight active filter
        def get_button_style(filter_name):
            if st.session_state.active_filter == filter_name:
                return "primary"
            return "secondary"

        # Create filter buttons
        with filter_col1:
            if st.button("All Items", key="all_items", use_container_width=True, type=get_button_style("All Items")):
                st.session_state.active_filter = "All Items"
                st.rerun()

        with filter_col2:
            if st.button("Normal", key="normal", use_container_width=True, type=get_button_style("Normal")):
                st.session_state.active_filter = "Normal"
                st.rerun()

        with filter_col3:
            if st.button("Low Stock", key="low_stock", use_container_width=True, type=get_button_style("Low Stock")):
                st.session_state.active_filter = "Low Stock"
                st.rerun()

        with filter_col4:
            if st.button("Expiring Soon", key="expiring_soon", use_container_width=True, type=get_button_style("Expiring Soon")):
                st.session_state.active_filter = "Expiring Soon"
                st.rerun()

        with filter_col5:
            if st.button("Expired", key="expired", use_container_width=True, type=get_button_style("Expired")):
                st.session_state.active_filter = "Expired"
                st.rerun()

        with filter_col6:
            if st.button("Out of Stock", key="out_of_stock", use_container_width=True, type=get_button_style("Out of Stock")):
                st.session_state.active_filter = "Out of Stock"
                st.rerun()
    else:
        st.info("Inventory Status: No items currently in stock")


def add_items():
    """Add new items to inventory or update existing items"""
    column_first, column_second, column_third = st.columns(3)
    with column_first:
        item_name = st.text_input("Item Name", placeholder="Enter item name").strip().lower()

    with column_second:
        item_quantity = st.number_input("Quantity", min_value=1, step=1)

    with column_third:
        low_threshold = st.number_input("Low Stock Threshold", min_value=1, value=5, step=1)

    # Second row for expiry, category, and location
    col_expiry, col_category, col_location = st.columns(3)
    with col_expiry:
        expiry_date = st.date_input("Expiry Date", min_value=datetime.today().date())
    
    with col_category:
        item_category = st.text_input("Category", placeholder="e.g., Surgical, Cleaning, Medication").strip()
    
    with col_location:
        item_location = st.text_input("Location", placeholder="e.g., Cabinet 1, Shelf B, Drawer 3").strip()

    if st.button("Add Item", use_container_width=True):
        if item_name:
            expiry_string = expiry_date.strftime("%Y-%m-%d")

            # Generate a unique item ID based on name and expiry date
            item_id = f"{item_name}_{expiry_string}"

            # Check if item with same name and expiry date already exists
            if item_id in st.session_state.inventory_data:
                st.warning(f"Item '{item_name}' with the same expiry date already exists. Please edit the existing item instead.")
            else:
                # Store the item with its unique ID
                success = store_stock(item_id, item_quantity, expiry_string, low_threshold, item_category, item_location)
                if success:
                    st.success(f"Item Added: {item_quantity} units of '{item_name}' (Expires: {format_date(expiry_string)}) added to inventory")

                    # Reset email sent flag when adding new items that might trigger alerts
                    st.session_state["email_alert_sent"] = False
                    # Force refresh of inventory data
                    st.session_state.inventory_data = fetch_stock()
                    st.rerun()
        else:
            st.error("Entry Error: Please enter a valid item name")


def edit_inventory():
    """Edit or remove items from inventory"""
    search_term = st.text_input("Item to Edit", placeholder="Enter item name to edit").strip().lower()
    find_edit_button = st.button("🔍 Find Item", use_container_width=True)

    # Track if we're in search mode or edit mode
    if "edit_search_mode" not in st.session_state:
        st.session_state.edit_search_mode = False

    if search_term and find_edit_button:
        # Clear previous selections when searching for a new item
        st.session_state.pop("edit_item_id", None)
        st.session_state.pop("matching_items", None)
        st.session_state.edit_search_mode = True

        # Find all items that contain the search term (partial match)
        matching_items = {}
        for item_id, details in st.session_state.inventory_data.items():
            # Extract the base name from the item_id (removing the _date suffix)
            name_part = item_id.split('_')[0] if '_' in item_id else item_id
            
            # Check if search term appears anywhere in the name (partial match)
            if search_term in name_part:
                # Add to matching items with expiry date as key info
                matching_items[item_id] = {
                    "name": name_part,
                    "expiry_date": details["expiry_date"],
                    "quantity": details["quantity"],
                    "low_threshold": details.get("low_threshold", 5)
                }

        if not matching_items:
            st.error(f"Item Not Found: No items containing '{search_term}' found in inventory")
            st.session_state.edit_search_mode = False
            return

        # Store matching items in session state to access them after rerun
        st.session_state.matching_items = matching_items
        st.session_state.search_term = search_term

    # Check if we have matching items from a previous search
    if st.session_state.get("edit_search_mode") and "matching_items" in st.session_state:
        matching_items = st.session_state.matching_items

        # Select the item to edit
        edit_item = None

        # If only one matching item, select it directly
        if len(matching_items) == 1:
            edit_item = list(matching_items.keys())[0]
            st.session_state.edit_item_id = edit_item
        # If multiple matching items, show dropdown
        else:
            item_options = []
            for item_id, details in matching_items.items():
                display_text = f"{details['name']} (Expires: {format_date(details['expiry_date'])}) - {details['quantity']} units"
                item_options.append({"id": item_id, "display": display_text})

            selected_option = st.selectbox(
                "Select Item to Edit",
                options=[item["display"] for item in item_options],
                index=0,
                key="item_selector"
            )

            # Get the selected item ID
            selected_index = item_options.index(next(item for item in item_options if item["display"] == selected_option))
            edit_item = item_options[selected_index]["id"]
            st.session_state.edit_item_id = edit_item

        # Handle item editing
        if edit_item and edit_item in st.session_state.inventory_data:
            handle_item_editing(edit_item)
        elif "edit_item_id" in st.session_state:
            st.error("The selected item no longer exists in the inventory.")
            st.session_state.edit_search_mode = False
            st.session_state.pop("edit_item_id", None)
            st.session_state.pop("matching_items", None)


def handle_item_editing(edit_item):
    """Handle the editing interface for a specific inventory item"""
    item_details = st.session_state.inventory_data[edit_item]
    base_name = edit_item.split('_')[0] if '_' in edit_item else edit_item

    # Display current item information
    st.info(f"Editing: '{base_name}' | Current quantity: {item_details['quantity']} units | "
           f"Expiry date: {format_date(item_details['expiry_date'])}")

    # Create column layout for edit inputs
    edit_col1, edit_col2, edit_col3 = st.columns(3)
    with edit_col1:
        new_quantity = st.number_input(
            "New Quantity",
            min_value=0,
            value=item_details['quantity'],
            step=1
        )

    with edit_col2:
        try:
            current_expiry = datetime.strptime(item_details['expiry_date'], "%Y-%m-%d").date()
            today = datetime.today().date()
            if current_expiry < today:
                current_expiry = today

            new_expiry = st.date_input(
                "New Expiry Date",
                value=current_expiry,
                min_value=today
            )
        except Exception as e:
            st.error(f"Date validation error: {e}")
            new_expiry = datetime.today().date()

    with edit_col3:
        new_threshold = st.number_input(
            "New Low Stock Threshold",
            min_value=1,
            value=item_details.get('low_threshold', 5),
            step=1
        )

    cat_col, loc_col = st.columns(2)
    with cat_col:
        new_category = st.text_input(
            "Category",
            value=item_details.get('category', ''),
            placeholder="e.g., Surgical, Cleaning, Medication",
            key="edit_category"
        )
    
    with loc_col:
        new_location = st.text_input(
            "Location",
            value=item_details.get('location', ''),
            placeholder="e.g., Cabinet 1, Shelf B, Drawer 3",
            key="edit_location"
        )

    # Create two buttons side by side - Save Changes and Delete Item
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Save Changes", use_container_width=True, key="save_changes"):
            expiry_string = new_expiry.strftime("%Y-%m-%d")

            # If expiry date changed, we need to create a new item ID and delete the old one
            new_item_id = f"{base_name}_{expiry_string}"

            if new_item_id != edit_item:
                # Check if an item with the new ID already exists
                if new_item_id in st.session_state.inventory_data:
                    st.error(f"Cannot update: An item with name '{base_name}' and expiry date {format_date(expiry_string)} already exists")
                else:
                    # Create new item with updated expiry
                    stock_collection.document(new_item_id).set({
                        "quantity": new_quantity,
                        "expiry_date": expiry_string,
                        "low_threshold": new_threshold,
                        "category": new_category,
                        "location": new_location
                    }, merge=True)
                    # Delete old item
                    stock_collection.document(edit_item).delete()
                    st.success(f"Item Updated with new expiry: '{base_name}' has been updated successfully")

                    # Reset email sent flag when editing items that might trigger alerts
                    st.session_state["email_alert_sent"] = False
                    # Clear session state
                    st.session_state.pop("edit_item_id", None)
                    st.session_state.pop("matching_items", None)
                    # Force refresh of inventory data
                    st.session_state.inventory_data = fetch_stock()
                    st.rerun()
            else:
                # Update existing item
                stock_collection.document(edit_item).set({
                    "quantity": new_quantity,
                    "expiry_date": expiry_string,
                    "low_threshold": new_threshold,
                    "category": new_category,
                    "location": new_location
                }, merge=True)
                st.success(f"Item Updated: '{base_name}' has been updated successfully")

                # Reset email sent flag when editing items that might trigger alerts
                st.session_state["email_alert_sent"] = False
                # Clear session state
                st.session_state.pop("edit_item_id", None)
                st.session_state.pop("matching_items", None)
                # Force refresh of inventory data
                st.session_state.inventory_data = fetch_stock()
                st.rerun()

    with col2:
        if st.button("🗑️ Delete Item", use_container_width=True, key="delete_item"):
            # Directly delete the item and clear state in one go
            try:
                stock_collection.document(edit_item).delete()
                st.success(f"Item Removed: '{base_name}' (Expires: {format_date(item_details['expiry_date'])}) has been deleted from inventory")

                # Reset email sent flag when deleting items that might change alert status
                st.session_state["email_alert_sent"] = False

                # Clear all session state variables related to editing
                st.session_state.pop("edit_item_id", None)
                st.session_state.pop("matching_items", None)

                # Force refresh of inventory data
                st.session_state.inventory_data = fetch_stock()
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting item: {str(e)}")


main()
show_footer()
