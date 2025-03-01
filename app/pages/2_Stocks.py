import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime


db = firestore.client()

# ✅ Ensure user is logged in
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.error("You need to log in first.")
    st.stop()

doctor_email = st.session_state["doctor_email"]  # Get logged-in doctor's email
stock_collection = db.collection("doctors").document(doctor_email).collection("stock")

st.title("Dental Stock Management System")


# ✅ Function to load stock from Firestore
def load_stock():
    docs = stock_collection.stream()
    return {doc.id: doc.to_dict() for doc in docs}  # Convert Firestore docs to dictionary


# ✅ Function to save stock (Add or Update)
def save_stock(item, quantity, expiry_date):
    stock_collection.document(item).set({
        "quantity": quantity,
        "expiry_date": expiry_date
    }, merge=True)  # Merge ensures existing data isn't overwritten entirely


# ✅ Function to remove stock
def remove_stock(item, quantity_to_remove):
    doc_ref = stock_collection.document(item)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        current_quantity = data["quantity"]

        if quantity_to_remove == 0 or quantity_to_remove >= current_quantity:
            doc_ref.delete()  # Remove item completely
            st.success(f"'{item}' removed from stock.")
        else:
            doc_ref.update({"quantity": current_quantity - quantity_to_remove})  # Update quantity
            st.success(f"{quantity_to_remove} units of '{item}' removed.")


# ✅ Load stock from Firestore
stock = load_stock()

# ✅ Add Stock
with st.expander("Add Stock"):
    item = st.text_input("Enter the item name").strip().lower()
    quantity = st.number_input("Enter the quantity to add", min_value=0, step=1)
    expiry_date = st.date_input("Enter the expiry date")

    if st.button("Add Item"):
        if item:
            expiry_date_str = expiry_date.strftime("%Y-%m-%d")
            existing_item = stock.get(item, {"quantity": 0})  # Get current quantity or default 0
            total_quantity = existing_item["quantity"] + quantity
            save_stock(item, total_quantity, expiry_date_str)
            st.success(f"{quantity} units of '{item}' added with expiry date {expiry_date_str}.")
        else:
            st.error("Please enter an item name.")

# ✅ Remove Stock
with st.expander("Remove Stock"):
    item = st.text_input("Enter the item name to remove").strip().lower()
    if item in stock:
        st.write(f"Current stock: {stock[item]['quantity']} units")
        quantity_to_remove = st.number_input("Enter quantity to remove (or 0 to delete)", min_value=0, step=1)
        if st.button("Remove Item"):
            remove_stock(item, quantity_to_remove)
    elif st.button("Check Item to Remove"):
        st.error(f"'{item}' not found in stock.")

# ✅ View Stock
with st.expander("View Stock"):
    if stock:
        for item, details in stock.items():
            st.write(f"- **{item.capitalize()}**: {details['quantity']} units, Expiry: {details['expiry_date']}")
    else:
        st.write("Stock is empty.")

# ✅ Search Stock
with st.expander("Search Stock"):
    search_item = st.text_input("Enter the item name to search").strip().lower()
    if st.button("Search Item"):
        if search_item in stock:
            details = stock[search_item]
            st.success(
                f"'{search_item.capitalize()}' is in stock: {details['quantity']} units, Expiry: {details['expiry_date']}.")
        else:
            st.error(f"'{search_item.capitalize()}' is not in stock.")

# ✅ Low Stock Alert (Fixed)
with st.expander("Low Stock Alert"):
    threshold = st.number_input("Enter low stock threshold", min_value=1, step=1, value=5)

    low_stock_items = [
        (item, details["quantity"])
        for item, details in stock.items()
        if details["quantity"] <= threshold
    ]

    if low_stock_items:
        st.write("🚨 **Low Stock Items:**")
        for item, quantity in low_stock_items:
            st.write(f"- **{item.capitalize()}**: {quantity} units remaining")
    else:
        st.write("✅ No items are low in stock.")

# ✅ Expiry Alerts (Fixed)
with st.expander("Expiry Alerts"):
    days = st.number_input("Enter the number of days for expiry alerts", min_value=1, step=1, value=30)
    today = datetime.today().date()

    near_expiry_items = []
    for item, details in stock.items():
        expiry_date = datetime.strptime(details["expiry_date"], "%Y-%m-%d").date()
        days_until_expiry = (expiry_date - today).days

        if days_until_expiry <= days:
            near_expiry_items.append((item, details["quantity"], expiry_date, days_until_expiry))

    if near_expiry_items:
        st.write("⚠️ **Items Near Expiry:**")
        for item, quantity, expiry_date, days_left in near_expiry_items:
            st.write(f"- **{item.capitalize()}**: {quantity} units, Expiry in {days_left} days ({expiry_date})")
    else:
        st.write("✅ No items nearing expiry.")