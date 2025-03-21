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

# Initialize Firestore database connection
database = firestore.client()
doctor_email = st.session_state["doctor_email"] if "doctor_email" in st.session_state else None
stock_collection = database.collection("doctors").document(doctor_email).collection("stock") if doctor_email else None


def fetch_stock():
    """Fetch all inventory items from Firestore database"""
    stock_documents = stock_collection.stream()
    return {doc.id: doc.to_dict() for doc in stock_documents}


def store_stock(item_name, item_quantity, expiry_date):
    """Store or update inventory item in Firestore database"""
    stock_collection.document(item_name).set({
        "quantity": item_quantity,
        "expiry_date": expiry_date
    }, merge=True)


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


def send_expiry_alert(email, expiry_items, days_threshold):
    """Send email alert for items nearing expiry"""
    # Get email credentials from environment variables
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        return "Email credentials not found in environment variables"

    # Format items for email content
    items_list = "\n".join([f"- {item['Item']}: {item['Quantity']} units, expires in {item['Days Left']} days ({item['Expiry Date']})" 
                           for item in expiry_items])

    # Prepare email content
    subject = f"Dental Supply Alert: Items Expiring Within {days_threshold} Days"
    body = f"""
Hello,

This is an automated alert from your Dental Supply Tracker.

The following items in your inventory are expiring within {days_threshold} days:

{items_list}

Please review these items and take appropriate action.

Regards,
Dental Supply Tracker
"""
    full_message = f"Subject: {subject}\n\n{body}"

    try:
        # Connect to Gmail SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Enable encryption
        server.login(user=ADMIN_EMAIL, password=ADMIN_PASSWORD)

        # Send alert email to specified email address
        server.sendmail(from_addr=ADMIN_EMAIL, to_addrs=email, msg=full_message)

        # Close the connection
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


def display_alerts():
    """Display alerts tab with expiry and low stock warnings"""
    st.header("Inventory Alerts")

    # Initialize email alert related session states
    doctor_doc = database.collection("doctors").document(doctor_email).get()
    doctor_data = doctor_doc.to_dict()
    if "alert_email" in doctor_data and doctor_data["alert_email"]:
        st.session_state["enable_email_alerts"] = True
        st.session_state["alert_email"] = doctor_data["alert_email"]
    
    # Track if we already sent an email this session to avoid spam
    if "email_alert_sent" not in st.session_state:
        st.session_state["email_alert_sent"] = False

    # Use inventory data from session state
    inventory_data = st.session_state.inventory_data

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Low Stock Alerts", divider="red")
            # Low stock settings and display
            threshold = st.slider("Low Stock Threshold", min_value=1, max_value=50, value=5)

            # Find items below threshold quantity
            low_stock_items = [
                (item, details["quantity"])
                for item, details in inventory_data.items()
                if details["quantity"] <= threshold
            ]

            if low_stock_items:
                st.markdown("### 🚨 Low Stock Items")
                low_stock_df = pd.DataFrame(low_stock_items, columns=["Item", "Quantity"])
                low_stock_df["Item"] = low_stock_df["Item"].str.capitalize()
                st.dataframe(low_stock_df, use_container_width=True)

                # Create a visualization of low stock items
                fig = px.bar(
                    low_stock_df,
                    x="Item",
                    y="Quantity",
                    title=f"Items Below Threshold ({threshold} units)",
                    color="Quantity",
                    color_continuous_scale="Reds_r"
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
                expiry_date = datetime.strptime(details["expiry_date"], "%Y-%m-%d").date()
                days_until_expiry = (expiry_date - today).days

                # Add items expiring within threshold days
                if days_until_expiry <= days_threshold:
                    expiry_items.append({
                        "Item": item.capitalize(),
                        "Quantity": details["quantity"],
                        "Expiry Date": format_date(details["expiry_date"]),
                        "Days Left": days_until_expiry
                    })

            # Check if we need to send email alerts
            if expiry_items and st.session_state.get("enable_email_alerts", False) and not st.session_state["email_alert_sent"]:
                alert_email = st.session_state.get("alert_email")
                if alert_email:
                    result = send_expiry_alert(alert_email, expiry_items, days_threshold)
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
                database.collection("doctors").document(doctor_email).set({
                    "alert_email": st.session_state["alert_email"]
                }, merge=True)
            
            # Reset email sent flag when enabling alerts
            st.session_state["email_alert_sent"] = False

        # If user disables email alerts, remove the alert_email from Firestore
        if not enable_email_alerts and previous_email_alert_state:
            database.collection("doctors").document(doctor_email).update({
                "alert_email": firestore.DELETE_FIELD
            })

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
                    # Save the new alert email to session state
                    st.session_state["alert_email"] = alert_email

                    # Update the alert email in Firestore
                    if doctor_email:
                        database.collection("doctors").document(doctor_email).set({
                            "alert_email": alert_email
                        }, merge=True)

                    # Reset email sent flag when changing email
                    st.session_state["email_alert_sent"] = False
                    st.success(f"Email updated: Alerts will be sent to {alert_email}")
            
            # Add a button to manually send test alert
            if st.button("Send Test Alert", use_container_width=True):
                if expiry_items:
                    result = send_expiry_alert(alert_email, expiry_items, days_threshold)
                    if "successfully" in result:
                        st.success(f"Test email alert sent to {alert_email}")
                    else:
                        st.error(f"Failed to send test email alert: {result}")
                else:
                    st.warning("No items are near expiry. Add items that will expire soon to test the alert.")


def display_reports():
    """Display reports tab with analytics and export options"""
    st.header("Inventory Reports")

    # Use inventory data from session state
    inventory_data = st.session_state.inventory_data

    if inventory_data:
        # First show visualizations
        st.subheader("Inventory Visualizations", divider="green")

        # Prepare data for visualization
        today = datetime.today().date()
        inventory_records = []

        for item_name, details in inventory_data.items():
            expiry_date = datetime.strptime(details["expiry_date"], "%Y-%m-%d").date()
            days_until_expiry = (expiry_date - today).days

            inventory_records.append({
                "Item": item_name.capitalize(),
                "Quantity": details["quantity"],
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
                x="Item",
                y="Quantity",
                title="Top Items by Quantity",
                color="Quantity",
                color_continuous_scale="Blues"
            )
            fig1.update_layout(xaxis_title="Item", yaxis_title="Quantity")
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            # Items closest to expiry
            if len(viz_df) > 0 and "Days Until Expiry" in viz_df.columns:
                expiry_sorted = viz_df.sort_values("Days Until Expiry").head(10)
                fig2 = px.bar(
                    expiry_sorted,
                    x="Item",
                    y="Days Until Expiry",
                    title="Items Closest to Expiry",
                    color="Days Until Expiry",
                    color_continuous_scale="RdYlGn",
                )
                fig2.update_layout(xaxis_title="Item", yaxis_title="Days Until Expiry")
                st.plotly_chart(fig2, use_container_width=True)

        # Add pie chart for inventory distribution
        if len(inventory_data) > 0:
            st.subheader("Inventory Distribution")
            fig3 = px.pie(
                viz_df,
                values="Quantity",
                names="Item",
                title="Inventory Distribution by Item",
                hole=0.4
            )
            st.plotly_chart(fig3, use_container_width=True)

        # Then summary statistics
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

        # Generate inventory records for export
        if 'inventory_records' in st.session_state:
            report_df = pd.DataFrame(st.session_state.inventory_records)

            # Export options
            st.subheader("Export Options", divider="blue")

            export_col1, export_col2 = st.columns(2)
            with export_col1:
                csv = report_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download CSV Report",
                    data=csv,
                    file_name=f"inventory_report_{datetime.today().strftime('%Y-%m-%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with export_col2:
                json_data = report_df.to_json(orient="records")
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
    """Display all inventory items in a data table"""
    # Always refresh inventory data from session state
    inventory_data = st.session_state.inventory_data

    if inventory_data:
        st.session_state.inventory_records = []
        for item_name, details in inventory_data.items():
            # Calculate days until expiry
            today = datetime.today().date()
            expiry_date = datetime.strptime(details["expiry_date"], "%Y-%m-%d").date()
            days_until_expiry = (expiry_date - today).days
            quantity = details["quantity"]

            # Determine status
            status = "Normal"
            if days_until_expiry <= 30:
                status = "⚠️ Expiring Soon"
            if details["quantity"] <= 5:
                status = "🚨 Low Stock"
            if days_until_expiry <= 0:
                status = "❌ Expired"
            if quantity == 0:
                status = "❌ Out of Stock"

            st.session_state.inventory_records.append({
                "Item": item_name.capitalize(),
                "Quantity": details["quantity"],
                "Expiry Date": format_date(details["expiry_date"]),
                "Days Until Expiry": days_until_expiry,
                "Status": status
            })

        # Create DataFrame and sort by status priority
        inventory_df = pd.DataFrame(st.session_state.inventory_records)
        # Custom sorting function to prioritize alerts
        def status_priority(status):
            priorities = {"❌ Expired": 0, "❌ Out of Stock": 1, "🚨 Low Stock": 2, "⚠️ Expiring Soon": 3, "Normal": 4}
            return priorities.get(status, 4)

        # Sort by priority (critical items first)
        inventory_df["Status Priority"] = inventory_df["Status"].apply(status_priority)
        inventory_df = inventory_df.sort_values("Status Priority")
        inventory_df = inventory_df.drop(columns=["Status Priority"])

        # Reset index to show proper sequential numbering starting at 1
        inventory_df = inventory_df.reset_index(drop=True)
        # Add 1 to the index to start from 1 instead of 0
        inventory_df.index = inventory_df.index + 1

        # Display with conditional formatting
        st.dataframe(
            inventory_df,
            use_container_width=True,
            column_config={
                "Quantity": st.column_config.NumberColumn(
                    "Quantity",
                    help="Number of units in stock",
                    format="%d"
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

        # Quick filter options
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            if st.button("🔍 Show Low Stock", use_container_width=True):
                st.error("Filters are not yet implemented. Please check the Alerts tab for low stock items")

        with filter_col2:
            if st.button("🔍 Show Expiring Soon", use_container_width=True):
                st.error("Filters are not yet implemented. Please check the Alerts tab for expiring items")

        with filter_col3:
            if st.button("🧹 Clear Inventory", use_container_width=True):
                # Get all documents in the stock collection and delete them
                docs = stock_collection.stream()
                for doc in docs:
                    doc.reference.delete()

                st.session_state.inventory_data = fetch_stock()
                st.success("Inventory Cleared: All items have been removed")
                st.rerun()
    else:
        st.info("Inventory Status: No items currently in stock")


def add_items():
    """Add new items to inventory or update existing items"""
    column_first, column_second = st.columns(2)
    with column_first:
        item_name = st.text_input("Item Name", placeholder="Enter item name").strip().lower()

    with column_second:
        item_quantity = st.number_input("Quantity", min_value=1, step=1)

    expiry_date = st.date_input("Expiry Date", min_value=datetime.today().date())

    if st.button("➕ Add Item", use_container_width=True):
        if item_name:
            expiry_string = expiry_date.strftime("%Y-%m-%d")

            # Check if item already exists
            if item_name in st.session_state.inventory_data:
                st.warning(f"Item '{item_name}' already exists. Please use Edit Inventory to modify it.")
                return

            # Add new item
            store_stock(item_name, item_quantity, expiry_string)
            st.success(f"Item Added: {item_quantity} units of '{item_name}' added to inventory")

            # Reset email sent flag when adding new items that might trigger alerts
            st.session_state["email_alert_sent"] = False

            # Force refresh of inventory data
            st.session_state.inventory_data = fetch_stock()
            st.rerun()
        else:
            st.error("Entry Error: Please enter a valid item name")


def edit_inventory():
    """Edit or remove items from inventory"""
    edit_item = st.text_input("Item to Edit", placeholder="Enter item name to edit").strip().lower()
    find_edit_button = st.button("🔍 Find Item", use_container_width=True)

    # Item found in inventory - display edit options
    if edit_item in st.session_state.inventory_data:
        item_details = st.session_state.inventory_data[edit_item]
        st.success(f"Item Found: '{edit_item}'")

        # Display current item information
        st.info(f"Current quantity: {item_details['quantity']} units | Expiry date: {format_date(item_details['expiry_date'])}")

        # Create two-column layout for edit inputs
        edit_col1, edit_col2 = st.columns(2)
        with edit_col1:
            new_quantity = st.number_input(
                "New Quantity",
                min_value=0,
                value=item_details['quantity'],
                step=1
            )

        with edit_col2:
            # Convert string date to datetime object for the date input widget
            try:
                current_expiry = datetime.strptime(item_details['expiry_date'], "%Y-%m-%d").date()
                # Ensure current_expiry is not before today to avoid date validation error
                today = datetime.today().date()
                if current_expiry < today:
                    current_expiry = today

                new_expiry = st.date_input(
                    "New Expiry Date",
                    value=current_expiry,
                    min_value=today
                )
            except Exception as e:
                # Handle any date parsing errors
                st.error(f"Date validation error: {e}")
                new_expiry = datetime.today().date()

        # Create two buttons side by side - Save Changes and Delete Item
        col1, col2 = st.columns(2)
        with col1:
            save_changes = st.button("✅ Save Changes", use_container_width=True)

        with col2:
            delete_button = st.button("🗑️ Delete Item", use_container_width=True)

        # Process based on which button was clicked
        if save_changes:
            expiry_string = new_expiry.strftime("%Y-%m-%d")
            store_stock(edit_item, new_quantity, expiry_string)
            st.success(f"Item Updated: '{edit_item}' has been updated successfully")

            # Reset email sent flag when editing items that might trigger alerts
            st.session_state["email_alert_sent"] = False

            # Force refresh of inventory data
            st.session_state.inventory_data = fetch_stock()
            st.rerun()

        elif delete_button:
            stock_collection.document(edit_item).delete()
            st.success(f"Item Removed: '{edit_item}' has been deleted from inventory")

            # Reset email sent flag when deleting items that might change alert status
            st.session_state["email_alert_sent"] = False

            # Force refresh of inventory data
            st.session_state.inventory_data = fetch_stock()
            st.rerun()

    # Item not found in inventory
    elif edit_item and find_edit_button:
        st.error(f"Item Not Found: '{edit_item}' does not exist in inventory")


main()
show_footer()