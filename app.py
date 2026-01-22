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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Line

# --- CONFIGURATION ---
st.set_page_config(page_title="Ruvello ERP", page_icon="💎", layout="wide")

# LUXURY THEME
GOLD = HexColor('#C5A059')
BLACK = HexColor('#101010')
WHITE = HexColor('#FFFFFF')
DARK_GREY = HexColor('#252525')

# DB FILE
DB_FILE = "ruvello_ultimate.db"

# --- SECURITY UTILS ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password, hashed_pw):
    return make_hash(password) == hashed_pw

# --- DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Users
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, created_at DATE)''')
    
    # 2. Products (Master - No Rates)
    c.execute('''CREATE TABLE IF NOT EXISTS products 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT UNIQUE, description TEXT, hsn TEXT, unit TEXT)''')
    
    # 3. Clients
    c.execute('''CREATE TABLE IF NOT EXISTS clients 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  company_name TEXT UNIQUE, address TEXT, country TEXT, 
                  email TEXT, phone TEXT)''')
    
    # 4. My Company Settings (Banks & Address)
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    
    # 5. Invoices (Fully Flexible)
    # Added 'billed_to_text' and 'bank_text' to store snapshots for that specific invoice
    c.execute('''CREATE TABLE IF NOT EXISTS invoices 
                 (inv_no TEXT PRIMARY KEY, type TEXT, date DATE, 
                  client_id INTEGER, status TEXT, 
                  container_no TEXT, vessel TEXT, pol TEXT, pod TEXT, 
                  final_dest TEXT, terms_payment TEXT, terms_delivery TEXT,
                  billed_to_text TEXT, bank_text TEXT,
                  FOREIGN KEY(client_id) REFERENCES clients(id))''')
    
    # 6. Invoice Items
    c.execute('''CREATE TABLE IF NOT EXISTS inv_items 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, inv_no TEXT, 
                  product_name TEXT, description TEXT, hsn TEXT, 
                  qty REAL, unit TEXT, rate REAL, amount REAL,
                  FOREIGN KEY(inv_no) REFERENCES invoices(inv_no))''')
    
    # 7. Measurement Slabs
    c.execute('''CREATE TABLE IF NOT EXISTS slabs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, inv_no TEXT, 
                  slab_no TEXT, gl REAL, gh REAL, nl REAL, nh REAL, 
                  gross_area REAL, net_area REAL,
                  FOREIGN KEY(inv_no) REFERENCES invoices(inv_no))''')

    # Defaults
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?)", ('admin', make_hash('admin123'), 'admin', datetime.now()))
        
    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute(query, params)
        if fetch:
            return c.fetchall()
        conn.commit()
    except Exception as e:
        st.error(f"Database Error: {e}")
    finally:
        conn.close()

# --- STYLES ---
def get_asset(name):
    return name if os.path.exists(name) else None

def get_styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle('R_Title', fontName='Times-Bold', fontSize=24, textColor=BLACK, leading=28, alignment=1))
    s.add(ParagraphStyle('R_Sub', fontName='Helvetica-Bold', fontSize=10, textColor=GOLD, alignment=1, letterSpacing=2))
    s.add(ParagraphStyle('R_Text', fontName='Helvetica', fontSize=9, textColor=BLACK, leading=12))
    return s

# --- MODULES ---

# 1. SETTINGS (User & Company)
def module_settings():
    st.markdown("## ⚙️ Settings & Company Profile")
    
    tab1, tab2, tab3 = st.tabs(["My Profile", "Company & Bank Details", "User Admin"])
    
    # TAB 1: Change Password
    with tab1:
        st.subheader("Security")
        curr_user = st.session_state['user']['name'] # FIX: Access from dict
        with st.form("change_pass"):
            new_p = st.text_input("New Password", type="password")
            confirm_p = st.text_input("Confirm", type="password")
            if st.form_submit_button("Update Password"):
                if new_p == confirm_p and new_p:
                    run_query("UPDATE users SET password=? WHERE username=?", (make_hash(new_p), curr_user))
                    st.success("Password Updated!")
                else:
                    st.error("Passwords mismatch.")

    # TAB 2: Company Setup (Address & Banks)
    with tab2:
        st.subheader("My Company Header")
        curr_addr = run_query("SELECT value FROM settings WHERE key='company_addr'", fetch=True)
        default_addr = curr_addr[0][0] if curr_addr else "1305, Uniyaro Ka Rasta... (Default)"
        
        new_addr = st.text_area("Company Address & Contact (For Header)", value=default_addr, height=100)
        if st.button("Save Company Address"):
            run_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('company_addr', ?)", (new_addr,))
            st.success("Address Saved")
        
        st.subheader("Bank Accounts")
        st.info("Save different bank details here to pick from invoices.")
        
        # Simple Bank Manager using keys like 'bank_1', 'bank_2'
        c1, c2 = st.columns(2)
        b_key = c1.text_input("Bank Profile Name (e.g., HDFC_EXPORT)")
        b_val = c2.text_area("Bank Details Text", height=100, placeholder="Bank Name: ...\nA/C No: ...\nSWIFT: ...")
        
        if st.button("Save Bank Profile"):
            if b_key and b_val:
                run_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"bank_{b_key}", b_val))
                st.success("Bank Profile Saved")
        
        # List existing banks
        banks = run_query("SELECT key, value FROM settings WHERE key LIKE 'bank_%'", fetch=True)
        if banks:
            st.write("Saved Banks:")
            for b in banks:
                with st.expander(b[0].replace('bank_', '')):
                    st.text(b[1])
                    if st.button(f"Delete {b[0]}", key=b[0]):
                        run_query("DELETE FROM settings WHERE key=?", (b[0],))
                        st.rerun()

    # TAB 3: Admin
    with tab3:
        if st.session_state['user']['role'] == 'admin':
            st.subheader("Create User")
            c1, c2, c3 = st.columns(3)
            u = c1.text_input("Username")
            p = c2.text_input("Password", type="password")
            r = c3.selectbox("Role", ["admin", "editor", "viewer"])
            if st.button("Create"):
                try:
                    run_query("INSERT INTO users VALUES (?,?,?,?)", (u, make_hash(p), r, datetime.now()))
                    st.success("User Created")
                except: st.error("Exists")
        else:
            st.warning("Admin Access Required")

# 2. MASTER DATA (No Rates)
def module_master():
    st.markdown("## 📦 Master Products")
    st.caption("Define Product Names and HSN Codes here. Rates are defined per Invoice.")
    
    # Editable Grid
    products = run_query("SELECT * FROM products", fetch=True)
    df_prod = pd.DataFrame(products if products else [], columns=['ID', 'Name', 'Description', 'HSN', 'Unit'])
    
    edited = st.data_editor(df_prod, num_rows="dynamic", use_container_width=True, key="prod_master")
    
    if st.button("Save Changes"):
        run_query("DELETE FROM products")
        for i, row in edited.iterrows():
            if row['Name']:
                run_query("INSERT INTO products (name, description, hsn, unit) VALUES (?,?,?,?)",
                          (row['Name'], row['Description'], row['HSN'], row['Unit']))
        st.success("Product Master Updated")

# 3. CRM
def module_crm():
    st.markdown("## 🏛️ Client CRM")
    with st.expander("Add Client"):
        name = st.text_input("Company Name")
        addr = st.text_area("Address")
        if st.button("Save"):
            run_query("INSERT INTO clients (company_name, address) VALUES (?,?)", (name, addr))
            st.success("Saved")
    
    data = run_query("SELECT * FROM clients", fetch=True)
    if data: st.dataframe(pd.DataFrame(data, columns=['ID','Name','Addr','Country','Email','Phone']))

# 4. SALES (THE CORE)
def module_sales():
    st.markdown("## 📄 Sales & Invoicing")
    
    tab_new, tab_edit = st.tabs(["Create New Invoice", "Edit Invoice"])
    
    # --- CREATE NEW ---
    with tab_new:
        st.subheader("Start New Order")
        c1, c2 = st.columns(2)
        inv_no = c1.text_input("Invoice No (e.g., PI/2026/001)")
        
        # Buyer Selection
        clients = run_query("SELECT id, company_name, address FROM clients", fetch=True)
        cli_dict = {c[1]: c for c in clients} if clients else {}
        sel_client_name = c2.selectbox("Select Buyer", list(cli_dict.keys()))
        
        # PRE-FILL EDITABLE FIELDS
        default_bill_to = cli_dict[sel_client_name][2] if sel_client_name else ""
        
        # Bank Selection
        banks = run_query("SELECT key, value FROM settings WHERE key LIKE 'bank_%'", fetch=True)
        bank_opts = {b[0].replace('bank_', ''): b[1] for b in banks}
        sel_bank_name = st.selectbox("Select Bank Profile", list(bank_opts.keys()) if bank_opts else [])
        default_bank = bank_opts[sel_bank_name] if sel_bank_name else ""
        
        if st.button("Initialize Invoice"):
            if inv_no and sel_client_name:
                try:
                    cid = cli_dict[sel_client_name][0]
                    # Create invoice with snapshots of address and bank
                    run_query('''INSERT INTO invoices (inv_no, type, date, client_id, status, billed_to_text, bank_text) 
                                 VALUES (?,?,?,?,?,?,?)''', 
                              (inv_no, 'PI', datetime.now(), cid, 'DRAFT', default_bill_to, default_bank))
                    st.success(f"Invoice {inv_no} Created! Go to 'Edit Invoice' tab to add details.")
                except Exception as e: st.error(f"Error: {e}")

    # --- EDIT EXISTING ---
    with tab_edit:
        invs = run_query("SELECT inv_no FROM invoices", fetch=True)
        sel_inv = st.selectbox("Select Invoice to Edit", [i[0] for i in invs] if invs else [])
        
        if sel_inv:
            inv_data = run_query("SELECT * FROM invoices WHERE inv_no=?", (sel_inv,), fetch=True)[0]
            # Unpack: 0=inv_no, 1=type, 2=date, 3=cid, 4=status, 5=cont, 6=vess, 7=pol, 8=pod, 9=dest, 10=pay, 11=del, 12=bill_text, 13=bank_text
            
            st.markdown(f"### 📝 Editing: {sel_inv}")
            
            with st.expander("1. Buyer & Bank Details (Fully Editable)", expanded=True):
                c1, c2 = st.columns(2)
                # Editable Snapshot of Buyer Address
                new_bill_to = c1.text_area("Bill To (Editable for this Invoice)", value=inv_data[12] if inv_data[12] else "")
                # Editable Snapshot of Bank Details
                new_bank = c2.text_area("Bank Details (Editable)", value=inv_data[13] if inv_data[13] else "")
                
                if st.button("Update Address/Bank"):
                    run_query("UPDATE invoices SET billed_to_text=?, bank_text=? WHERE inv_no=?", (new_bill_to, new_bank, sel_inv))
                    st.success("Updated")

            with st.expander("2. Logistics & Terms", expanded=False):
                c1, c2, c3 = st.columns(3)
                n_cont = c1.text_input("Container", inv_data[5])
                n_pol = c2.text_input("POL", inv_data[7])
                n_pod = c3.text_input("POD", inv_data[8])
                n_pay = st.text_input("Payment Terms", inv_data[10])
                if st.button("Update Logistics"):
                    run_query("UPDATE invoices SET container_no=?, pol=?, pod=?, terms_payment=? WHERE inv_no=?", (n_cont, n_pol, n_pod, n_pay, sel_inv))
                    st.success("Logistics Saved")
            
            st.markdown("### 3. Product Lines (Add & Edit Rates)")
            
            # Add Item
            masters = run_query("SELECT name, description, hsn, unit FROM products", fetch=True)
            prod_map = {m[0]: m for m in masters}
            
            c_add, c_btn = st.columns([3, 1])
            add_p = c_add.selectbox("Add Product from Master", [""] + list(prod_map.keys()))
            
            if c_btn.button("Add Row"):
                if add_p:
                    p = prod_map[add_p]
                    # Insert with Rate = 0.0 (User must edit)
                    run_query("INSERT INTO inv_items (inv_no, product_name, description, hsn, qty, unit, rate, amount) VALUES (?,?,?,?,?,?,?,?)",
                              (sel_inv, p[0], p[1], p[2], 1.0, p[3], 0.0, 0.0))
                    st.rerun()

            # Edit Grid
            items = run_query("SELECT id, product_name, description, hsn, qty, unit, rate, amount FROM inv_items WHERE inv_no=?", (sel_inv,), fetch=True)
            df_items = pd.DataFrame(items, columns=['ID', 'Product', 'Desc', 'HSN', 'Qty', 'Unit', 'Rate', 'Amount'])
            
            edited = st.data_editor(
                df_items, 
                column_config={"ID": None, "Amount": st.column_config.NumberColumn(disabled=True)},
                num_rows="dynamic",
                key="item_grid",
                use_container_width=True
            )
            
            if st.button("💾 Save Grid Changes"):
                for i, row in edited.iterrows():
                    amt = float(row['Qty']) * float(row['Rate'])
                    run_query("UPDATE inv_items SET product_name=?, description=?, hsn=?, qty=?, unit=?, rate=?, amount=? WHERE id=?",
                              (row['Product'], row['Desc'], row['HSN'], row['Qty'], row['Unit'], row['Rate'], amt, row['ID']))
                st.success("Calculations Updated!")
                st.rerun()

# 5. DOCUMENT ENGINE
def generate_pdf(inv_no):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20, bottomMargin=20, leftMargin=25, rightMargin=25)
    elements = []
    S = get_styles()
    
    # FETCH
    inv = run_query("SELECT * FROM invoices WHERE inv_no=?", (inv_no,), fetch=True)[0]
    items = run_query("SELECT * FROM inv_items WHERE inv_no=?", (inv_no,), fetch=True)
    # Fetch My Company Address
    my_addr = run_query("SELECT value FROM settings WHERE key='company_addr'", fetch=True)
    my_addr_txt = my_addr[0][0] if my_addr else "RUVELLO GLOBAL LLP..."
    
    # 1. HEADER
    logo = get_asset("logo.png")
    if logo: elements.append(RLImage(logo, width=2.2*inch, height=1.6*inch, kind='proportional'))
    
    elements.append(Paragraph("RUVELLO GLOBAL LLP", S['R_Title']))
    elements.append(Paragraph(my_addr_txt.replace('\n', '<br/>'), ParagraphStyle('ad', parent=S['R_Text'], alignment=1)))
    elements.append(Spacer(1, 10))
    
    title = "COMMERCIAL INVOICE" if inv[1] == 'CI' else "PROFORMA INVOICE"
    elements.append(Paragraph(title, S['R_Sub']))
    elements.append(Drawing(500, 5).add(Line(0,0,535,0, strokeColor=GOLD, strokeWidth=1.5)))
    elements.append(Spacer(1, 15))
    
    # 2. INFO GRID (Using Saved Snapshots)
    # inv[12] is 'billed_to_text', inv[0] is 'inv_no', inv[2] is 'date'
    
    grid_data = [
        [Paragraph(f"<b>INVOICE NO:</b> {inv[0]}<br/><b>DATE:</b> {inv[2]}", S['R_Text']),
         Paragraph(f"<b>BILL TO:</b><br/>{inv[12].replace(chr(10), '<br/>') if inv[12] else ''}", S['R_Text'])],
        [Paragraph(f"<b>LOGISTICS:</b><br/>Container: {inv[5] or ''}<br/>POL: {inv[7] or ''}<br/>POD: {inv[8] or ''}", S['R_Text']),
         Paragraph(f"<b>TERMS:</b><br/>Payment: {inv[10] or ''}", S['R_Text'])]
    ]
    
    t_grid = Table(grid_data, colWidths=[265, 265])
    t_grid.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#DDDDDD')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    elements.append(t_grid)
    elements.append(Spacer(1, 20))
    
    # 3. PRODUCT TABLE
    # items schema: id, inv, prod, desc, hsn, qty, unit, rate, amt
    headers = ["Product", "Description", "Qty", "Rate", "Amount"]
    data = [headers]
    total = 0
    for i in items:
        # i[2]=prod, i[3]=desc, i[5]=qty, i[7]=rate, i[8]=amt
        data.append([
            Paragraph(f"<b>{i[2]}</b>", S['R_Text']),
            Paragraph(i[3], S['R_Text']),
            f"{i[5]} {i[6]}",
            f"{i[7]:.2f}",
            f"{i[8]:.2f}"
        ])
        total += i[8]
    
    data.append(["TOTAL", "", "", "", f"<b>{total:,.2f}</b>"])
    
    t = Table(data, colWidths=[120, 180, 70, 70, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), GOLD),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#EEEEEE')),
        ('ALIGN', (-2,1), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,-1), (-1,-1), GOLD),
        ('TEXTCOLOR', (0,-1), (-1,-1), BLACK),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))
    
    # 4. BANK & SIGNATURE
    # inv[13] is 'bank_text'
    sig = get_asset("signature.png")
    sig_elem = RLImage(sig, width=1.5*inch, height=0.6*inch) if sig else Spacer(1, 40)
    
    bank_block = f"<b>BANKING DETAILS:</b><br/>{inv[13].replace(chr(10), '<br/>') if inv[13] else ''}"
    
    footer = [[Paragraph(bank_block, S['R_Text']), 
               [Paragraph("For RUVELLO GLOBAL LLP", S['R_Text']), sig_elem, Paragraph("Auth. Signatory", S['R_Text'])]]]
    
    t_foot = Table(footer, colWidths=[270, 270])
    t_foot.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (1,0), (1,0), 'CENTER')]))
    elements.append(t_foot)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def module_docs():
    st.markdown("## 🖨️ Document Center")
    invs = run_query("SELECT inv_no FROM invoices", fetch=True)
    sel = st.selectbox("Select Invoice", [i[0] for i in invs] if invs else [])
    
    if sel:
        if st.button("Generate PDF"):
            pdf = generate_pdf(sel)
            st.download_button("📥 Download PDF", pdf, f"{sel.replace('/','_')}.pdf", "application/pdf")

# --- LOGIN & MAIN ---
def login():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("RUVELLO ERP")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login", type="primary"):
            user = run_query("SELECT * FROM users WHERE username=?", (u,), fetch=True)
            if user and check_hash(p, user[0][1]):
                # Store user dict in session state
                st.session_state['user'] = {'name': u, 'role': user[0][2]}
                st.rerun()
            else:
                st.error("Invalid Credentials")

def main():
    init_db()
    if 'user' not in st.session_state:
        login()
    else:
        with st.sidebar:
            if get_asset("logo.png"): st.image("logo.png")
            st.title(f"User: {st.session_state['user']['name']}")
            nav = st.radio("Menu", ["Dashboard", "Settings", "Master Data", "Client CRM", "Sales (Invoice)", "Documents"])
            if st.button("Logout"):
                del st.session_state['user']
                st.rerun()
                
        if nav == "Dashboard": st.title("Dashboard")
        elif nav == "Settings": module_settings()
        elif nav == "Master Data": module_master()
        elif nav == "Client CRM": module_crm()
        elif nav == "Sales (Invoice)": module_sales()
        elif nav == "Documents": module_docs()

if __name__ == "__main__":
    main()
