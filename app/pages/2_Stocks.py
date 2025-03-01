import json
from datetime import datetime, timedelta
import streamlit as st

# File to save and load stock data
STOCK_FILE = "dental_stock.json"

# Load stock from a file if it exists
def load_stock():
    try:
        with open(STOCK_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save stock to a file
def save_stock(stock):
    with open(STOCK_FILE, "w") as file:
        json.dump(stock, file, indent=4)

# Streamlit App
st.title("Dental Stock Management System")

# Load stock
stock = load_stock()

# Add Stock
with st.expander("Add Stock"):
    item = st.text_input("Enter the item name").strip().lower()
    quantity = st.number_input("Enter the quantity to add", min_value=0, step=1)
    expiry_date = st.date_input("Enter the expiry date")

    if st.button("Add Item"):
        if item:
            expiry_date_str = expiry_date.strftime("%Y-%m-%d")
            if item in stock:
                stock[item]["quantity"] += quantity
            else:
                stock[item] = {"quantity": quantity, "expiry_date": expiry_date_str}
            save_stock(stock)
            st.success(f"{quantity} units of '{item}' added with expiry date {expiry_date_str}.")
        else:
            st.error("Please enter an item name.")

# Remove Stock
with st.expander("Remove Stock"):
    item = st.text_input("Enter the item name to remove").strip().lower()
    if item in stock:
        st.write(f"Current stock: {stock[item]['quantity']} units")
        quantity_to_remove = st.number_input("Enter quantity to remove (or 0 to delete)", min_value=0, step=1)
        if st.button("Remove Item"):
            if quantity_to_remove == 0 or quantity_to_remove >= stock[item]["quantity"]:
                del stock[item]
                save_stock(stock)
                st.success(f"'{item}' removed from stock.")
            else:
                stock[item]["quantity"] -= quantity_to_remove
                save_stock(stock)
                st.success(f"{quantity_to_remove} units of '{item}' removed.")
    elif st.button("Check Item to Remove"):
        st.error(f"'{item}' not found in stock.")

# View Stock
with st.expander("View Stock"):
    if stock:
        for item, details in stock.items():
            expiry_date = details["expiry_date"]
            st.write(f"- **{item.capitalize()}**: {details['quantity']} units, Expiry: {expiry_date}")
    else:
        st.write("Stock is empty.")

# Search Stock
with st.expander("Search Stock"):
    search_item = st.text_input("Enter the item name to search").strip().lower()
    if st.button("Search Item"):
        if search_item in stock:
            details = stock[search_item]
            expiry_date = details["expiry_date"]
            st.success(f"'{search_item.capitalize()}' is in stock: {details['quantity']} units, Expiry: {expiry_date}.")
        else:
            st.error(f"'{search_item.capitalize()}' is not in stock.")

# Low Stock Alert
with st.expander("Low Stock Alert"):
    threshold = st.number_input("Enter low stock threshold", min_value=1, step=1, value=5)
    low_stock_items = [item for item, details in stock.items() if details["quantity"] <= threshold]
    if low_stock_items:
        st.write("Low Stock Items:")
        for item in low_stock_items:
            st.write(f"- **{item.capitalize()}**: {stock[item]['quantity']} units remaining")
    else:
        st.write("No low stock items.")

# Expiry Alerts
with st.expander("Expiry Alerts"):
    days = st.number_input("Enter the number of days for expiry alerts", min_value=1, step=1, value=30)
    today = datetime.today().date()
    near_expiry_items = [
        (item, details)
        for item, details in stock.items()
        if (datetime.strptime(details["expiry_date"], "%Y-%m-%d").date() - today).days <= days
    ]
    if near_expiry_items:
        st.write("Items Near Expiry:")
        for item, details in near_expiry_items:
            expiry_date = datetime.strptime(details["expiry_date"], "%Y-%m-%d").date()
            days_left = (expiry_date - today).days
            st.write(f"- **{item.capitalize()}**: {details['quantity']} units, Expiry in {days_left} days ({expiry_date})")
    else:
        st.write("No items nearing expiry.")
# run this app from command line with following command
# streamlit run streamlit_dental_stock.py