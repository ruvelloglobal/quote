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
st.set_page_config(page_title="Ruvello Luxury Invoice", page_icon="💎", layout="wide")

st.title("💎 Ruvello Global: Luxury Invoice Generator")
st.markdown("Fill in the details below to generate an **Ultra-Luxury PDF** instantly.")

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("1. Company Assets")
    uploaded_logo = st.file_uploader("Upload Company Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
    
    st.header("2. Invoice Settings")
    invoice_no = st.text_input("Invoice Number", value="PI-2026-001")
    validity_days = st.number_input("Validity (Days)", value=15)

# --- MAIN FORM ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("3. Buyer Details")
    buyer_name = st.text_input("Buyer Company Name", placeholder="e.g. Village Arts")
    buyer_country = st.text_input("Buyer Country / Address", placeholder="e.g. Australia")

with col2:
    st.subheader("4. Shipping Terms")
    transit_time = st.text_input("Transit Time", value="35 - 40 Days")
    incoterm = st.selectbox("Incoterm", ["CIF (Cost, Insurance, Freight)", "FOB (Free On Board)", "EXW (Ex-Works)"])

st.subheader("5. Product Collection")
st.info("Edit the prices and details below. You can add more rows if needed.")

# Default Data for the table
default_data = [
    {"Product": "Black Galaxy", "Finish": "Polished", "Size": "60 x 60 cm", "Thickness": "3 cm", "Price (CIF)": "$35.00 / m2"},
    {"Product": "Absolute Black", "Finish": "Polished", "Size": "60 x 60 cm", "Thickness": "3 cm", "Price (CIF)": "$38.50 / m2"},
    {"Product": "Tan Brown", "Finish": "Polished", "Size": "60 x 60 cm", "Thickness": "3 cm", "Price (CIF)": "$29.00 / m2"},
    {"Product": "Steel Grey", "Finish": "Polished", "Size": "60 x 60 cm", "Thickness": "3 cm", "Price (CIF)": "$31.25 / m2"},
    {"Product": "Viscon White", "Finish": "Polished", "Size": "60 x 60 cm", "Thickness": "3 cm", "Price (CIF)": "$33.00 / m2"},
]

# Editable Table
edited_data = st.data_editor(default_data, num_rows="dynamic", use_container_width=True)

# --- PDF GENERATION ENGINE ---
def generate_pdf(logo_file, buyer_name, buyer_country, items, inv_no, valid_days, transit, term):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=30, bottomMargin=30, leftMargin=40, rightMargin=40)
    elements = []
    styles = getSampleStyleSheet()

    # Colors
    lux_gold = HexColor('#D4AF37')
    lux_black = HexColor('#000000')
    lux_grey = HexColor('#404040')
    lux_light_grey = HexColor('#FAFAFA')

    # 1. Header & Logo
    if logo_file is not None:
        # Save uploaded file temporarily to process with ReportLab
        img = RLImage(logo_file, width=2.0*inch, height=1.6*inch, kind='proportional')
        img.hAlign = 'CENTER'
        elements.append(img)
        elements.append(Spacer(1, 10))

    # Company Branding
    style_company = ParagraphStyle('Company', parent=styles['Heading1'], fontSize=24, textColor=lux_black, alignment=1, spaceAfter=5, fontName='Times-Bold')
    style_tagline = ParagraphStyle('Tagline', parent=styles['Normal'], fontSize=9, textColor=lux_gold, alignment=1, spaceAfter=15, fontName='Helvetica-Bold', letterSpacing=3)

    elements.append(Paragraph("RUVELLO GLOBAL LLP", style_company))
    elements.append(Paragraph("EXQUISITE NATURAL STONES & SURFACES", style_tagline))

    # Gold Divider
    d = Drawing(500, 10)
    d.add(Line(0, 5, 550, 5, strokeColor=lux_gold, strokeWidth=0.5))
    d.add(Line(0, 2, 550, 2, strokeColor=lux_gold, strokeWidth=1.5))
    elements.append(d)
    elements.append(Spacer(1, 15))

    # 2. Buyer & Invoice Info
    current_date = datetime.now().strftime("%B %d, %Y")
    inv_info = f"<b>DATE:</b> {current_date}<br/><b>PROFORMA NO:</b> {inv_no}<br/><b>VALIDITY:</b> {valid_days} Days"
    buyer_info_text = f"<font color='#D4AF37'><b>BILL TO:</b></font><br/><b>{buyer_name.upper()}</b><br/>{buyer_country}"
    
    style_buyer = ParagraphStyle('Buyer', fontSize=10, textColor=lux_grey, leading=14, fontName='Times-Roman')
    buyer_table = Table([[Paragraph(inv_info, style_buyer), Paragraph(buyer_info_text, style_buyer)]], colWidths=[260, 260])
    buyer_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
    elements.append(buyer_table)
    elements.append(Spacer(1, 20))

    # 3. Items Table
    elements.append(Paragraph("PREMIUM GRANITE SELECTION", ParagraphStyle('Title', fontSize=13, textColor=lux_black, alignment=1, spaceAfter=10, fontName='Times-Bold')))
    
    # Headers
    header_style = ParagraphStyle('Header', fontSize=9, textColor=lux_gold, alignment=1, fontName='Times-Bold')
    row_style_name = ParagraphStyle('RowName', fontSize=10, textColor=lux_black, alignment=0, fontName='Times-Bold')
    row_style_norm = ParagraphStyle('RowNorm', fontSize=10, textColor=lux_grey, alignment=1, fontName='Times-Roman')
    row_style_price = ParagraphStyle('RowPrice', fontSize=11, textColor=lux_black, alignment=1, fontName='Times-Bold')

    data = [[Paragraph(k.upper(), header_style) for k in items[0].keys()]]
    for item in items:
        row = [
            Paragraph(str(item["Product"]), row_style_name),
            Paragraph(str(item["Finish"]), row_style_norm),
            Paragraph(str(item["Size"]), row_style_norm),
            Paragraph(str(item["Thickness"]), row_style_norm),
            Paragraph(str(item["Price (CIF)"]), row_style_price)
        ]
        data.append(row)

    t = Table(data, colWidths=[140, 90, 90, 80, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), lux_black),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, lux_gold),
        ('ROWBACKGROUNDS', (1,1), (-1,-1), [colors.white, lux_light_grey]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 25))

    # 4. Terms
    elements.append(Paragraph("TERMS OF SALE", ParagraphStyle('TermsHead', fontSize=10, textColor=lux_black, spaceAfter=5, fontName='Times-Bold')))
    
    terms_left = f"""<font color="#D4AF37">&bull;</font> <b>Incoterm:</b> {term}<br/><font color="#D4AF37">&bull;</font> <b>Transit Time:</b> {transit}<br/><font color="#D4AF37">&bull;</font> <b>Payment:</b> 30% Advance, Balance vs Scan BL."""
    terms_right = """<font color="#D4AF37">&bull;</font> <b>Packing:</b> Seaworthy Wooden Crates.<br/><font color="#D4AF37">&bull;</font> <b>Insurance:</b> "All Risks" Coverage included.<br/><font color="#D4AF37">&bull;</font> <b>Bank:</b> HDFC Bank, Jaipur Branch."""
    
    style_terms = ParagraphStyle('Terms', fontSize=9, textColor=lux_grey, leading=12, fontName='Times-Roman')
    elements.append(Table([[Paragraph(terms_left, style_terms), Paragraph(terms_right, style_terms)]], colWidths=[260, 260]))
    elements.append(Spacer(1, 20))

    # Footer
    elements.append(Paragraph("RUVELLO GLOBAL LLP  |  www.ruvello.com  |  +91 9636648894", ParagraphStyle('Footer', fontSize=8, textColor=lux_grey, alignment=1, fontName='Helvetica')))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- BUTTON TO GENERATE ---
st.markdown("---")
if st.button("Generate Luxury Invoice", type="primary"):
    if not buyer_name:
        st.error("Please enter the Buyer's Name!")
    else:
        pdf_bytes = generate_pdf(uploaded_logo, buyer_name, buyer_country, edited_data, invoice_no, validity_days, transit_time, incoterm)
        
        st.success("Invoice Generated Successfully!")
        st.download_button(
            label="Download PDF 📥",
            data=pdf_bytes,
            file_name=f"PI_{buyer_name.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )