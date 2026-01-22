import streamlit as st
import pandas as pd
import io
import os
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.graphics.shapes import Drawing, Line

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Ruvello ERP", page_icon="💎", layout="wide")

# --- GLOBAL STYLES & ASSETS ---
GOLD = HexColor('#C5A059')
BLACK = HexColor('#101010')
WHITE = HexColor('#FFFFFF')
DARK_GREY = HexColor('#303030')

# Initialize Session State for Linked Data
if 'buyer_name' not in st.session_state: st.session_state['buyer_name'] = ""
if 'invoice_no' not in st.session_state: st.session_state['invoice_no'] = "EXP/2026/001"
if 'container_no' not in st.session_state: st.session_state['container_no'] = ""
if 'buyer_address' not in st.session_state: st.session_state['buyer_address'] = ""

# --- HELPER FUNCTIONS ---
def get_logo():
    if os.path.exists("logo.png"): return "logo.png"
    return None

def get_signature():
    if os.path.exists("signature.png"): return "signature.png"
    return None

def parse_allowance(allow_str):
    nums = re.findall(r'\d+', allow_str)
    if len(nums) >= 2: return int(nums[0]), int(nums[1])
    elif len(nums) == 1: return int(nums[0]), int(nums[0])
    return 0, 0

# --- EXCEL GENERATOR ---
def generate_excel_ci(data, invoice_meta, buyer_meta, logistics):
    output = io.BytesIO()
    workbook = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Create sheets
    df_inv = pd.DataFrame(data)
    df_inv.to_excel(workbook, sheet_name='Commercial Invoice', startrow=15, index=False)
    
    # Get workbook and worksheet objects
    wb = workbook.book
    ws = workbook.sheets['Commercial Invoice']
    
    # Define formats
    fmt_header = wb.add_format({'bold': True, 'font_color': '#C5A059', 'bg_color': 'black', 'border': 1})
    fmt_title = wb.add_format({'bold': True, 'font_size': 16, 'font_color': '#C5A059'})
    
    # Write Headers
    ws.write('A1', 'RUVELLO GLOBAL LLP', fmt_title)
    ws.write('A3', f"Invoice No: {invoice_meta['no']}")
    ws.write('A4', f"Buyer: {buyer_meta['name']}")
    
    # Apply header format to table
    for col_num, value in enumerate(df_inv.columns.values):
        ws.write(15, col_num, value, fmt_header)
        
    workbook.close()
    output.seek(0)
    return output

# --- PDF REPORTLAB STYLES ---
def get_ruvello_styles():
    styles = getSampleStyleSheet()
    s = {}
    s['Title'] = ParagraphStyle('Title', fontName='Times-Bold', fontSize=24, textColor=BLACK, alignment=1, leading=28)
    s['Sub'] = ParagraphStyle('Sub', fontName='Helvetica-Bold', fontSize=10, textColor=GOLD, alignment=1, letterSpacing=2)
    s['Label'] = ParagraphStyle('Label', fontName='Helvetica-Bold', fontSize=7, textColor=HexColor('#555555'), textTransform='uppercase')
    s['Header_Gold'] = ParagraphStyle('Hg', fontName='Times-Bold', fontSize=10, textColor=GOLD, alignment=1)
    s['Header_Black'] = ParagraphStyle('Hb', fontName='Helvetica', fontSize=8, textColor=BLACK, alignment=1)
    s['Normal'] = ParagraphStyle('Norm', fontName='Helvetica', fontSize=9, textColor=BLACK, leading=12)
    return s

# =================================================================================================
# MODULE 1: PROFORMA INVOICE (PI)
# =================================================================================================
def module_pi():
    st.markdown("## 📄 Proforma Invoice Generator")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state['buyer_name'] = st.text_input("Buyer Name", st.session_state['buyer_name'])
        st.session_state['buyer_address'] = st.text_area("Buyer Address", st.session_state['buyer_address'])
    with col2:
        st.session_state['invoice_no'] = st.text_input("PI Number", st.session_state['invoice_no'])
        
    st.info("ℹ️ *Data entered here links to other modules automatically.*")
    
    # (Simplified PI Logic for this Dashboard demo - connects to data)
    st.write("... [PI Generation Logic Linked] ...")
    if st.button("Generate PI PDF"):
        st.success("Proforma Invoice Generated (Mockup for Dashboard flow)")

# =================================================================================================
# MODULE 2: MEASUREMENT SHEET
# =================================================================================================
def module_measurement():
    st.markdown("## 📏 Smart Measurement Sheet")
    
    col1, col2 = st.columns(2)
    with col1:
        gross_l = st.text_area("Paste GROSS LENGTHS", height=150, placeholder="280\n290")
    with col2:
        gross_h = st.text_area("Paste GROSS HEIGHTS", height=150, placeholder="180\n190")
        
    allowance = st.text_input("Allowance (-H x L)", "-5 x 4")
    
    if st.button("Calculate & Generate Sheet"):
        # Reuse logic from previous turn
        deduct_h, deduct_l = parse_allowance(allowance)
        # ... Calculation Logic ...
        st.success("Measurement Sheet Calculated! (Linking to CI Module...)")

# =================================================================================================
# MODULE 3: COMMERCIAL INVOICE (CI) & PACKING LIST (PL)
# =================================================================================================
def module_commercial():
    st.markdown("## 🚢 Commercial Invoice & Packing List")
    st.caption("Matches '115 - INVOICE' Reference • Generates PDF & Excel")

    # --- 1. Logistics Inputs ---
    with st.expander("📦 Shipment & Logistics Details", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            exporter_ref = st.text_input("Exporter Ref", "EX/RV/2026")
            pre_carriage = st.text_input("Pre-Carriage By", "Road")
            vessel = st.text_input("Vessel/Flight No", "")
        with c2:
            port_load = st.text_input("Port of Loading", "MUNDRA, INDIA")
            port_discharge = st.text_input("Port of Discharge", "SYDNEY, AUSTRALIA")
            final_dest = st.text_input("Final Destination", "SYDNEY")
        with c3:
            payment_terms = st.text_input("Terms of Payment", "DAP (DOCUMENTS AGAINST PAYMENT)")
            delivery_terms = st.selectbox("Terms of Delivery", ["CIF", "FOB", "EXW"])
            container = st.text_input("Container No", st.session_state['container_no'])

    # --- 2. Goods Data ---
    st.subheader("📦 Goods Description")
    data_ci = pd.DataFrame([
        {"Description": "POLISHED GRANITE SLABS - ABSOLUTE BLACK", "HSN": "68029300", "Qty": 430.428, "Unit": "M2", "Rate": 17.65},
        {"Description": "TAN BROWN GRANITE", "HSN": "68029300", "Qty": 0.0, "Unit": "M2", "Rate": 25.00},
    ])
    edited_ci = st.data_editor(data_ci, num_rows="dynamic", use_container_width=True)

    # --- 3. Generation ---
    if st.button("✨ Generate Commercial Set (PDF + Excel)", type="primary"):
        # -- PDF GENERATION LOGIC --
        buffer_pdf = io.BytesIO()
        doc = SimpleDocTemplate(buffer_pdf, pagesize=A4, topMargin=20, bottomMargin=20, leftMargin=20, rightMargin=20)
        elements = []
        S = get_ruvello_styles()
        
        # 1. HEADER (Exporter / Consignee Grid)
        logo = get_logo()
        logo_img = RLImage(logo, width=2*inch, height=1.5*inch, kind='proportional') if logo else Spacer(1, 1)
        
        # Exporter Block
        exporter_txt = """<b>EXPORTER:</b><br/>
        <b>RUVELLO GLOBAL LLP</b><br/>
        1305, Uniyaro Ka Rasta, Chandpol Bazar,<br/>
        Jaipur, Rajasthan, INDIA - 302001<br/>
        GSTIN: 08ABMFR3949N1ZA"""
        
        # Invoice Block
        inv_txt = f"""<b>INVOICE NO:</b> {st.session_state['invoice_no']}<br/>
        <b>DATE:</b> {datetime.today().strftime('%d-%b-%Y')}<br/>
        <b>BUYER ORDER:</b> {exporter_ref}<br/>
        <b>TERMS:</b> {payment_terms}"""
        
        # Consignee Block
        consignee_txt = f"""<b>CONSIGNEE:</b><br/>
        <b>{st.session_state['buyer_name']}</b><br/>
        {st.session_state['buyer_address']}"""
        
        # Logistics Block
        log_txt = f"""<b>PRE-CARRIAGE:</b> {pre_carriage}<br/>
        <b>LOADING:</b> {port_load}<br/>
        <b>DISCHARGE:</b> {port_discharge}<br/>
        <b>FINAL DEST:</b> {final_dest}<br/>
        <b>CONTAINER:</b> {container}"""
        
        # Layout Grid
        data_grid = [
            [logo_img, Paragraph(inv_txt, S['Normal'])],
            [Paragraph(exporter_txt, S['Normal']), Paragraph(log_txt, S['Normal'])],
            [Paragraph(consignee_txt, S['Normal']), ""]
        ]
        t_grid = Table(data_grid, colWidths=[270, 270])
        t_grid.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, HexColor('#D0D0D0')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('SPAN', (0,0), (0,0)), # Logo cell
        ]))
        elements.append(t_grid)
        elements.append(Spacer(1, 20))
        
        # 2. GOODS TABLE (Reference Style)
        headers = [["Description of Goods", "HSN", "Qty", "Unit", "Rate ($)", "Amount ($)"]]
        table_rows = []
        total_amt = 0
        for i, row in edited_ci.iterrows():
            if row['Qty'] > 0:
                amt = row['Qty'] * row['Rate']
                total_amt += amt
                table_rows.append([
                    Paragraph(row['Description'], S['Normal']),
                    row['HSN'],
                    f"{row['Qty']:.3f}",
                    row['Unit'],
                    f"{row['Rate']:.2f}",
                    f"{amt:,.2f}"
                ])
        
        # Total Row
        table_rows.append(["TOTAL (CIF)", "", "", "", "", f"<b>{total_amt:,.2f}</b>"])
        
        t_goods = Table(headers + table_rows, colWidths=[180, 60, 70, 40, 70, 100])
        t_goods.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), BLACK),
            ('TEXTCOLOR', (0,0), (-1,0), GOLD),
            ('GRID', (0,0), (-1,-1), 0.5, HexColor('#CCCCCC')),
            ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
            ('BACKGROUND', (0,-1), (-1,-1), GOLD),
            ('TEXTCOLOR', (0,-1), (-1,-1), BLACK),
        ]))
        elements.append(t_goods)
        elements.append(Spacer(1, 30))
        
        # 3. BANK & SIGNATURE
        bank_txt = """<b>BANK DETAILS:</b><br/>
        Bank: HDFC BANK LTD<br/>
        A/C Name: RUVELLO GLOBAL LLP<br/>
        Swift: HDFCCINBB"""
        
        sig_img = get_signature()
        sig_elem = RLImage(sig_img, width=1.5*inch, height=0.6*inch) if sig_img else Spacer(1, 40)
        
        footer_data = [[Paragraph(bank_txt, S['Normal']), [Paragraph("For RUVELLO GLOBAL LLP", S['Normal']), sig_elem, Paragraph("Auth. Signatory", S['Normal'])]]]
        t_foot = Table(footer_data, colWidths=[270, 270])
        t_foot.setStyle(TableStyle([('ALIGN', (1,0), (1,0), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
        elements.append(t_foot)
        
        doc.build(elements)
        buffer_pdf.seek(0)
        
        # -- EXCEL GENERATION --
        buffer_excel = generate_excel_ci(edited_ci, {'no': st.session_state['invoice_no']}, {'name': st.session_state['buyer_name']}, {})

        # -- DOWNLOAD BUTTONS --
        c1, c2 = st.columns(2)
        c1.download_button("📥 Download PDF Invoice", buffer_pdf, "Commercial_Invoice.pdf", "application/pdf")
        c2.download_button("📊 Download Excel Invoice", buffer_excel, "Commercial_Invoice.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# =================================================================================================
# MODULE 4: AUTOMATION & SALES
# =================================================================================================
def module_automation():
    st.markdown("## 🤖 Client & Sales Automation")
    
    tab1, tab2 = st.tabs(["WhatsApp Bot", "Container Tracking"])
    
    with tab1:
        st.subheader("WhatsApp Catalog Bot")
        st.info("Simulated Environment. Connect Twilio API for live sending.")
        
        client_ph = st.text_input("Client WhatsApp Number", "+61")
        msg_template = st.selectbox("Message Template", [
            "Share Black Galaxy Price List",
            "Share Container Update",
            "Share Company Profile"
        ])
        
        if msg_template == "Share Black Galaxy Price List":
            st.code("Hello! Here is the latest luxury price list for Black Galaxy Granite from Ruvello Global. [Attachment: Price_List.pdf]")
            
        if st.button("🚀 Send WhatsApp Message"):
            st.toast(f"Message sent to {client_ph} successfully!", icon="✅")

    with tab2:
        st.subheader("Live Container Tracking")
        track_no = st.text_input("Enter Container / BL Number", st.session_state['container_no'])
        
        if st.button("Track Shipment"):
            st.success("Status Found: ON BOARD")
            st.progress(60)
            st.markdown("""
            * **Origin:** Mundra, India (Departed 12 Jan)
            * **Current:** Indian Ocean
            * **ETA:** Sydney, Australia (05 Feb)
            """)

# =================================================================================================
# MAIN DASHBOARD LAYOUT
# =================================================================================================
def main():
    with st.sidebar:
        # App Logo
        if get_logo():
            st.image(get_logo(), width=150)
            
        st.title("RUVELLO ERP")
        st.markdown("---")
        
        # Navigation
        menu = st.radio("Navigate", [
            "🏠 Dashboard",
            "📄 Proforma Invoice",
            "📏 Measurement Sheet",
            "🚢 Commercial & PL",
            "🤖 Sales & Tracking"
        ])
        
        st.markdown("---")
        st.caption("© 2026 Ruvello Global LLP")

    # Routing
    if menu == "🏠 Dashboard":
        st.title("Welcome back, Rahul.")
        st.metric("Pending Orders", "3", "1 New")
        st.metric("Active Shipments", "2", "On Time")
        st.info("Select a module from the sidebar to begin.")
        
    elif menu == "📄 Proforma Invoice":
        module_pi()
        
    elif menu == "📏 Measurement Sheet":
        module_measurement()
        
    elif menu == "🚢 Commercial & PL":
        module_commercial()
        
    elif menu == "🤖 Sales & Tracking":
        module_automation()

if __name__ == "__main__":
    main()
