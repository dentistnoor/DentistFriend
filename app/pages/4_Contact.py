import os
import smtplib
import streamlit as st
from dotenv import load_dotenv
from utils import show_footer

# Load environment variables from .env file
load_dotenv()


def contact_us():
    st.markdown("# Contact Us")
    st.divider()

    # Create form for contact submission
    with st.form("contact_form"):
        st.subheader("📬Let's get in touch!")
        col1, col2 = st.columns(2)

        # Split name and email inputs into two columns for better layout
        with col1:
            name = st.text_input("Your Name")

        with col2:
            email = st.text_input("Your Email")

        # Text area for detailed message
        message = st.text_area("Your Message", height=200, help="Feel free to ask any questions or share your feedback.")

        # Form submission button and validation
        if st.form_submit_button("📤 Submit", use_container_width=True):
            # Validate that all fields are filled
            if not name or not email or not message:
                st.warning("Please fill in all the fields", icon="⚠️")
            else:
                # Attempt to send email and show appropriate feedback
                result = send_mail(name, email, message)
                if "successfully" in result:
                    st.success("Thank you! We've received your message and will get back to you soon 🙂", icon="✅")
                else:
                    st.error("Error occurred while sending the email", icon="❌")


def send_mail(name, email, message):
    # Get email credentials from environment variables
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    # Prepare email content
    subject = "Denthic Feedback Team"
    body = f"Hello {name},\n\nThank you for reaching out to Denthic! Below is a copy of your message:\n\n{message}"
    full_message = f"Subject: {subject}\n\n{body}"

    try:
        # Connect to Gmail SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Enable encryption
        server.login(user=ADMIN_EMAIL, password=ADMIN_PASSWORD)

        # Send confirmation email to user
        server.sendmail(from_addr=ADMIN_EMAIL, to_addrs=email, msg=full_message)

        # Forward message to admin team
        server.sendmail(from_addr=ADMIN_EMAIL, to_addrs=["noordentist@gmail.com", "areebahmed0709@gmail.com"], msg=full_message)

        # Close the connection
        server.quit()
        return "Email sent successfully"
    except Exception as e:
        return str(e)


contact_us()
show_footer()
