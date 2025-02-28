from fpdf import FPDF

def generate_pdf(patient_name, treatment_plan, total_cost, xray_image_path=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Patient Name: {patient_name}", ln=True)
    pdf.cell(200, 10, txt="Treatment Plan", ln=True)
    pdf.set_font("Arial", size=10)
    col_widths = [20, 50, 20]
    pdf.cell(col_widths[0], 10, "Tooth", border=1)
    pdf.cell(col_widths[1], 10, "Procedure", border=1)
    pdf.cell(col_widths[2], 10, "Cost", border=1)
    pdf.ln()

    for item in treatment_plan:
        pdf.cell(col_widths[0], 10, item['Tooth'], border=1)
        pdf.cell(col_widths[1], 10, item['Procedure'], border=1)
        pdf.cell(col_widths[2], 10, f"${item['Cost']}", border=1)
        pdf.ln()

    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Total Estimated Cost: ${total_cost}", ln=True)

    if xray_image_path:
        pdf.ln(10)
        pdf.cell(200, 10, txt="X-Ray Image:", ln=True)
        pdf.image(xray_image_path, x=10, y=pdf.get_y(), w=100)

    pdf_output = f"{patient_name}_treatment_plan.pdf"
    pdf.output(pdf_output)
    return pdf_output