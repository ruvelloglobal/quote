import streamlit as st
import sqlite3
import pandas as pd
import io
import os
import re
import hashlib
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.graphics.shapes import Drawing, Line

# --- CONFIG & THEME ---
st.set_page_config(page_title="Ruvello ERP", page_icon="💎", layout="wide")

# LUXURY THEME COLORS
GOLD = HexColor('#C5A059')
BLACK = HexColor('#101010')
WHITE = HexColor('#FFFFFF')
DARK_GREY = HexColor('#252525')
LIGHT_GREY = HexColor('#F4F4F4')

# --- DATABASE ENGINE ---
DB_FILE = "ruvello_erp.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    
    # Clients Table
    c.execute('''CREATE TABLE IF NOT EXISTS clients 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  company_name TEXT, address TEXT, country TEXT, 
                  email TEXT, phone TEXT)''')
    
    # Invoices Table (Stores PI and CI meta)
    c.execute('''CREATE TABLE IF NOT EXISTS invoices 
                 (inv_no TEXT PRIMARY KEY, type TEXT, date DATE, 
                  client_id INTEGER, status TEXT, 
                  container_no TEXT, vessel TEXT, pol TEXT, pod TEXT, 
                  final_dest TEXT, terms TEXT,
                  FOREIGN KEY(client_id) REFERENCES clients(id))''')
    
    # Slabs Table (Linked to Invoice)
    c.execute('''CREATE TABLE IF NOT EXISTS slabs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, inv_no TEXT, 
                  slab_no TEXT, gl REAL, gh REAL, nl REAL, nh REAL, 
                  gross_area REAL, net_area REAL,
                  FOREIGN KEY(inv_no) REFERENCES invoices(inv_no))''')

    # Create Default Admin if not exists
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        # Default Pass: admin123 (In production, use hashing)
        c.execute("INSERT INTO users VALUES ('admin', 'admin123', 'admin')")
        
    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, params)
    if fetch:
        res = c.fetchall()
    else:
        conn.commit()
        res = None
    conn.close()
    return res

# --- AUTHENTICATION MODULE ---
def check_login(username, password):
    user = run_query("SELECT * FROM users WHERE username=? AND password=?", (username, password), fetch=True)
    return user[0] if user else None

def login_screen():
    st.markdown("<h1 style='text-align: center; color: #C5A059;'>💎 RUVELLO GLOBAL ERP</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Authorized Access Only</p>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            sub = st.form_submit_button("SECURE LOGIN", type="primary")
            
        if sub:
            user = check_login(u, p)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = user[2]
                st.session_state['username'] = user[0]
                st.rerun()
            else:
                st.error("Access Denied.")

# --- HELPER FUNCTIONS ---
def get_asset(name):
    return name if os.path.exists(name) else None

def parse_allowance(allow_str):
    nums = re.findall(r'\d+', allow_str)
    if len(nums) >= 2: return int(nums[0]), int(nums[1]) # H, L
    return 0, 0

# --- PDF STYLES ---
def get_styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle('R_Title', fontName='Times-Bold', fontSize=24, textColor=BLACK, leading=28, alignment=1))
    s.add(ParagraphStyle('R_Sub', fontName='Helvetica-Bold', fontSize=10, textColor=GOLD, alignment=1, letterSpacing=2))
    s.add(ParagraphStyle('R_Header', fontName='Times-Bold', fontSize=10, textColor=GOLD, alignment=1))
    s.add(ParagraphStyle('R_Text', fontName='Helvetica', fontSize=9, textColor=BLACK))
    s.add(ParagraphStyle('R_Label', fontName='Helvetica-Bold', fontSize=7, textColor=HexColor('#555555')))
    return s

# --- MODULES ---

# 1. CLIENT MANAGEMENT (CRM)
def module_clients():
    st.markdown("## 🏛️ Client Management")
    
    with st.expander("➕ Add New Client", expanded=False):
        c1, c2 = st.columns(2)
        name = c1.text_input("Company Name")
        country = c2.text_input("Country")
        email = c1.text_input("Email")
        phone = c2.text_input("Phone")
        addr = st.text_area("Full Address")
        
        if st.button("Save Client Profile"):
            run_query("INSERT INTO clients (company_name, address, country, email, phone) VALUES (?,?,?,?,?)", 
                      (name, addr, country, email, phone))
            st.success(f"Client {name} added to Database.")

    st.subheader("Client Directory")
    clients = run_query("SELECT * FROM clients", fetch=True)
    if clients:
        df = pd.DataFrame(clients, columns=['ID', 'Name', 'Address', 'Country', 'Email', 'Phone'])
        st.dataframe(df, use_container_width=True)

# 2. SALES (Proforma Invoice)
def module_sales():
    st.markdown("## 📄 Sales & Proforma")
    
    # Step 1: Select Client
    clients = run_query("SELECT id, company_name FROM clients", fetch=True)
    client_dict = {c[1]: c[0] for c in clients} if clients else {}
    
    c1, c2 = st.columns(2)
    selected_client = c1.selectbox("Select Buyer", list(client_dict.keys()) if client_dict else [])
    pi_no = c2.text_input("Generate PI No", value=f"PI/{datetime.now().year}/001")
    
    # Step 2: Invoice Details
    c3, c4, c5 = st.columns(3)
    date = c3.date_input("Date")
    terms = c4.selectbox("Incoterm", ["FOB", "CIF", "EXW", "DDP"])
    material = c5.text_input("Material", "ABSOLUTE BLACK")
    
    if st.button("💾 Create Proforma Invoice"):
        if selected_client:
            cid = client_dict[selected_client]
            # Check duplicate
            exist = run_query("SELECT * FROM invoices WHERE inv_no=?", (pi_no,), fetch=True)
            if exist:
                st.error("Invoice Number already exists!")
            else:
                run_query("INSERT INTO invoices (inv_no, type, date, client_id, status, terms) VALUES (?,?,?,?,?,?)",
                          (pi_no, 'PI', date, cid, 'OPEN', terms))
                st.success(f"PI {pi_no} Created! Proceed to Measurement.")

# 3. OPERATIONS (Measurement & Magic Paste)
def module_ops():
    st.markdown("## 📏 Operations: Measurement")
    
    # Select Active PI
    open_pis = run_query("SELECT inv_no FROM invoices WHERE type='PI'", fetch=True)
    pi_list = [p[0] for p in open_pis] if open_pis else []
    
    selected_pi = st.selectbox("Select Active Order (PI)", pi_list)
    
    if selected_pi:
        st.info(f"Adding Slabs for Order: **{selected_pi}**")
        
        # Settings
        c1, c2 = st.columns(2)
        allowance = c1.text_input("Allowance (-H x L)", "-5 x 4")
        container = c2.text_input("Container No (Optional)", "")
        
        # Magic Paste
        st.markdown("### 📋 Magic Paste (Excel Data)")
        pc1, pc2 = st.columns(2)
        raw_l = pc1.text_area("Gross Lengths", height=150)
        raw_h = pc2.text_area("Gross Heights", height=150)
        
        if st.button("⚡ Calculate & Save Slabs"):
            deduct_h, deduct_l = parse_allowance(allowance)
            try:
                l_list = [float(x) for x in raw_l.split()]
                h_list = [float(x) for x in raw_h.split()]
                
                if len(l_list) != len(h_list):
                    st.error("Mismatch in counts!")
                    return
                
                # Save to DB
                # First clear old slabs for this PI if re-doing? (Optional, here we append)
                run_query("DELETE FROM slabs WHERE inv_no=?", (selected_pi,))
                
                for i in range(len(l_list)):
                    gl, gh = l_list[i], h_list[i]
                    nl, nh = gl - deduct_l, gh - deduct_h
                    ga = round((gl * gh)/10000, 3)
                    na = round((nl * nh)/10000, 3)
                    slab_no = f"RG-{i+1}"
                    
                    run_query("INSERT INTO slabs (inv_no, slab_no, gl, gh, nl, nh, gross_area, net_area) VALUES (?,?,?,?,?,?,?,?)",
                              (selected_pi, slab_no, gl, gh, nl, nh, ga, na))
                
                # Update Invoice with Container if added
                if container:
                    run_query("UPDATE invoices SET container_no=? WHERE inv_no=?", (container, selected_pi))
                    
                st.success(f"✅ Saved {len(l_list)} slabs to Database for {selected_pi}")
                
            except ValueError:
                st.error("Numbers only please.")

# 4. LOGISTICS & DOCS (The Output Engine)
def generate_pdf_doc(doc_type, inv_no):
    # Fetch Data
    inv = run_query("SELECT * FROM invoices WHERE inv_no=?", (inv_no,), fetch=True)[0]
    client = run_query("SELECT * FROM clients WHERE id=?", (inv[3],), fetch=True)[0]
    slabs = run_query("SELECT * FROM slabs WHERE inv_no=?", (inv_no,), fetch=True)
    
    # Calculate Totals
    total_slabs = len(slabs)
    total_net = sum(s[8] for s in slabs)
    total_gross = sum(s[7] for s in slabs)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=30, bottomMargin=30, leftMargin=30, rightMargin=30)
    elements = []
    S = get_styles()
    
    # --- HEADER ---
    logo = get_asset("logo.png")
    if logo: elements.append(RLImage(logo, width=2.2*inch, height=1.6*inch, kind='proportional'))
    
    elements.append(Paragraph("RUVELLO GLOBAL LLP", S['R_Title']))
    addr = "1305, Uniyaro Ka Rasta, Chandpol Bazar, Jaipur, Rajasthan<br/>www.ruvello.com | +91 9636648894"
    elements.append(Paragraph(addr, ParagraphStyle('addr', parent=S['R_Text'], alignment=1, textColor=DARK_GREY)))
    elements.append(Spacer(1, 10))
    
    # Document Title
    title = "COMMERCIAL INVOICE" if doc_type == "CI" else "PACKING LIST"
    elements.append(Paragraph(title, S['R_Sub']))
    elements.append(Drawing(500, 5).add(Line(0,0,535,0, strokeColor=GOLD, strokeWidth=2)))
    elements.append(Spacer(1, 20))
    
    # --- INFO GRID (Exporter/Buyer) ---
    grid_data = [
        [Paragraph(f"<b>INVOICE NO:</b> {inv[0]}<br/><b>DATE:</b> {inv[2]}", S['R_Text']),
         Paragraph(f"<b>BUYER:</b><br/>{client[1]}<br/>{client[2]}<br/>{client[3]}", S['R_Text'])],
        [Paragraph(f"<b>EXPORTER:</b><br/>RUVELLO GLOBAL LLP<br/>Jaipur, India", S['R_Text']),
         Paragraph(f"<b>LOGISTICS:</b><br/>Container: {inv[5]}<br/>Terms: {inv[10]}", S['R_Text'])]
    ]
    t_grid = Table(grid_data, colWidths=[265, 265])
    t_grid.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, HexColor('#E0E0E0')), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('PADDING', (0,0), (-1,-1), 10)]))
    elements.append(t_grid)
    elements.append(Spacer(1, 25))
    
    # --- TABLE DATA ---
    if doc_type == "CI":
        # Commercial Invoice Table (Grouped)
        headers = ["Description", "Qty (m2)", "Rate", "Amount"]
        # Simplified for demo: Single line item for total area
        # In real ERP, you'd have a 'Products' table. Here we assume 1 material.
        rate = 35.00 # Placeholder rate
        amt = total_net * rate
        data = [headers, ["Polished Granite Slabs", f"{total_net:.3f}", f"${rate}", f"${amt:,.2f}"]]
        # Total
        data.append(["TOTAL (CIF)", "", "", f"<b>${amt:,.2f}</b>"])
        col_w = [200, 100, 100, 130]
        
    else:
        # Packing List / Measurement (Detailed)
        headers = ["S.No", "Slab No", "Gross (cm)", "", "Net (cm)", "", "Net Area"]
        sub_headers = ["", "", "L", "H", "L", "H", "(m2)"]
        data = [headers, sub_headers]
        for i, s in enumerate(slabs):
            data.append([str(i+1), s[2], f"{s[3]:.0f}", f"{s[4]:.0f}", f"{s[5]:.0f}", f"{s[6]:.0f}", f"<b>{s[8]:.3f}</b>"])
        data.append(["TOTAL", "", "", "", "", "", f"<b>{total_net:.3f}</b>"])
        col_w = [30, 80, 60, 60, 60, 60, 80]

    # --- TABLE STYLE (Luxury) ---
    t = Table(data, colWidths=col_w, repeatRows=2)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), GOLD),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#DDDDDD')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BACKGROUND', (0,-1), (-1,-1), BLACK),
        ('TEXTCOLOR', (0,-1), (-1,-1), GOLD),
    ]))
    elements.append(t)
    
    # --- FOOTER ---
    elements.append(Spacer(1, 30))
    sig = get_asset("signature.png")
    if sig: 
        elements.append(Paragraph("For RUVELLO GLOBAL LLP", S['R_Text']))
        elements.append(RLImage(sig, width=1.5*inch, height=0.6*inch))
        elements.append(Paragraph("Authorized Signatory", S['R_Text']))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def module_docs():
    st.markdown("## 🚢 Logistics & Documentation")
    
    # Select PI to convert
    invoices = run_query("SELECT inv_no FROM invoices", fetch=True)
    inv_list = [i[0] for i in invoices] if invoices else []
    
    sel_inv = st.selectbox("Select Invoice Order", inv_list)
    
    if sel_inv:
        # Update Logistics
        st.caption("Update Logistics Details")
        c1, c2, c3 = st.columns(3)
        cont = c1.text_input("Container No")
        vessel = c2.text_input("Vessel")
        pol = c3.text_input("Port of Loading", "Mundra")
        
        if st.button("Update Logistics Data"):
            run_query("UPDATE invoices SET container_no=?, vessel=?, pol=? WHERE inv_no=?", (cont, vessel, pol, sel_inv))
            st.success("Logistics Updated.")
            
        st.markdown("### 🖨️ Generate Documents")
        d1, d2 = st.columns(2)
        
        # Generate CI
        pdf_ci = generate_pdf_doc("CI", sel_inv)
        d1.download_button("📥 Commercial Invoice (PDF)", pdf_ci, f"CI_{sel_inv}.pdf", "application/pdf")
        
        # Generate PL
        pdf_pl = generate_pdf_doc("PL", sel_inv)
        d2.download_button("📥 Packing List / Measure (PDF)", pdf_pl, f"PL_{sel_inv}.pdf", "application/pdf")

# 5. SEARCH & TRACKING
def module_search():
    st.markdown("## 🔍 Global Search & Tracking")
    
    tab1, tab2 = st.tabs(["Database Search", "Container Tracking"])
    
    with tab1:
        q = st.text_input("Search (Invoice No, Buyer, or Slab No)")
        if q:
            # Search Invoices
            res_inv = run_query(f"SELECT * FROM invoices WHERE inv_no LIKE '%{q}%'", fetch=True)
            if res_inv:
                st.write("**Invoices Found:**")
                st.dataframe(pd.DataFrame(res_inv, columns=['Inv No', 'Type', 'Date', 'ClientID', 'Status', 'Cont', 'Vessel', 'POL', 'POD', 'Dest', 'Terms']))
                
            # Search Clients
            res_cli = run_query(f"SELECT * FROM clients WHERE company_name LIKE '%{q}%'", fetch=True)
            if res_cli:
                st.write("**Clients Found:**")
                st.dataframe(pd.DataFrame(res_cli))
    
    with tab2:
        track_no = st.text_input("Enter Container No")
        if st.button("Track Live"):
            # Mock API
            st.success(f"Tracking {track_no}...")
            st.progress(70)
            c1, c2 = st.columns(2)
            c1.metric("Status", "In Transit")
            c2.metric("Location", "Singapore Strait")
            st.map(pd.DataFrame({'lat': [1.35], 'lon': [103.8]}))

# --- MAIN APP LOGIC ---
def main():
    init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        
    if not st.session_state['logged_in']:
        login_screen()
    else:
        # SIDEBAR NAVIGATION
        with st.sidebar:
            if get_asset("logo.png"): st.image("logo.png")
            st.title("RUVELLO ERP")
            st.caption(f"User: {st.session_state['username'].upper()}")
            
            nav = st.radio("Module", ["Dashboard", "Client CRM", "Sales (PI)", "Operations (Measure)", "Logistics (Docs)", "Search & Track"])
            
            if st.button("Logout"):
                st.session_state['logged_in'] = False
                st.rerun()

        # ROUTING
        if nav == "Dashboard":
            st.title("Admin Dashboard")
            tot_cli = len(run_query("SELECT * FROM clients", fetch=True))
            tot_inv = len(run_query("SELECT * FROM invoices", fetch=True))
            tot_slabs = len(run_query("SELECT * FROM slabs", fetch=True))
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Active Clients", tot_cli)
            m2.metric("Total Invoices", tot_inv)
            m3.metric("Total Slabs Processed", tot_slabs)
            
        elif nav == "Client CRM": module_clients()
        elif nav == "Sales (PI)": module_sales()
        elif nav == "Operations (Measure)": module_ops()
        elif nav == "Logistics (Docs)": module_docs()
        elif nav == "Search & Track": module_search()

if __name__ == "__main__":
    main()
