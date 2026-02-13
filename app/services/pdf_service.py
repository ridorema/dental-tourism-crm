from pathlib import Path

from flask import current_app


def generate_quote_pdf(quote, lead, clinic):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    output_dir = Path(current_app.root_path) / "generated_pdfs"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"quote_{quote.id}.pdf"
    pdf = canvas.Canvas(str(output_path), pagesize=A4)

    y = 800
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(60, y, f"{clinic.name} - Quote #{quote.id}")

    y -= 40
    pdf.setFont("Helvetica", 11)
    full_name = f"{lead.first_name} {lead.last_name}" if lead else "-"
    pdf.drawString(60, y, f"Patient/Lead: {full_name}")
    y -= 20
    pdf.drawString(60, y, f"Currency: {quote.currency}")
    y -= 20
    pdf.drawString(60, y, f"Total: {quote.total}")
    y -= 20
    pdf.drawString(60, y, f"Status: {quote.status}")

    y -= 40
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(60, y, "Treatment Items")
    y -= 20
    pdf.setFont("Helvetica", 10)

    items = []
    if quote.treatment_plan and quote.treatment_plan.items:
        items = quote.treatment_plan.items

    if not items:
        pdf.drawString(60, y, "-")
    else:
        for item in items:
            label = item.get("label", "Item")
            quantity = item.get("quantity", 1)
            unit_price = item.get("unit_price", 0)
            pdf.drawString(60, y, f"- {label} | Qty: {quantity} | Unit: {unit_price}")
            y -= 16
            if y < 80:
                pdf.showPage()
                y = 800
                pdf.setFont("Helvetica", 10)

    pdf.showPage()
    pdf.save()
    return f"generated_pdfs/{output_path.name}"
