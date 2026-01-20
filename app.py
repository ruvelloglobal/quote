import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.graphics.shapes import Drawing, Line
import io
import os
from datetime import datetime
from PIL import Image

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Ruvello Export Suite", page_icon="💎", layout="wide")

st.title("💎 Ruvello Global: Ultimate Export Generator")
st.markdown("Generate **Client-Ready, Ultra-Luxury** Proforma Invoices.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Brand Assets")
    uploaded_logo = st.file_uploader("Upload Company Logo", type=["png", "jpg", "jpeg"])
    
    st.header("2. Invoice Meta")
    invoice_no = st.text_input("Invoice Number", value="PI-2026-001")
    invoice_date = st.date_input("Date", value=datetime.today())
    validity_days = st.number_input("Validity (Days)", value=15)

# --- MAIN INPUTS ---
st.subheader("3. Client & Logistics")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Bill To (Buyer):**")
    buyer_name = st.text_input("Buyer Company Name", placeholder="Village Arts")
    buyer_address = st.text_area("Buyer Address", placeholder="123 Street, Sydney, Australia", height=100)
    buyer_country = st.text_input("Destination Country", value="Australia")

with col2:
    st.markdown("**Logistics (Origin):**")
    pre_carriage = st.text_input("Pre-Carriage By", value="Road/Rail")
    place_receipt = st.text_input("Place of Receipt", value="Jaipur, India")
    port_loading = st.text_input("Port of Loading", value="Mundra Port, India")

with col3:
    st.markdown("**Logistics (Dest):**")
    port_discharge = st.text_input("Port of Discharge", placeholder="e.g. Sydney Port")
    final_dest = st.text_input("Final Destination", placeholder="e.g. Sydney")
    incoterm = st.selectbox("Incoterm", ["FOB", "CIF", "EXW", "DDP", "CFR"])

# --- PAYMENT & BANK ---
st.subheader("4. Financials")
p_col1, p_col2 = st.columns(2)

with p_col1:
    payment_terms_text = st.text_area(
        "Payment Terms", 
        value="50% Advance Payment to Confirm Order.\n50% Balance against Scan Copy of Bill of Lading (BL).",
        height=150
    )

with p_col2:
    bank_name = st.text_input("Bank Name", value="HDFC BANK LTD")
    bank_ac = st.text_input("Account Number", value="502000XXXXXXXX")
    bank_swift = st.text_input("SWIFT Code", value="HDFCCINBB")
    bank_ifsc = st.text_input("IFSC / IBAN", value="HDFC0000XXX")

# --- PRODUCTS ---
st.subheader("5. Order Specification")
default_data = [
    {"Product": "Black Galaxy Granite", "Finish": "Polished", "Size": "60 x 60 x 3 cm", "Quantity": 400.0, "Rate ($)": 35.00},
    {"Product": "Absolute Black Granite", "Finish": "Polished", "Size": "240up x 60up x 2 cm", "Quantity": 400.0, "Rate ($)": 38.50},
    {"Product": "Tan Brown Granite", "Finish": "Polished", "Size": "60 x 60 x 2 cm", "Quantity": 400.0, "Rate ($)": 29.00},
]
edited_data = st.data_editor(default_data, num_rows="dynamic", use_container_width=True)

# --- PDF ENGINE ---
def generate_luxury_pdf(logo, inv_no, inv_date, valid, b_name, b_addr, b_country, 
                        pre_car, receipt, p_load, p_disch, f_dest, inco, 
                        pay_terms, bank_n, bank_a, bank_s, bank_i, items):
    
    buffer = io.BytesIO()
    # Adjusted margins to ensure content fits without cramping
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=30, bottomMargin=30, leftMargin=35, rightMargin=35)
    elements = []
    styles = getSampleStyleSheet()

    # --- COLOR PALETTE ---
    GOLD = HexColor('#C5A059')   # Elegant Antique Gold
    BLACK = HexColor('#000000')  # Pure Black
    DARK_GREY = HexColor('#202020')
    LIGHT_GREY = HexColor('#FAFAFA')

    # --- STYLES ---
    # Custom "Letter Spaced" style for that Expensive look
    style_company = ParagraphStyle(
        'Company', parent=styles['Normal'], fontName='Times-Bold', fontSize=26, 
        textColor=BLACK, alignment=1, spaceAfter=2, letterSpacing=1.5
    )
    style_tagline = ParagraphStyle(
        'Tagline', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, 
        textColor=GOLD, alignment=1, letterSpacing=3, spaceBefore=4
    )
    style_label = ParagraphStyle(
        'Label', fontName='Helvetica-Bold', fontSize=7, textColor=GOLD, textTransform='uppercase'
    )
    style_content = ParagraphStyle(
        'Content', fontName='Times-Roman', fontSize=10, textColor=DARK_GREY, leading=12
    )
    style_content_bold = ParagraphStyle(
        'ContentBold', fontName='Times-Bold', fontSize=10, textColor=BLACK, leading=12
    )

    # --- 1. HEADER SECTION ---
    # We use a Table for the logo/title to prevent overlapping
    header_elements = []
    
    if logo:
        # Resize logo to be manageable
        img = RLImage(logo, width=2.0*inch, height=1.5*inch, kind='proportional')
        header_elements.append(img)
    
    header_elements.append(Spacer(1, 15)) # Force gap between logo and text
    header_elements.append(Paragraph("RUVELLO GLOBAL LLP", style_company))
    header_elements.append(Paragraph("EXQUISITE NATURAL STONES & SURFACES", style_tagline))
    
    # Wrap header in a table to ensure vertical stability
    t_header = Table([[e] for e in header_elements], colWidths=[500])
    t_header.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(t_header)
    
    # The "Double Gold" Divider Line
    elements.append(Spacer(1, 15))
    d = Drawing(500, 8)
    d.add(Line(0, 4, 540, 4, strokeColor=GOLD, strokeWidth=0.5))
    d.add(Line(0, 1, 540, 1, strokeColor=GOLD, strokeWidth=1.5))
    elements.append(d)
    elements.append(Spacer(1, 25))

    # --- 2. EXPORTER & BUYER GRID (UN Layout) ---
    
    # Exporter Block
    exporter_text = f"""
    <b>RUVELLO GLOBAL LLP</b><br/>
    1305, Uniyaro Ka Rasta, Chandpol Bazar,<br/>
    Jaipur, Rajasthan, INDIA - 302001<br/>
    GSTIN: 08ABMFR3949N1ZA | LLPIN: ACS-0204<br/>
    Email: Rahul@ruvello.com | +91 9636648894
    """

    # Invoice Meta Block
    invoice_text = f"""
    <b>NO:</b> {inv_no}<br/>
    <b>DATE:</b> {inv_date.strftime('%d-%b-%Y')}<br/>
    <b>VALID:</b> {valid} Days<br/>
    <b>REF:</b> EX/RV/2026
    """

    # Buyer Block
    buyer_text = f"""
    <b>{b_name}</b><br/>
    {b_addr.replace(chr(10), '<br/>')}<br/>
    <b>{b_country}</b>
    """

    # Logistics Block
    logistics_text = f"""
    <b>Pre-Carriage:</b> {pre_car}<br/>
    <b>Receipt:</b> {receipt}<br/>
    <b>Loading:</b> {p_load}<br/>
    <b>Discharge:</b> {p_disch}<br/>
    <b>Final Dest:</b> {f_dest}<br/>
    <b>Terms:</b> {inco} {p_disch}
    """

    # Creating the 2x2 Grid with labels
    data_grid = [
        [Paragraph("EXPORTER", style_label), Paragraph("INVOICE DETAILS", style_label)],
        [Paragraph(exporter_text, style_content), Paragraph(invoice_text, style_content)],
        [Paragraph("CONSIGNEE (BUYER)", style_label), Paragraph("LOGISTICS & TERMS", style_label)],
        [Paragraph(buyer_text, style_content), Paragraph(logistics_text, style_content)]
    ]

    t_grid = Table(data_grid, colWidths=[270, 270])
    t_grid.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 6),
        # Subtle horizontal dividers only (Luxury look)
        ('LINEBELOW', (0,1), (-1,1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0,2), (-1,2), 15), # Add space before Buyer row
    ]))
    elements.append(t_grid)
    elements.append(Spacer(1, 30))

    # --- 3. PRODUCT TABLE ---
    elements.append(Paragraph("DESCRIPTION OF GOODS", style_label))
    elements.append(Spacer(1, 5))

    # Headers
    headers = ["Product", "Size", "Qty (sq.m)", "Rate", "Amount"]
    table_data = [[Paragraph(h, style_tagline) for h in headers]] # Using Tagline style for Gold Header Text
    
    total_qty = 0
    total_amt = 0

    for item in items:
        # Check for valid numbers to prevent crashes
        try:
            q = float(item["Quantity"])
            r = float(item["Rate ($)"])
        except:
            q, r = 0.0, 0.0
            
        amt = q * r
        total_qty += q
        total_amt += amt
        
        row = [
            Paragraph(f"<b>{item['Product']}</b><br/><font size=8>Finish: {item['Finish']}</font>", style_content),
            Paragraph(item['Size'], style_content),
            Paragraph(f"{q:,.2f}", style_content),
            Paragraph(f"${r:,.2f}", style_content),
            Paragraph(f"${amt:,.2f}", style_content_bold),
        ]
        table_data.append(row)

    # Total Row
    table_data.append([
        Paragraph("TOTAL (USD):", style_content_bold), 
        "", 
        Paragraph(f"<b>{total_qty:,.2f}</b>", style_content_bold),
        "", 
        Paragraph(f"<b>${total_amt:,.2f}</b>", style_content_bold)
    ])

    t_prod = Table(table_data, colWidths=[180, 100, 80, 80, 100])
    t_prod.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK), # Black Header
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TEXTCOLOR', (0,0), (-1,0), GOLD),   # Gold Text in Header
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (1,1), (-2,-1), [colors.white, LIGHT_GREY]), # Zebra stripes
        ('ALIGN', (2,1), (-1,-1), 'RIGHT'),   # Numbers Right Aligned
        ('LINEABOVE', (0,-1), (-1,-1), 1, BLACK), # Line above Total
        ('BACKGROUND', (0,-1), (-1,-1), LIGHT_GREY), # Total Row BG
    ]))
    elements.append(t_prod)
    elements.append(Spacer(1, 30))

    # --- 4. TERMS & BANK ---
    
    # Left Side: Payment Terms
    terms_content = f"""
    {pay_terms.replace(chr(10), '<br/>')}<br/><br/>
    <font size=8 color='grey'>DECLARATION: We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct. Country of Origin: INDIA.</font>
    """
    
    # Right Side: Bank
    bank_content = f"""
    <b>Bank:</b> {bank_n}<br/>
    <b>Ac/Name:</b> RUVELLO GLOBAL LLP<br/>
    <b>Ac/No:</b> {bank_a}<br/>
    <b>SWIFT:</b> {bank_s}<br/>
    <b>IFSC:</b> {bank_i}
    """

    data_footer = [
        [Paragraph("PAYMENT TERMS", style_label), Paragraph("BANKING INSTRUCTIONS", style_label)],
        [Paragraph(terms_content, style_content), Paragraph(bank_content, style_content)]
    ]
    
    t_foot = Table(data_footer, colWidths=[270, 270])
    t_foot.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBEFORE', (1,0), (1,1), 1, colors.lightgrey), # Vertical divider
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t_foot)
    elements.append(Spacer(1, 40))

    # --- 5. SIGNATURE ---
    sig_content = f"""
    <b>For RUVELLO GLOBAL LLP</b><br/><br/><br/><br/>
    Authorized Signatory
    """
    t_sig = Table([[ "", Paragraph(sig_content, style_content) ]], colWidths=[350, 190])
    t_sig.setStyle(TableStyle([('ALIGN', (1,0), (1,0), 'CENTER')]))
    elements.append(t_sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- GENERATE BUTTON ---
st.markdown("---")
if st.button("✨ Generate Invoice", type="primary"):
    pdf_bytes = generate_luxury_pdf(
        uploaded_logo, invoice_no, invoice_date, validity_days, 
        buyer_name, buyer_address, buyer_country,
        pre_carriage, place_receipt, port_loading, port_discharge, final_dest, incoterm,
        payment_terms_text, bank_name, bank_ac, bank_swift, bank_ifsc,
        edited_data
    )
    st.success("Invoice Ready!")
    st.download_button("Download PDF", data=pdf_bytes, file_name=f"PI_{invoice_no}.pdf", mime="application/pdf")
