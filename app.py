import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Line
import io
import os
from datetime import datetime
from PIL import Image

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Ruvello Export PI", page_icon="💎", layout="wide")

st.title("💎 Ruvello Global: Export Proforma Invoice")
st.markdown("Generate a **Client-Ready, Luxury Export Invoice** with full logistics details.")

# --- SIDEBAR: ASSETS & SETTINGS ---
with st.sidebar:
    st.header("1. Company Assets")
    uploaded_logo = st.file_uploader("Upload Company Logo", type=["png", "jpg", "jpeg"])
    
    st.header("2. Invoice Meta")
    invoice_no = st.text_input("Invoice Number", value="PI-2026-001")
    invoice_date = st.date_input("Date", value=datetime.today())
    validity_days = st.number_input("Validity (Days)", value=15)

# --- MAIN FORM: EXPORT DETAILS ---
st.subheader("3. Shipment & Buyer Details")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Bill To (Buyer):**")
    buyer_name = st.text_input("Buyer Company Name", placeholder="Village Arts")
    buyer_address = st.text_area("Buyer Address", placeholder="123 Street, Sydney, Australia", height=100)
    buyer_country = st.text_input("Destination Country", value="Australia")

with col2:
    st.markdown("**Logistics (Part 1):**")
    pre_carriage = st.text_input("Pre-Carriage By", value="Road/Rail")
    place_receipt = st.text_input("Place of Receipt", value="Jaipur, India")
    port_loading = st.text_input("Port of Loading", value="Mundra Port, India")

with col3:
    st.markdown("**Logistics (Part 2):**")
    port_discharge = st.text_input("Port of Discharge", placeholder="e.g. Sydney Port")
    final_dest = st.text_input("Final Destination", placeholder="e.g. Sydney")
    incoterm = st.selectbox("Incoterm", ["CIF", "FOB", "EXW", "DDP", "CFR"])

# --- PAYMENT TERMS (Editable) ---
st.subheader("4. Payment & Bank")
pay_col1, pay_col2 = st.columns(2)

with pay_col1:
    payment_terms_text = st.text_area(
        "Payment Terms (Full Text)", 
        value="30% Advance Payment to Confirm Order.\n70% Balance against Scan Copy of Bill of Lading (BL).",
        height=150
    )

with pay_col2:
    st.markdown("**Bank Details (For Invoice):**")
    bank_name = st.text_input("Bank Name", value="HDFC BANK LTD")
    bank_ac = st.text_input("Account Number", value="502000XXXXXXXX")
    bank_swift = st.text_input("SWIFT Code", value="HDFCCINBB")
    bank_ifsc = st.text_input("IFSC / IBAN", value="HDFC0000XXX")

# --- PRODUCT COLLECTION ---
st.subheader("5. Product Collection")
st.info("Edit your product list below. Click '+' to add rows.")

default_data = [
    {"Product": "Black Galaxy Granite", "Finish": "Polished", "Size": "60 x 60 x 3 cm", "Quantity (sq.m)": 400, "Rate ($)": 35.00},
    {"Product": "Absolute Black Granite", "Finish": "Polished", "Size": "240up x 60up x 2 cm", "Quantity (sq.m)": 0, "Rate ($)": 38.50},
    {"Product": "Tan Brown Granite", "Finish": "Polished", "Size": "60 x 60 x 2 cm", "Quantity (sq.m)": 0, "Rate ($)": 29.00},
]

edited_data = st.data_editor(default_data, num_rows="dynamic", use_container_width=True)

# --- PDF GENERATION ENGINE ---
def generate_export_pdf(logo, inv_no, inv_date, valid, b_name, b_addr, b_country, 
                        pre_car, receipt, p_load, p_disch, f_dest, inco, 
                        pay_terms, bank_n, bank_a, bank_s, bank_i, items):
    
    buffer = io.BytesIO()
    # Margins optimized for Export Document (Standard A4/Letter)
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=20, bottomMargin=20, leftMargin=30, rightMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # --- LUXURY STYLING CONSTANTS ---
    GOLD = HexColor('#D4AF37')
    BLACK = HexColor('#000000')
    GREY = HexColor('#303030')
    LIGHT_BG = HexColor('#FAFAFA')
    
    # Font Styles
    style_header = ParagraphStyle('Header', fontName='Times-Bold', fontSize=22, textColor=BLACK, alignment=1)
    style_sub = ParagraphStyle('Sub', fontName='Helvetica-Bold', fontSize=8, textColor=GOLD, alignment=1, letterSpacing=2)
    style_label = ParagraphStyle('Label', fontName='Helvetica-Bold', fontSize=7, textColor=GREY)
    style_text = ParagraphStyle('Text', fontName='Times-Roman', fontSize=9, textColor=BLACK, leading=10)
    style_text_bold = ParagraphStyle('TextBold', fontName='Times-Bold', fontSize=9, textColor=BLACK, leading=10)

    # 1. HEADER LOGO
    if logo:
        img = RLImage(logo, width=2.2*inch, height=1.5*inch, kind='proportional')
        img.hAlign = 'CENTER'
        elements.append(img)
    
    elements.append(Paragraph("RUVELLO GLOBAL LLP", style_header))
    elements.append(Paragraph("EXQUISITE NATURAL STONES & SURFACES", style_sub))
    elements.append(Spacer(1, 10))

    # Gold Divider
    d = Drawing(500, 5)
    d.add(Line(0, 0, 550, 0, strokeColor=GOLD, strokeWidth=1))
    elements.append(d)
    elements.append(Spacer(1, 15))

    # 2. EXPORT LOGISTICS GRID (UN Layout Style)
    # Row 1: Exporter (Left) vs Invoice Info (Right)
    
    exporter_info = """
    <b>EXPORTER:</b><br/>
    <b>RUVELLO GLOBAL LLP</b><br/>
    1305, Uniyaro Ka Rasta, Chandpol Bazar,<br/>
    Jaipur, Rajasthan, INDIA - 302001<br/>
    GSTIN: 08ABMFR3949N1ZA | LLPIN: ACS-0204<br/>
    Email: Rahul@ruvello.com | +91 9636648894
    """
    
    invoice_meta = f"""
    <b>PROFORMA INVOICE NO:</b> {inv_no}<br/>
    <b>DATE:</b> {inv_date.strftime('%d-%b-%Y')}<br/>
    <b>VALIDITY:</b> {valid} Days<br/>
    <b>EXPORTER REF:</b> EX/RV/2026
    """

    # Row 2: Consignee (Left) vs Logistics (Right)
    consignee_info = f"""
    <b>CONSIGNEE (BUYER):</b><br/>
    <b>{b_name}</b><br/>
    {b_addr.replace(chr(10), '<br/>')}<br/>
    <b>{b_country}</b>
    """

    logistics_info = f"""
    <b>PRE-CARRIAGE BY:</b> {pre_car}<br/>
    <b>PLACE OF RECEIPT:</b> {receipt}<br/>
    <b>PORT OF LOADING:</b> {p_load}<br/>
    <b>PORT OF DISCHARGE:</b> {p_disch}<br/>
    <b>FINAL DESTINATION:</b> {f_dest}<br/>
    <b>TERMS:</b> {inco} {p_disch}
    """

    # Create the Grid Table
    grid_data = [
        [Paragraph(exporter_info, style_text), Paragraph(invoice_meta, style_text)],
        [Paragraph(consignee_info, style_text), Paragraph(logistics_info, style_text)]
    ]
    
    t_grid = Table(grid_data, colWidths=[275, 275])
    t_grid.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey), # Subtle grid like export docs
        ('BACKGROUND', (0,0), (0,0), LIGHT_BG), # Highlight Exporter
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_grid)
    elements.append(Spacer(1, 20))

    # 3. PRODUCT TABLE
    elements.append(Paragraph("DESCRIPTION OF GOODS", style_text_bold))
    elements.append(Spacer(1, 5))

    # Filter out empty rows (quantity 0)
    active_items = [i for i in items if i["Quantity (sq.m)"] > 0]
    
    # Table Header
    headers = ["Product Name", "Size", "Quantity", "Rate", "Amount"]
    table_data = [[Paragraph(h, style_sub) for h in headers]]
    
    total_amount = 0
    
    for item in active_items:
        qty = float(item["Quantity (sq.m)"])
        rate = float(item["Rate ($)"])
        amt = qty * rate
        total_amount += amt
        
        row = [
            Paragraph(f"<b>{item['Product']}</b><br/>Finish: {item['Finish']}", style_text),
            Paragraph(item['Size'], style_text),
            Paragraph(f"{qty} sq.m", style_text),
            Paragraph(f"${rate:.2f}", style_text),
            Paragraph(f"${amt:,.2f}", style_text_bold),
        ]
        table_data.append(row)

    # Total Row
    table_data.append([
        "", "", "", 
        Paragraph("<b>TOTAL (USD):</b>", style_text_bold), 
        Paragraph(f"<b>${total_amount:,.2f}</b>", style_text_bold)
    ])

    t_prod = Table(table_data, colWidths=[200, 100, 80, 80, 90])
    t_prod.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK), # Header Black
        ('TEXTCOLOR', (0,0), (-1,0), GOLD),   # Header Gold
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, GOLD),
        ('ALIGN', (2,1), (-1,-1), 'RIGHT'),   # Numbers align right
        ('BACKGROUND', (-1,-1), (-1,-1), LIGHT_BG), # Total cell bg
    ]))
    elements.append(t_prod)
    elements.append(Spacer(1, 20))

    # 4. TERMS & BANK (Side by Side)
    # Left: Terms
    terms_html = f"""
    <font size=10><b>PAYMENT TERMS:</b></font><br/>
    {pay_terms.replace(chr(10), '<br/>')}<br/><br/>
    <font size=10><b>DECLARATION:</b></font><br/>
    We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.
    Country of Origin: INDIA.
    """
    
    # Right: Bank
    bank_html = f"""
    <font size=10 color='#D4AF37'><b>BANKING INSTRUCTIONS:</b></font><br/>
    <b>Bank Name:</b> {bank_n}<br/>
    <b>Account Name:</b> RUVELLO GLOBAL LLP<br/>
    <b>Account No:</b> {bank_a}<br/>
    <b>SWIFT/BIC:</b> {bank_s}<br/>
    <b>IFSC/IBAN:</b> {bank_i}<br/>
    <i>Please mention Invoice No. in transfer remarks.</i>
    """
    
    term_data = [[Paragraph(terms_html, style_text), Paragraph(bank_html, style_text)]]
    t_terms = Table(term_data, colWidths=[275, 275])
    t_terms.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBEFORE', (1,0), (1,0), 1, colors.lightgrey), # Divider line
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t_terms)
    elements.append(Spacer(1, 40))

    # 5. SIGNATURE
    sig_data = [["", Paragraph("<b>For RUVELLO GLOBAL LLP</b><br/><br/><br/><br/>Authorized Signatory", style_text)]]
    t_sig = Table(sig_data, colWidths=[350, 200])
    t_sig.setStyle(TableStyle([('ALIGN', (1,0), (1,0), 'CENTER')]))
    elements.append(t_sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- GENERATE BUTTON ---
st.markdown("---")
if st.button("Generate Export Invoice", type="primary"):
    if not buyer_name:
        st.error("Please enter Buyer Name")
    else:
        pdf_file = generate_export_pdf(
            uploaded_logo, invoice_no, invoice_date, validity_days, 
            buyer_name, buyer_address, buyer_country,
            pre_carriage, place_receipt, port_loading, port_discharge, final_dest, incoterm,
            payment_terms_text, bank_name, bank_ac, bank_swift, bank_ifsc,
            edited_data
        )
        
        st.success("✅ Export Invoice Generated!")
        st.download_button(
            label="Download Invoice PDF",
            data=pdf_file,
            file_name=f"PI_{invoice_no}.pdf",
            mime="application/pdf"
        )
