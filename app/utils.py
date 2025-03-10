import os
import streamlit as st
from datetime import datetime
from fpdf import FPDF


def format_date(date_str):
    """Convert date string to formatted date (e.g., '2021-12-31' -> 'December 31, 2021')"""
    if isinstance(date_str, datetime):
        date_obj = date_str
    else:
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return date_str  # Return original if parsing fails

    return date_obj.strftime("%B %d, %Y")


def show_footer():
    """Display the footer with links to GitHub, License, and Documentation"""
    st.divider()
    st.markdown(
        """
        <footer style="text-align: center">
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
    """Generate a PDF document with treatment plan details"""
    pdf = FPDF(orientation="P", unit="mm", format="A4")  # Initialize PDF
    pdf.add_page()  # Add a new page to the PDF

    # Set up document title and date
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Dental Treatment Plan", 0, 1, "C")

    pdf.set_font("Arial", "", 10)
    current_date = datetime.now().strftime("%B %d, %Y")
    pdf.cell(0, 6, f"Date: {current_date}", 0, 1, "R")

    # Add patient information section
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Patient Information", 0, 1, "L")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    # Add patient and doctor details
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Treating Dentist: {doctor_name}", 0, 1)
    pdf.cell(0, 8, f"Patient Name: {patient_name}", 0, 1)
    pdf.cell(0, 8, f"Report ID: {datetime.now().strftime('%Y%m%d%H%M')}", 0, 1)

    # Add X-ray image if available
    if xray_image_path and os.path.exists(xray_image_path):
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Dental X-Ray", 0, 1, "L")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)

        try:
            current_y = pdf.get_y()
            if current_y > 200:  # Add new page if needed
                pdf.add_page()
                current_y = pdf.get_y()

            # Add X-ray image centered on page
            pdf.image(xray_image_path, x=50, y=current_y, w=100)
            pdf.ln(85)  # Add space after image
        except Exception as e:
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 10, f"Error loading X-ray image: {str(e)}", 0, 1)

    # Add treatment plan details section
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Treatment Plan Details", 0, 1, "L")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    # Display treatments or message if no treatments
    if not treatment_plan:
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, "No treatment procedures have been defined yet.", 0, 1)
    else:
        # Create treatment table with headers
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(230, 230, 230)

        # Define table structure and layout
        columns = ["Tooth", "Procedure", "Status", "Start Date", "End Date", "Cost"]
        col_widths = [20, 50, 25, 35, 35, 25]

        available_columns = []
        available_widths = []

        # Filter available columns based on treatment plan
        for i, col in enumerate(columns):
            if col in treatment_plan[0] or col == "Tooth" or col == "Procedure" or col == "Cost":
                available_columns.append(col)
                available_widths.append(col_widths[i])

        # Adjust column widths to fit page
        total_width = sum(available_widths)
        if total_width < 190:
            scale_factor = 190 / total_width
            available_widths = [w * scale_factor for w in available_widths]

        # Create table header row
        for i, col in enumerate(available_columns):
            pdf.cell(available_widths[i], 10, col, 1, 0, "C", True)
        pdf.ln()

        # Add treatment data rows
        pdf.set_font("Arial", "", 10)
        for item in treatment_plan:
            for i, col in enumerate(available_columns):
                value = str(item.get(col, ""))
                if col == "Cost" and value:
                    try:
                        value = f"{float(value):.2f}"
                    except ValueError:
                        pass
                pdf.cell(available_widths[i], 8, value, 1, 0, "L")
            pdf.ln()

    # Add cost summary section
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Cost Summary", 0, 1, "L")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Arial", "", 10)

    # Calculate final cost with discount and VAT
    final_cost = total_cost
    if isinstance(discount, (int, float)):
        final_cost -= discount
    if isinstance(vat, (int, float)):
        final_cost += vat

    # Define column layout for cost table
    col1_width = 100
    col2_width = 40

    # Create cost breakdown table
    pdf.cell(col1_width, 8, "Total Treatment Cost", 1, 0)
    pdf.cell(col2_width, 8, f"{float(total_cost):.2f}", 1, 1, "R")

    pdf.cell(col1_width, 8, "Discount", 1, 0)
    pdf.cell(col2_width, 8, f"{float(discount):.2f}", 1, 1, "R")

    pdf.cell(col1_width, 8, "VAT (15%)", 1, 0)
    pdf.cell(col2_width, 8, f"{float(vat):.2f}", 1, 1, "R")

    # Highlight final total with bold text
    pdf.set_font("Arial", "B", 10)
    pdf.cell(col1_width, 8, "Final Total", 1, 0)
    pdf.cell(col2_width, 8, f"{float(final_cost):.2f}", 1, 1, "R")

    # Add footer with generation details
    pdf.ln(10)
    pdf.set_font("Arial", "I", 8)
    generation_time = datetime.now()
    pdf.cell(0, 5, "Generated by Dental Flow", 0, 1, "C")
    pdf.cell(0, 5, f"This report was generated on {generation_time.strftime('%B %d, %Y')} at {generation_time.strftime('%H:%M')}.", 0, 1, "C")

    # Generate filename and output PDF
    filename = f"{patient_name.replace(' ', '_')}_treatment_plan.pdf"
    pdf.output(filename)
    return filename


def update_tooth(tooth_number):
    """Update tooth condition in session state."""
    selected_value = st.session_state[f"tooth_{tooth_number}"]
    st.session_state[f"tooth_condition_{tooth_number}"] = selected_value


def render_chart(dental_data, dental_chart=None):
    """Render interactive dental chart with colored teeth boxes."""
    if dental_chart is None:
        dental_chart = {}

    # Copy teeth_map to work with
    teeth_map = dental_data["teeth_map"].copy()

    # Merge existing dental chart data with teeth map
    for tooth in teeth_map:
        if tooth in dental_chart:
            teeth_map[tooth] = dental_chart[tooth]

    # Define color mapping for different health conditions
    condition_colors = {
        "Healthy": "#008000",  # Green
        "Decayed": "#9B2226",  # Dark Red
        "Missing": "#ADB5BD",  # Gray
        "Cavity": "#6C757D",   # Dark Gray
        "Implant": "#6C757D",  # Dark Gray
        "Extraction": "#774936", # Brown
        "Root Canal": "#FFA500", # Orange
        "Fractured": "#9B2226",  # Dark Red
        "Filled": "#007BFF",   # Blue
        "Discolored": "#FFD700", # Gold
        "Loose": "#FF7F50",    # Coral
        "Crowded": "#800080",  # Purple
        "Gingivitis": "#FF69B4", # Pink
        "Periodontitis": "#FF0000", # Red
        "Impacted": "#6C757D", # Dark Gray
        "Abrasion": "#FF4500",  # Orange Red
        "Anodontia": "#ADB5BD", # Gray
        "Attrition": "#FF8C00", # Dark Orange
        "Erosion": "#DAA520",   # Golden Rod
        "Hyperdontia": "#4B0082", # Indigo
        # Default for any other condition
        "default": "#008000"   # Green
    }

    # Track if chart has been modified
    chart_changed = False

    st.header("Dental Chart Assessment")

    # Container for the entire dental chart with border
    with st.container(border=True):
        # Process each row of teeth in the dental chart
        for teeth_row in dental_data["teeth_rows"]:
            # Create columns for each tooth in the row (8 teeth per row for standard dental chart)
            cols = st.columns(8)

            for i, tooth_number in enumerate(teeth_row):
                with cols[i]:
                    # Get current condition from the session state first (for immediate updates)
                    # or fall back to dental_chart, or default to "Healthy"
                    current_condition = st.session_state.get(f"tooth_condition_{tooth_number}", 
                                                          dental_chart.get(tooth_number, "Healthy"))

                    # Get the appropriate color for this tooth's condition
                    tooth_color = condition_colors.get(current_condition, condition_colors["default"])

                    # Create a visual box for the tooth with the appropriate color
                    st.markdown(
                        f"""
                        <div style="
                            background-color: {tooth_color};
                            color: white;
                            text-align: center;
                            padding: 10px 0;
                            border-radius: 5px;
                            font-weight: bold;
                            margin-bottom: 5px;
                        ">
                            {tooth_number}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Dropdown selector for tooth condition
                    default_index = 0
                    try:
                        default_index = dental_data["health_conditions"].index(current_condition)
                    except (ValueError, IndexError):
                        default_index = 0

                    selected_condition = st.selectbox(
                        f"Tooth {tooth_number}",
                        dental_data["health_conditions"],
                        index=default_index,
                        key=f"tooth_{tooth_number}",
                        label_visibility="collapsed",
                        on_change=update_tooth,
                        args=(tooth_number,)
                    )

                    # Store selected condition in session state for immediate visual updates
                    st.session_state[f"tooth_condition_{tooth_number}"] = selected_condition

                    # Track changes to dental chart
                    if tooth_number not in dental_chart or dental_chart[tooth_number] != selected_condition:
                        dental_chart[tooth_number] = selected_condition
                        chart_changed = True

                        # Auto-select unhealthy teeth for potential treatment
                        if selected_condition != "Healthy":
                            st.session_state.tooth_selected = tooth_number

    return dental_chart, chart_changed
