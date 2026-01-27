import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.units import inch, mm
from reportlab.graphics.shapes import Drawing, Line
import io
import os
from datetime import datetime

# ==========================================
# ⚙️ CONFIGURATION ZONE
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

# Assets
AUTO_LOGO_FILE = "logo.png"
AUTO_SIG_FILE = "signature.png"
COUNTER_FILE = "pi_counter.txt"

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def get_next_invoice_number():
    if not os.path.exists(COUNTER_FILE):
        return 1103
    try:
        with open(COUNTER_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 1103

def increment_invoice_number(current_val):
    try:
        num_part = int(current_val.split('-')[-1])
        next_val = num_part + 1
        with open(COUNTER_FILE, "w") as f:
            f.write(str(next_val))
    except:
        pass

def num_to_words(amount):
    """Simple converter for Amount in Words (USD)"""
    # Note: For production, libraries like 'num2words' are better, 
    # but this avoids dependency errors in standard Streamlit clouds.
    return f"USD {amount:,.2f} (IN FIGURES)" 
    # If you have num2words installed, uncomment below:
    # from num2words import num2words
    # return "USD " + num2words(amount, lang='en').upper() + " ONLY"

# ==========================================
# 🚀 MAIN APP
# ==========================================
st.set_page_config(page_title="Ruvello PI Generator", page_icon="💎", layout="wide")
st.title("💎 Ruvello Global: Smart Proforma System")

# --- SIDEBAR: ASSETS ---
with st.sidebar:
    st.header("1. Assets")
    logo_source = AUTO_LOGO_FILE if os.path.exists(AUTO_LOGO_FILE) else st.file_uploader("Upload Logo", type=["png", "jpg"])
    if os.path.exists(AUTO_LOGO_FILE): st.success("✅ Logo Loaded")
    
    sig_source = AUTO_SIG_FILE if os.path.exists(AUTO_SIG_FILE) else st.file_uploader("Upload Signature", type=["png", "jpg"])
    if os.path.exists(AUTO_SIG_FILE): st.success("✅ Signature Loaded")

# --- SECTION 1: INVOICE META ---
st.subheader("1. Invoice Details")
col_i1, col_i2, col_i3 = st.columns(3)
with col_i1:
    current_counter = get_next_invoice_number()
    invoice_no = st.text_input("Invoice Number", value=f"PI-2025-26-{current_counter}")
with col_i2:
    invoice_date = st.date_input("Issue Date", value=datetime.today())
with col_i3:
    validity = st.number_input("Validity (Days)", value=15)

# --- SECTION 2: BUYER & LOGISTICS ---
st.subheader("2. Buyer & Logistics")
c1, c2 = st.columns(2)
with c1:
    st.info("Bill To (Buyer)")
    buyer_name = st.text_input("Buyer Company", placeholder="e.g. AlNosaif Marble")
    buyer_address = st.text_area("Address", height=100, placeholder="Street, City, Country")
    buyer_country = st.text_input("Destination Country", value="Bahrain")

with c2:
    st.info("Logistics")
    l_c1, l_c2 = st.columns(2)
    with l_c1:
        pre_carriage = st.text_input("Pre-Carriage", value="Road")
        port_load = st.text_input("Port of Loading", value="Chennai")
        incoterm = st.selectbox("Incoterm", ["CIF", "FOB", "EXW", "CFR"])
    with l_c2:
        port_discharge = st.text_input("Port of Discharge", value="Bahrain")
        final_dest = st.text_input("Final Destination", value="Bahrain")

# --- SECTION 3: PRODUCTS ---
st.subheader("3. Product Line Items")
df_template = pd.DataFrame([
    {"Product": "Black Galaxy", "Desc": "260Up x 70Up", "Qty": 450.0, "Unit": "M2", "Rate": 26.50},
    {"Product": "Jet Black", "Desc": "240Up x 70 to 90", "Qty": 450.0, "Unit": "M2", "Rate": 43.00},
])
edited_df = st.data_editor(df_template, num_rows="dynamic", use_container_width=True)

# --- SECTION 4: BANK & TERMS ---
st.subheader("4. Terms")
pay_terms = st.text_area("Payment Terms", value="50% Advance & Balance 50% Against BL Scan Copy", height=60)

# --- PDF ENGINE ---
def generate_proforma_pdf(logo, sig, inv_no, inv_dt, valid_days, 
                          b_name, b_addr, b_ctry, 
                          logistics, items, pay_terms, bank_d):
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=30, bottomMargin=30, leftMargin=40, rightMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # --- COLORS & STYLES ---
    GOLD = HexColor('#C5A059')
    BLACK = HexColor('#101010')
    DARK_GREY = HexColor('#404040')
    
    # Typography
    style_co_name = ParagraphStyle('H', fontName='Times-Bold', fontSize=26, textColor=BLACK, alignment=TA_CENTER, leading=28)
    style_slogan = ParagraphStyle('S', fontName='Helvetica', fontSize=8, textColor=GOLD, alignment=TA_CENTER, letterSpacing=3)
    style_address = ParagraphStyle('A', fontName='Helvetica', fontSize=9, textColor=DARK_GREY, alignment=TA_CENTER, leading=12)
    
    style_lbl_gold = ParagraphStyle('L', fontName='Helvetica-Bold', fontSize=8, textColor=GOLD, textTransform='uppercase')
    style_val_bold = ParagraphStyle('V', fontName='Helvetica-Bold', fontSize=9, textColor=BLACK, leading=11)
    style_val_norm = ParagraphStyle('N', fontName='Helvetica', fontSize=9, textColor=BLACK, leading=11)
    
    # 1. HEADER (CENTERED)
    if logo:
        logo_obj = logo if isinstance(logo, str) else (logo.seek(0) or logo)
        img = RLImage(logo_obj, width=1.8*inch, height=1.2*inch, kind='proportional')
        img.hAlign = 'CENTER'
        elements.append(img)
    
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(COMPANY_INFO["NAME"], style_co_name))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(COMPANY_INFO["SLOGAN"], style_slogan))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(COMPANY_INFO["ADDRESS"], style_address))
    elements.append(Paragraph(COMPANY_INFO["CONTACT"], style_address))
    elements.append(Spacer(1, 15))
    
    # Gold Separator
    d = Drawing(500, 2)
    d.add(Line(0, 0, 515, 0, strokeColor=GOLD, strokeWidth=1.5))
    elements.append(d)
    elements.append(Spacer(1, 20))

    # 2. LOGISTICS GRID (CLEAN LAYOUT)
    # Left Column: Buyer + Shipment
    buyer_info = [
        [Paragraph("CONSIGNEE / BUYER", style_lbl_gold)],
        [Paragraph(f"{b_name}<br/>{b_addr.replace(chr(10), '<br/>')}<br/>{b_ctry}", style_val_bold)],
        [Spacer(1, 10)],
        [Paragraph("SHIPMENT DETAILS", style_lbl_gold)],
        [Paragraph(f"""
        <b>Pre-Carriage:</b> {logistics['pre']}<br/>
        <b>Loading Port:</b> {logistics['pol']}<br/>
        <b>Discharge Port:</b> {logistics['pod']}<br/>
        <b>Final Dest:</b> {logistics['final']}<br/>
        <b>Incoterm:</b> {logistics['inco']}
        """, style_val_norm)]
    ]
    
    # Right Column: Invoice Meta
    invoice_meta = [
        [Paragraph("PROFORMA INVOICE DETAILS", style_lbl_gold)],
        [Paragraph(f"""
        <b>NO:</b> {inv_no}<br/>
        <b>DATE:</b> {inv_dt.strftime('%d-%b-%Y')}<br/>
        <b>VALID UNTIL:</b> {valid_days} Days<br/>
        <b>GSTIN:</b> {COMPANY_INFO['GSTIN']}<br/>
        <b>IEC:</b> {COMPANY_INFO['IEC']}
        """, style_val_norm)]
    ]
    
    t_grid = Table([
        [Table(buyer_info, colWidths=[260]), Table(invoice_meta, colWidths=[240])]
    ], colWidths=[270, 245])
    
    t_grid.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBEFORE', (1,0), (1,0), 0.5, HexColor('#E0E0E0')), # Vertical Divider
        ('LEFTPADDING', (1,0), (1,0), 15),
    ]))
    elements.append(t_grid)
    elements.append(Spacer(1, 25))

    # 3. ITEMS TABLE (REALISTIC)
    items["Amount"] = items["Qty"] * items["Rate"]
    total_val = items["Amount"].sum()
    
    headers = [
        Paragraph("DESCRIPTION OF GOODS", style_lbl_gold),
        Paragraph("QTY (M2)", style_lbl_gold),
        Paragraph("RATE ($)", style_lbl_gold),
        Paragraph("AMOUNT ($)", style_lbl_gold)
    ]
    
    data = [headers]
    for _, row in items.iterrows():
        if row['Qty'] > 0:
            desc = f"<b>{row['Product']}</b><br/>{row['Desc']}"
            data.append([
                Paragraph(desc, style_val_norm),
                f"{row['Qty']:.2f}",
                f"{row['Rate']:.2f}",
                f"{row['Amount']:,.2f}"
            ])
            
    # Total Row
    data.append([
        Paragraph("<b>TOTAL (USD)</b>", style_val_bold),
        "", "",
        Paragraph(f"<b>{total_val:,.2f}</b>", style_val_bold)
    ])
    
    t_items = Table(data, colWidths=[250, 80, 80, 105])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK),       # Header BG
        ('TEXTCOLOR', (0,0), (-1,0), GOLD),          # Header Text
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),         # Center Numbers
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-2), 0.5, HexColor('#EEEEEE')), # Light Grid
        ('LINEBELOW', (0,0), (-1,0), 1.5, GOLD),     # Gold Header Line
        ('BACKGROUND', (0,-1), (-1,-1), HexColor('#F5F5F5')), # Total Row BG
        ('PADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (-1,0), (-1,-1), 'RIGHT'),         # Align Amounts Right
    ]))
    elements.append(t_items)
    
    # Amount in Words
    elements.append(Spacer(1, 10))
    amt_words = num_to_words(total_val)
    elements.append(Paragraph(f"<b>AMOUNT CHARGEABLE:</b> {amt_words}", style_val_norm))
    elements.append(Spacer(1, 30))

    # 4. FOOTER GRID (Terms vs Bank vs Sig)
    # Using a 2-column layout. Left: Terms & Bank. Right: Signature.
    
    left_content = [
        [Paragraph("TERMS & CONDITIONS", style_lbl_gold)],
        [Paragraph(pay_terms, style_val_norm)],
        [Spacer(1, 10)],
        [Paragraph("BANKING INSTRUCTIONS", style_lbl_gold)],
        [Paragraph(f"""
        <b>Bank:</b> {bank_d['BANK_NAME']}<br/>
        <b>A/C Name:</b> {bank_d['AC_NAME']}<br/>
        <b>A/C No:</b> {bank_d['AC_NO']}<br/>
        <b>SWIFT:</b> {bank_d['SWIFT']}<br/>
        <b>IFSC:</b> {bank_d['IFSC']}
        """, style_val_norm)]
    ]
    
    # Signature Block (Perfectly Aligned Right)
    sig_content = []
    sig_content.append(Paragraph(f"For {COMPANY_INFO['NAME']}", style_val_bold))
    sig_content.append(Spacer(1, 35)) # Space for manual signature
    
    if sig:
        sig_obj = sig if isinstance(sig, str) else (sig.seek(0) or sig)
        img_sig = RLImage(sig_obj, width=1.5*inch, height=0.8*inch, kind='proportional')
        img_sig.hAlign = 'RIGHT'
        sig_content.append(img_sig)
        
    sig_content.append(Paragraph("Authorized Signatory", style_val_norm))
    
    right_content = [
        [Spacer(1, 20)], # Push signature down slightly
        [Table([[x] for x in sig_content], style=[('ALIGN', (0,0), (-1,-1), 'RIGHT')])]
    ]

    t_footer = Table([
        [Table(left_content, colWidths=[300]), Table(right_content, colWidths=[200])]
    ], colWidths=[315, 200])
    
    t_footer.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(t_footer)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- ACTION ---
st.divider()
if st.button("✨ Generate Invoice", type="primary"):
    log_data = {"pre": pre_carriage, "pol": port_load, "pod": port_discharge, "final": final_dest, "inco": incoterm}
    
    pdf_bytes = generate_proforma_pdf(
        logo_source, sig_source, invoice_no, invoice_date, validity,
        buyer_name, buyer_address, buyer_country,
        log_data, edited_df, pay_terms, BANK_DETAILS
    )
    
    increment_invoice_number(invoice_no)
    st.success(f"Invoice {invoice_no} Generated!")
    st.download_button("📥 Download PDF", data=pdf_bytes, file_name=f"{invoice_no}.pdf", mime="application/pdf")
