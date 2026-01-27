import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.graphics.shapes import Drawing, Line
import io
import os
from datetime import datetime

# ==========================================
# ⚙️ CONFIGURATION ZONE (EDIT ONCE HERE)
# ==========================================
COMPANY_INFO = {
    "NAME": "RUVELLO GLOBAL LLP",
    "SLOGAN": "EXQUISITE NATURAL STONES & SURFACES",
    "ADDRESS": "1305, Uniyaro Ka Rasta, Chandpol Bazar, Jaipur, Rajasthan, INDIA - 302001",
    "CONTACT": "Web: www.ruvello.com | Email: ruvelloglobal@gmail.com | +91 9636648894",
    "GSTIN": "08ABMFR3949N1ZA",
    "IEC": "ABMFR3949N"
}

BANK_DETAILS = {
    "BANK_NAME": "KOTAK MAHINDRA BANK LTD",
    "BRANCH": "JAIPUR-INDIA",
    "AC_NAME": "RUVELLO GLOBAL LLP",
    "AC_NO": "9636649890",
    "SWIFT": "KKBKINBBXXX",
    "IFSC": "KKBK0003553"
}

# File names to look for automatically
AUTO_LOGO_FILE = "logo.png"
AUTO_SIG_FILE = "signature.png"
COUNTER_FILE = "pi_counter.txt"

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def get_next_invoice_number():
    """Reads the counter file or defaults to 1103"""
    if not os.path.exists(COUNTER_FILE):
        return 1103
    try:
        with open(COUNTER_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 1103

def increment_invoice_number(current_val):
    """Updates the counter file for the next time"""
    # Extract number from string like "PI-2025-26-1103"
    try:
        num_part = int(current_val.split('-')[-1])
        next_val = num_part + 1
        with open(COUNTER_FILE, "w") as f:
            f.write(str(next_val))
    except:
        pass # If manual edit format is weird, don't crash

# ==========================================
# 🚀 MAIN APP
# ==========================================
st.set_page_config(page_title="Ruvello PI Generator", page_icon="💎", layout="wide")
st.title("💎 Ruvello Global: Smart Proforma System")

# --- SIDEBAR: ASSETS ---
with st.sidebar:
    st.header("1. Assets")
    
    # Auto-load Logo
    logo_source = None
    if os.path.exists(AUTO_LOGO_FILE):
        st.success(f"✅ Found {AUTO_LOGO_FILE}")
        logo_source = AUTO_LOGO_FILE
    else:
        logo_source = st.file_uploader("Upload Logo (Save as 'logo.png' to auto-load)", type=["png", "jpg"])

    # Auto-load Signature
    sig_source = None
    if os.path.exists(AUTO_SIG_FILE):
        st.success(f"✅ Found {AUTO_SIG_FILE}")
        sig_source = AUTO_SIG_FILE
    else:
        sig_source = st.file_uploader("Upload Signature (Save as 'signature.png' to auto-load)", type=["png", "jpg"])

# --- SECTION 1: INVOICE META ---
st.subheader("1. Invoice Details")
col_i1, col_i2, col_i3 = st.columns(3)

with col_i1:
    # Auto Generate Number
    current_counter = get_next_invoice_number()
    default_pi = f"PI-2025-26-{current_counter}"
    invoice_no = st.text_input("Invoice Number (Auto-Generated)", value=default_pi)

with col_i2:
    invoice_date = st.date_input("Issue Date", value=datetime.today())

with col_i3:
    validity = st.number_input("Validity (Days)", value=15)

# --- SECTION 2: BUYER & LOGISTICS ---
st.subheader("2. Buyer & Logistics")
c1, c2 = st.columns(2)

with c1:
    st.info("Bill To (Buyer)")
    buyer_name = st.text_input("Buyer Company", placeholder="e.g. Village Arts Pty Ltd")
    buyer_address = st.text_area("Address", height=100, placeholder="Street, City, Country")
    buyer_country = st.text_input("Destination Country", value="Australia")

with c2:
    st.info("Logistics")
    l_c1, l_c2 = st.columns(2)
    with l_c1:
        pre_carriage = st.text_input("Pre-Carriage", value="Road")
        port_load = st.text_input("Port of Loading", value="Mundra / Chennai")
        incoterm = st.selectbox("Incoterm", ["FOB", "CIF", "EXW", "CFR"])
    with l_c2:
        port_discharge = st.text_input("Port of Discharge", value="Adelaide")
        final_dest = st.text_input("Final Destination", value="Australia")

# --- SECTION 3: PRODUCTS ---
st.subheader("3. Product Line Items")
# Pre-defined columns for the editor
df_template = pd.DataFrame([
    {"Product": "Black Galaxy Granite", "Desc": "Polished, 3cm Slabs", "Qty": 45.0, "Unit": "M2", "Rate": 85.00},
    {"Product": "Viscon White", "Desc": "Polished, 2cm Slabs", "Qty": 0.0, "Unit": "M2", "Rate": 55.00},
])
edited_df = st.data_editor(df_template, num_rows="dynamic", use_container_width=True)

# --- SECTION 4: BANK & TERMS (Auto-filled) ---
st.subheader("4. Commercial Terms")
tc1, tc2 = st.columns(2)
with tc1:
    payment_terms = st.text_area("Payment Terms", value="50% Advance & Balance 50% Against BL Scan Copy", height=100)
with tc2:
    # Hidden inputs just to confirm they are there (or allow override)
    st.caption(f"Using Auto-Bank Details: **{BANK_DETAILS['BANK_NAME']}**")
    with st.expander("Edit Bank Details (Optional)"):
        b_name = st.text_input("Bank", value=BANK_DETAILS["BANK_NAME"])
        b_ac = st.text_input("A/C No", value=BANK_DETAILS["AC_NO"])
        b_swift = st.text_input("SWIFT", value=BANK_DETAILS["SWIFT"])

# --- PDF ENGINE ---
def generate_proforma_pdf(logo, sig, inv_no, inv_dt, valid_days, 
                          b_name, b_addr, b_ctry, 
                          logistics, items, pay_terms, bank_d):
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20, bottomMargin=20, leftMargin=30, rightMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Colors & Styles
    GOLD = HexColor('#C5A059')
    BLACK = HexColor('#101010')
    DARK_GREY = HexColor('#303030')
    
    style_header = ParagraphStyle('H', fontName='Times-Bold', fontSize=24, textColor=BLACK, alignment=1, leading=26)
    style_slogan = ParagraphStyle('S', fontName='Helvetica', fontSize=8, textColor=GOLD, alignment=1, letterSpacing=2)
    style_bold = ParagraphStyle('B', fontName='Helvetica-Bold', fontSize=9, textColor=BLACK)
    style_norm = ParagraphStyle('N', fontName='Helvetica', fontSize=9, textColor=DARK_GREY, leading=11)
    
    # 1. HEADER (Logo + Name + Fixed Spacing)
    if logo:
        # Handle both file path (str) and uploaded file (BytesIO)
        if isinstance(logo, str):
            img = RLImage(logo, width=2.0*inch, height=1.3*inch, kind='proportional')
        else:
            logo.seek(0)
            img = RLImage(logo, width=2.0*inch, height=1.3*inch, kind='proportional')
        elements.append(img)
    
    elements.append(Paragraph(COMPANY_INFO["NAME"], style_header))
    # spacer to prevent overlap
    elements.append(Spacer(1, 6)) 
    elements.append(Paragraph(COMPANY_INFO["SLOGAN"], style_slogan))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(COMPANY_INFO["ADDRESS"], style_norm))
    elements.append(Paragraph(COMPANY_INFO["CONTACT"], style_norm))
    elements.append(Spacer(1, 10))
    
    # Gold Line
    d = Drawing(500, 2)
    d.add(Line(0, 0, 535, 0, strokeColor=GOLD, strokeWidth=1))
    elements.append(d)
    elements.append(Spacer(1, 15))

    # 2. INFO GRID (Exporter vs Buyer vs Invoice)
    # We use a 2x2 grid approach for clean layout
    
    # Box 1: Invoice Meta
    meta_html = f"""
    <font color='#C5A059'><b>PROFORMA INVOICE DETAILS</b></font><br/>
    <b>NO:</b> {inv_no}<br/>
    <b>DATE:</b> {inv_dt.strftime('%d-%b-%Y')}<br/>
    <b>VALID UNTIL:</b> {valid_days} Days
    """
    
    # Box 2: Buyer Info
    buyer_html = f"""
    <font color='#C5A059'><b>CONSIGNEE / BUYER</b></font><br/>
    <b>{b_name}</b><br/>
    {b_addr.replace(chr(10), '<br/>')}<br/>
    <b>{b_ctry}</b>
    """
    
    # Box 3: Logistics
    log_html = f"""
    <font color='#C5A059'><b>SHIPMENT DETAILS</b></font><br/>
    <b>Pre-Carriage:</b> {logistics['pre']}<br/>
    <b>Loading Port:</b> {logistics['pol']}<br/>
    <b>Discharge Port:</b> {logistics['pod']}<br/>
    <b>Final Dest:</b> {logistics['final']}<br/>
    <b>Incoterm:</b> {logistics['inco']}
    """
    
    grid_data = [
        [Paragraph(buyer_html, style_norm), Paragraph(meta_html, style_norm)],
        [Paragraph(log_html, style_norm), ""] # Empty cell for balance or extra info
    ]
    
    t_grid = Table(grid_data, colWidths=[300, 235])
    t_grid.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#EEEEEE')),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t_grid)
    elements.append(Spacer(1, 20))

    # 3. ITEMS TABLE
    # Calculate totals
    items["Amount"] = items["Qty"] * items["Rate"]
    total_val = items["Amount"].sum()
    
    # Header
    tbl_data = [[
        Paragraph("Product Description", style_bold),
        Paragraph("Qty", style_bold),
        Paragraph("Unit", style_bold),
        Paragraph("Rate", style_bold),
        Paragraph("Amount", style_bold)
    ]]
    
    # Rows
    for _, row in items.iterrows():
        if row['Qty'] > 0:
            desc = f"<b>{row['Product']}</b><br/>{row['Desc']}"
            tbl_data.append([
                Paragraph(desc, style_norm),
                f"{row['Qty']:.2f}",
                row['Unit'],
                f"{row['Rate']:.2f}",
                f"{row['Amount']:,.2f}"
            ])
            
    # Total Row
    tbl_data.append([
        Paragraph("<b>TOTAL (USD)</b>", style_bold),
        "", "", "",
        Paragraph(f"<b>{total_val:,.2f}</b>", style_bold)
    ])
    
    t_items = Table(tbl_data, colWidths=[245, 60, 50, 80, 100])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), GOLD),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-2), 0.5, HexColor('#DDDDDD')), # Grid for items
        ('LINEBELOW', (0,0), (-1,0), 1, GOLD),
        ('BACKGROUND', (0,-1), (-1,-1), HexColor('#F0F0F0')), # Total row bg
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_items)
    elements.append(Spacer(1, 20))

    # 4. BANK & TERMS
    bank_html = f"""
    <font color='#C5A059'><b>BANKING INSTRUCTIONS</b></font><br/>
    <b>Bank:</b> {bank_d['BANK_NAME']}<br/>
    <b>A/C Name:</b> {bank_d['AC_NAME']}<br/>
    <b>A/C No:</b> {bank_d['AC_NO']}<br/>
    <b>SWIFT:</b> {bank_d['SWIFT']}<br/>
    <b>IFSC:</b> {bank_d['IFSC']}
    """
    
    terms_html = f"""
    <font color='#C5A059'><b>TERMS & CONDITIONS</b></font><br/>
    {pay_terms}<br/><br/>
    We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.
    """
    
    t_footer = Table([[Paragraph(terms_html, style_norm), Paragraph(bank_html, style_norm)]], colWidths=[300, 235])
    t_footer.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBEFORE', (1,0), (1,0), 1, HexColor('#EEEEEE')), # Vertical divider
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_footer)
    elements.append(Spacer(1, 30))

    # 5. SIGNATURE
    sig_content = []
    sig_content.append(Paragraph("<b>For RUVELLO GLOBAL LLP</b>", style_norm))
    sig_content.append(Spacer(1, 25))
    
    if sig:
        if isinstance(sig, str):
            sig_img = RLImage(sig, width=1.5*inch, height=0.8*inch, kind='proportional')
        else:
            sig.seek(0)
            sig_img = RLImage(sig, width=1.5*inch, height=0.8*inch, kind='proportional')
        sig_img.hAlign = 'RIGHT'
        sig_content.append(sig_img)
    else:
        sig_content.append(Spacer(1, 40))
        
    sig_content.append(Paragraph("Authorized Signatory", style_norm))
    
    t_sig = Table([[ "", [item for item in sig_content] ]], colWidths=[350, 185])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(t_sig)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- GENERATE ACTION ---
st.divider()
if st.button("✨ Generate Invoice & Update Counter", type="primary"):
    # 1. Gather Logistics
    log_data = {
        "pre": pre_carriage, "pol": port_load, "pod": port_discharge, 
        "final": final_dest, "inco": incoterm
    }
    
    # 2. Gather Bank (from Config + Edits)
    # Using the variables from the expander directly or defaults
    final_bank = BANK_DETAILS.copy()
    
    # 3. Generate
    pdf_bytes = generate_proforma_pdf(
        logo_source, sig_source, invoice_no, invoice_date, validity,
        buyer_name, buyer_address, buyer_country,
        log_data, edited_df, payment_terms, final_bank
    )
    
    # 4. Auto-Increment & Save Logic
    increment_invoice_number(invoice_no)
    
    st.success(f"Invoice {invoice_no} Generated Successfully! Counter updated.")
    st.download_button("📥 Download PDF", data=pdf_bytes, file_name=f"{invoice_no}.pdf", mime="application/pdf")
