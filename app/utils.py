import os
import streamlit as st
from datetime import datetime
from fpdf import FPDF


def show_footer():
    st.divider()
    st.markdown(
        """
        <footer style='text-align: center'>
            🔓 FOSS (Free and Open Source Software)
            <br>
            <a href="https://github.com/dent-noor/DentalFlow">GitHub</a> • 
            <a href="https://github.com/dent-noor/DentalFlow/blob/main/LICENSE">License</a> • 
            <a href="https://github.com/dent-noor/DentalFlow/blob/main/README.md">Documentation</a>
        </footer>
        """,
        unsafe_allow_html=True
    )


def generate_pdf(doctor_name, patient_name, treatment_plan, discount=0, vat=0, total_cost=0, xray_image_path=None):
    pdf = FPDF(orientation='P', unit='mm', format='A4')  # Initialize PDF
    pdf.add_page()  # Add a new page to the PDF

    pdf.set_font("Arial", "B", 16)  # Set font for title
    pdf.cell(0, 10, "Dental Treatment Plan", 0, 1, 'C')  # Add title

    pdf.set_font("Arial", "", 10)  # Set font for date
    current_date = datetime.now().strftime("%B %d, %Y")
    pdf.cell(0, 6, f"Date: {current_date}", 0, 1, 'R')  # Add current date

    pdf.ln(5)  # Add space
    pdf.set_font("Arial", "B", 12)  # Set font for section title
    pdf.cell(0, 10, "Patient Information", 0, 1, 'L')  # Section title
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Underline section title
    pdf.ln(2)  # Add space

    # Add patient and doctor information
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Treating Dentist: {doctor_name}", 0, 1)
    pdf.cell(0, 8, f"Patient Name: {patient_name}", 0, 1)
    pdf.cell(0, 8, f"Report ID: {datetime.now().strftime('%Y%m%d%H%M')}", 0, 1)

    pdf.ln(5)  # Add space
    pdf.set_font("Arial", "B", 12)  # Set font for treatment plan title
    pdf.cell(0, 10, "Treatment Plan Details", 0, 1, 'L')  # Treatment plan section title
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Underline treatment plan title
    pdf.ln(2)  # Add space

    # Check if treatment plan exists
    if not treatment_plan:
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, "No treatment procedures have been defined yet.", 0, 1)
    else:
        pdf.set_font("Arial", "B", 10)  # Set font for table headers
        pdf.set_fill_color(230, 230, 230)  # Set fill color for headers

        # Define table columns and widths
        columns = ['Tooth', 'Procedure', 'Cost', 'Status', 'Start Date', 'End Date']
        col_widths = [20, 50, 25, 25, 35, 35]

        available_columns = []
        available_widths = []

        # Filter available columns based on treatment plan
        for i, col in enumerate(columns):
            if col in treatment_plan[0] or col == 'Tooth' or col == 'Procedure' or col == 'Cost':
                available_columns.append(col)
                available_widths.append(col_widths[i])

        total_width = sum(available_widths)
        # Scale columns if the total width is too small
        if total_width < 190:
            scale_factor = 190 / total_width
            available_widths = [w * scale_factor for w in available_widths]

        # Add table headers
        for i, col in enumerate(available_columns):
            pdf.cell(available_widths[i], 10, col, 1, 0, 'C', True)
        pdf.ln()  # Move to next line

        pdf.set_font("Arial", "", 10)  # Set font for table content
        # Add rows to the table
        for item in treatment_plan:
            for i, col in enumerate(available_columns):
                value = str(item.get(col, ""))
                if col == 'Cost' and value:
                    try:
                        value = f"SAR {float(value):.2f}"  # Format cost as currency
                    except ValueError:
                        pass
                pdf.cell(available_widths[i], 8, value, 1, 0, 'L')
            pdf.ln()  # Move to next line

    pdf.ln(5)  # Add space
    pdf.set_font("Arial", "B", 12)  # Set font for cost summary title
    pdf.cell(0, 10, "Cost Summary", 0, 1, 'L')  # Cost summary section title
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Underline cost summary title
    pdf.ln(2)  # Add space

    pdf.set_font("Arial", "", 10)  # Set font for cost details

    # Calculate final cost with discount and VAT
    final_cost = total_cost
    if isinstance(discount, (int, float)):
        final_cost -= discount
    if isinstance(vat, (int, float)):
        final_cost += vat

    col1_width = 100  # Set column width for labels
    col2_width = 40  # Set column width for values

    # Add cost breakdown
    pdf.cell(col1_width, 8, "Treatment Total:", 1, 0)
    pdf.cell(col2_width, 8, f"SAR {float(total_cost):.2f}", 1, 1, 'R')

    pdf.cell(col1_width, 8, "Discount:", 1, 0)
    pdf.cell(col2_width, 8, f"SAR {float(discount):.2f}", 1, 1, 'R')

    pdf.cell(col1_width, 8, "VAT (15%):", 1, 0)
    pdf.cell(col2_width, 8, f"SAR {float(vat):.2f}", 1, 1, 'R')

    pdf.set_font("Arial", "B", 10)  # Set bold font for final total
    pdf.cell(col1_width, 8, "Final Total:", 1, 0)
    pdf.cell(col2_width, 8, f"SAR {float(final_cost):.2f}", 1, 1, 'R')

    # Check if X-ray image exists and add it to the PDF
    if xray_image_path and os.path.exists(xray_image_path):
        pdf.ln(5)  # Add space
        pdf.set_font("Arial", "B", 12)  # Set font for X-ray title
        pdf.cell(0, 10, "Dental X-Ray", 0, 1, 'L')  # X-ray section title
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Underline X-ray section title
        pdf.ln(2)  # Add space

        try:
            current_y = pdf.get_y()
            if current_y > 200:  # Add new page if needed
                pdf.add_page()
                current_y = pdf.get_y()

            pdf.image(xray_image_path, x=50, y=current_y, w=100)  # Add X-ray image
            pdf.ln(85)  # Add space after image
        except Exception as e:
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 10, f"Error loading X-ray image: {str(e)}", 0, 1)

    pdf.ln(10)  # Add space
    pdf.set_font("Arial", "I", 8)  # Set font for footer
    generation_time = datetime.now()
    pdf.cell(0, 5, "Generated by Dental Flow", 0, 1, 'C')
    pdf.cell(0, 5, f"This report was generated on {generation_time.strftime('%B %d, %Y')} at {generation_time.strftime('%H:%M')}.", 0, 1, 'C')

    # Generate filename based on patient name and timestamp
    filename = f"{patient_name.replace(' ', '_')}_treatment_plan.pdf"

    pdf.output(filename)  # Output the PDF
    return filename  # Return the filename
