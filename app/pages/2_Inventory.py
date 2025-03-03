import streamlit as st
import pandas as pd
from datetime import datetime
from firebase_admin import firestore
from utils import show_footer

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

        # Delete item if removing all quantity or more
        if quantity_remove == 0 or quantity_remove >= current_quantity:
            item_reference.delete()
            st.success(f"Item Removed: '{item_name}' has been deleted from inventory")
        else:
            # Otherwise reduce the quantity
            item_reference.update({"quantity": current_quantity - quantity_remove})
            st.success(f"Quantity Updated: {quantity_remove} units of '{item_name}' removed")


def main():
    st.title("Dental Supply Tracker")

    # Authentication check
    if st.session_state.get('doctor_email') is None:
        st.error("Doctor Authentication Required: Please log in to access the inventory system")
        return

    inventory_data = fetch_stock()

    # UI Sections in separate containers
    with st.container(border=True):
        inventory_data = add_items(inventory_data)

    with st.container(border=True):
        inventory_data = remove_items(inventory_data)

    with st.container(border=True):
        st.header("Current Inventory")
        show_inventory(inventory_data)

    with st.container(border=True):
        search_items(inventory_data)

    with st.container(border=True):
        show_alerts(inventory_data)

    with st.container(border=True):
        show_reports(inventory_data)


def add_items(inventory_data):
    """Add new items to inventory or update existing items"""
    st.header("Add Inventory")
    column_first, column_second = st.columns(2)

    with column_first:
        item_name = st.text_input("Item Name", placeholder="Enter dental supply name").strip().lower()

    with column_second:
        item_quantity = st.number_input("Quantity", min_value=0, step=1)

    expiry_date = st.date_input("Expiry Date", min_value=datetime.today())

    if st.button("➕ Add Item"):
        if item_name:
            expiry_string = expiry_date.strftime("%Y-%m-%d")
            # Check if item already exists and add to current quantity
            existing_item = inventory_data.get(item_name, {"quantity": 0})
            total_quantity = existing_item["quantity"] + item_quantity

            store_stock(item_name, total_quantity, expiry_string)
            st.success(f"Item Added: {item_quantity} units of '{item_name}' added to inventory")
            return fetch_stock()
        else:
            st.error("Entry Error: Please enter a valid item name")

    return inventory_data


def remove_items(inventory_data):
    """Remove items from inventory or reduce quantity"""
    st.header("Remove Inventory")
    removal_item = st.text_input("Item to Remove", placeholder="Enter item name to remove").strip().lower()

    # Show current quantity if item exists
    if removal_item in inventory_data:
        st.write(f"Current inventory: {inventory_data[removal_item]['quantity']} units")
        quantity_remove = st.number_input("Removal Quantity (0 to delete completely)", min_value=0, step=1)

        if st.button("➖ Remove Item"):
            modify_stock(removal_item, quantity_remove)
            return fetch_stock()
    elif st.button("🔍 Find Item"):
        st.error(f"Item Not Found: '{removal_item}' does not exist in inventory")

    return inventory_data


def show_inventory(inventory_data):
    """Display all inventory items in a data table"""
    if inventory_data:
        inventory_records = []
        for item_name, details in inventory_data.items():
            inventory_records.append({
                "Item": item_name.capitalize(),
                "Quantity": details["quantity"],
                "Expiry Date": details["expiry_date"]
            })

        inventory_df = pd.DataFrame(inventory_records)
        st.dataframe(inventory_df, use_container_width=True)
    else:
        st.info("Inventory Status: No items currently in stock")


def search_items(inventory_data):
    """Search for specific items in inventory"""
    st.header("Inventory Search")
    search_term = st.text_input("Search Item", placeholder="Enter item name to search").strip().lower()

    if st.button("🔍 Search Items"):
        if search_term in inventory_data:
            details = inventory_data[search_term]
            st.success(f"Item Located: '{search_term.capitalize()}' found with {details['quantity']} units, Expiry: {details['expiry_date']}")
        else:
            st.warning(f"Search Failed: '{search_term.capitalize()}' not found in inventory")


def show_alerts(inventory_data):
    """Display inventory alerts for low stock and expiring items"""
    st.header("Inventory Alerts")
    alert_tab1, alert_tab2 = st.tabs(["Low Stock", "Expiry Alerts"])

    with alert_tab1:
        threshold = st.number_input("Low Stock Threshold", min_value=1, step=1, value=5)

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
        else:
            st.success("Stock Status: All items have sufficient quantity")

    with alert_tab2:
        days_threshold = st.number_input("Days Until Expiry", min_value=1, step=1, value=30)

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
                    "Expiry Date": details["expiry_date"],
                    "Days Left": days_until_expiry
                })

        if expiry_items:
            st.markdown("### ⚠️ Items Near Expiry")
            expiry_df = pd.DataFrame(expiry_items)
            expiry_df = expiry_df.sort_values("Days Left")
            st.dataframe(expiry_df, use_container_width=True)
        else:
            st.success("Expiry Status: No items are nearing expiration")


def show_reports(inventory_data):
    """Generate inventory reports and export data"""
    st.header("Inventory Reports")
    report_tab1, report_tab2 = st.tabs(["Summary", "Export Data"])

    with report_tab1:
        if inventory_data:
            # Calculate summary statistics
            total_items = len(inventory_data)
            total_units = sum(item["quantity"] for item in inventory_data.values())
            today = datetime.today().date()
            expiring_soon = sum(1 for item, details in inventory_data.items()
                                if (datetime.strptime(details["expiry_date"], "%Y-%m-%d").date() - today).days <= 30)

            summary_data = {
                "Metric": ["Total Items", "Total Units", "Expiring Within 30 Days"],
                "Value": [total_items, total_units, expiring_soon]
            }
            summary_df = pd.DataFrame(summary_data)
            st.table(summary_df)
        else:
            st.info("Report Status: No inventory data available")

    with report_tab2:
        if inventory_data:
            if st.button("📊 Generate Report"):
                # Create downloadable CSV report
                today = datetime.today().date()
                inventory_records = []
                for item_name, details in inventory_data.items():
                    inventory_records.append({
                        "Item": item_name.capitalize(),
                        "Quantity": details["quantity"],
                        "Expiry Date": details["expiry_date"],
                        "Days Until Expiry": (datetime.strptime(details["expiry_date"], "%Y-%m-%d").date() - today).days
                    })

                export_df = pd.DataFrame(inventory_records)
                csv = export_df.to_csv(index=False)

                st.download_button(
                    label="Download Inventory Report",
                    data=csv,
                    file_name=f"inventory_report_{datetime.today().strftime('%Y-%m-%d')}.csv",
                    mime="text/csv"
                )

                st.success("Report Generated: Inventory data exported successfully")
        else:
            st.info("Export Status: No data available for export")


main()
show_footer()
