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

# --- CONFIGURATION ---
st.set_page_config(page_title="Ruvello ERP", page_icon="💎", layout="wide")

# LUXURY THEME
GOLD = HexColor('#C5A059')
BLACK = HexColor('#101010')
WHITE = HexColor('#FFFFFF')
DARK_GREY = HexColor('#252525')

# DB FILE
DB_FILE = "ruvello_master.db"

# --- SECURITY UTILS ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password, hashed_pw):
    if make_hash(password) == hashed_pw:
        return True
    return False

# --- DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Users Table (Role: 'admin', 'editor', 'viewer')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, created_at DATE)''')
    
    # 2. Products Master (New!)
    c.execute('''CREATE TABLE IF NOT EXISTS products 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT UNIQUE, description TEXT, hsn TEXT, 
                  unit TEXT, default_rate REAL)''')
    
    # 3. Clients
    c.execute('''CREATE TABLE IF NOT EXISTS clients 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  company_name TEXT UNIQUE, address TEXT, country TEXT, 
                  email TEXT, phone TEXT)''')
    
    # 4. Invoices (PI & CI Meta)
    c.execute('''CREATE TABLE IF NOT EXISTS invoices 
                 (inv_no TEXT PRIMARY KEY, type TEXT, date DATE, 
                  client_id INTEGER, status TEXT, 
                  container_no TEXT, vessel TEXT, pol TEXT, pod TEXT, 
                  final_dest TEXT, terms_payment TEXT, terms_delivery TEXT,
                  FOREIGN KEY(client_id) REFERENCES clients(id))''')
    
    # 5. Invoice Items (New! Links products to invoices)
    c.execute('''CREATE TABLE IF NOT EXISTS inv_items 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, inv_no TEXT, 
                  product_name TEXT, description TEXT, hsn TEXT, 
                  qty REAL, unit TEXT, rate REAL, amount REAL,
                  FOREIGN KEY(inv_no) REFERENCES invoices(inv_no))''')
    
    # 6. Measurement Slabs
    c.execute('''CREATE TABLE IF NOT EXISTS slabs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, inv_no TEXT, 
                  slab_no TEXT, gl REAL, gh REAL, nl REAL, nh REAL, 
                  gross_area REAL, net_area REAL,
                  FOREIGN KEY(inv_no) REFERENCES invoices(inv_no))''')

    # Create Default Admin
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?)", 
                  ('admin', make_hash('admin123'), 'admin', datetime.now()))
        
    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute(query, params)
        if fetch:
            res = c.fetchall()
            return res
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
    s.add(ParagraphStyle('R_Bold', fontName='Helvetica-Bold', fontSize=9, textColor=BLACK))
    return s

# --- MODULES ---

# 1. USER MANAGEMENT & SETTINGS
def module_settings():
    st.markdown("## ⚙️ Settings & User Management")
    
    tab1, tab2 = st.tabs(["My Profile", "User Administration"])
    
    with tab1:
        st.subheader("Change Password")
        curr_user = st.session_state['username']
        with st.form("change_pass"):
            new_p = st.text_input("New Password", type="password")
            confirm_p = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                if new_p == confirm_p and new_p:
                    run_query("UPDATE users SET password=? WHERE username=?", (make_hash(new_p), curr_user))
                    st.success("Password Updated Successfully!")
                else:
                    st.error("Passwords do not match.")

    with tab2:
        if st.session_state['user_role'] == 'admin':
            st.subheader("Manage Team Access")
            
            # Add User
            with st.expander("➕ Create New User"):
                c1, c2, c3 = st.columns(3)
                u_new = c1.text_input("Username")
                p_new = c2.text_input("Default Password", type="password")
                r_new = c3.selectbox("Role", ["editor", "viewer", "admin"])
                
                if st.button("Create User"):
                    try:
                        run_query("INSERT INTO users VALUES (?,?,?,?)", 
                                  (u_new, make_hash(p_new), r_new, datetime.now()))
                        st.success(f"User {u_new} created!")
                    except:
                        st.error("Username already exists.")
            
            # List Users
            st.markdown("### Active Users")
            users = run_query("SELECT username, role, created_at FROM users", fetch=True)
            df_users = pd.DataFrame(users, columns=['Username', 'Role', 'Created At'])
            st.dataframe(df_users, use_container_width=True)
            
            # Delete User
            d_user = st.selectbox("Select User to Delete", [u[0] for u in users if u[0] != 'admin'])
            if st.button("Delete Selected User"):
                run_query("DELETE FROM users WHERE username=?", (d_user,))
                st.warning(f"User {d_user} deleted.")
                st.rerun()
        else:
            st.error("Restricted: Admin Access Only.")

# 2. MASTER DATA (PRODUCTS)
def module_master():
    st.markdown("## 📦 Master Data Management")
    st.caption("Define reusable products here. They will appear in dropdowns when creating invoices.")
    
    # Product Editor
    products = run_query("SELECT * FROM products", fetch=True)
    
    # Prepare Dataframe
    if products:
        df_prod = pd.DataFrame(products, columns=['ID', 'Name', 'Description', 'HSN', 'Unit', 'Rate ($)'])
    else:
        df_prod = pd.DataFrame(columns=['ID', 'Name', 'Description', 'HSN', 'Unit', 'Rate ($)'])

    # Editable Grid
    edited_prod = st.data_editor(df_prod, num_rows="dynamic", key="prod_editor", use_container_width=True)

    if st.button("💾 Save Product Master"):
        # We perform a full sync strategy for simplicity in this demo (Delete All -> Re-insert)
        # In a massive production DB, you'd do upserts.
        run_query("DELETE FROM products") 
        for i, row in edited_prod.iterrows():
            if row['Name']: # Only save if name exists
                run_query("INSERT INTO products (name, description, hsn, unit, default_rate) VALUES (?,?,?,?,?)",
                          (row['Name'], row['Description'], row['HSN'], row['Unit'], row['Rate ($)']))
        st.success("Product Database Updated!")

# 3. CLIENT CRM
def module_crm():
    st.markdown("## 🏛️ Client CRM")
    
    with st.expander("➕ Add New Client", expanded=False):
        c1, c2 = st.columns(2)
        name = c1.text_input("Company Name")
        country = c2.text_input("Country")
        email = c1.text_input("Email")
        phone = c2.text_input("Phone")
        addr = st.text_area("Address")
        
        if st.button("Save Client"):
            try:
                run_query("INSERT INTO clients (company_name, address, country, email, phone) VALUES (?,?,?,?,?)",
                          (name, addr, country, email, phone))
                st.success(f"Client {name} saved.")
            except:
                st.error("Client name already exists.")

    clients = run_query("SELECT * FROM clients", fetch=True)
    if clients:
        st.dataframe(pd.DataFrame(clients, columns=['ID', 'Name', 'Address', 'Country', 'Email', 'Phone']), use_container_width=True)

# 4. SALES & INVOICING (The Core)
def module_sales():
    st.markdown("## 📄 Sales & Invoicing")
    
    # 1. Create / Select Invoice
    c1, c2 = st.columns([1, 2])
    mode = c1.radio("Action", ["Create New Invoice", "Edit Existing Invoice"])
    
    if mode == "Create New Invoice":
        st.subheader("New Proforma Invoice (PI)")
        clients = run_query("SELECT id, company_name FROM clients", fetch=True)
        cli_dict = {c[1]: c[0] for c in clients}
        
        col1, col2 = st.columns(2)
        sel_client = col1.selectbox("Buyer", list(cli_dict.keys()) if cli_dict else [])
        inv_no = col2.text_input("Invoice No", f"PI/{datetime.now().year}/001")
        
        col3, col4 = st.columns(2)
        date = col3.date_input("Date")
        terms = col4.selectbox("Incoterm", ["FOB", "CIF", "EXW", "DDP"])
        
        if st.button("Create Invoice"):
            if sel_client:
                try:
                    run_query("INSERT INTO invoices (inv_no, type, date, client_id, status, terms_delivery) VALUES (?,?,?,?,?,?)",
                              (inv_no, 'PI', date, cli_dict[sel_client], 'DRAFT', terms))
                    st.success(f"Invoice {inv_no} Initialized!")
                except:
                    st.error("Invoice Number already exists.")
                    
    elif mode == "Edit Existing Invoice":
        invs = run_query("SELECT inv_no FROM invoices", fetch=True)
        sel_inv = c2.selectbox("Select Invoice to Edit", [i[0] for i in invs] if invs else [])
        
        if sel_inv:
            st.markdown(f"### Editing: {sel_inv}")
            
            # A. Invoice Meta Data
            curr_inv = run_query("SELECT * FROM invoices WHERE inv_no=?", (sel_inv,), fetch=True)[0]
            
            with st.expander("📝 Edit Header & Logistics", expanded=False):
                col1, col2 = st.columns(2)
                n_cont = col1.text_input("Container No", curr_inv[5])
                n_vess = col2.text_input("Vessel", curr_inv[6])
                n_pol = col1.text_input("Port of Loading", curr_inv[7])
                n_pod = col2.text_input("Port of Discharge", curr_inv[8])
                n_pay = st.text_input("Payment Terms", curr_inv[10] if curr_inv[10] else "DAP")
                
                if st.button("Update Meta Data"):
                    run_query("UPDATE invoices SET container_no=?, vessel=?, pol=?, pod=?, terms_payment=? WHERE inv_no=?",
                              (n_cont, n_vess, n_pol, n_pod, n_pay, sel_inv))
                    st.success("Details Updated")
            
            # B. Product Lines (Dynamic Editor)
            st.markdown("### 📦 Product Lines")
            
            # Fetch existing items
            items = run_query("SELECT id, product_name, description, hsn, qty, unit, rate, amount FROM inv_items WHERE inv_no=?", (sel_inv,), fetch=True)
            
            # Convert to DF
            if items:
                df_items = pd.DataFrame(items, columns=['ID', 'Product', 'Description', 'HSN', 'Qty', 'Unit', 'Rate', 'Amount'])
            else:
                df_items = pd.DataFrame(columns=['ID', 'Product', 'Description', 'HSN', 'Qty', 'Unit', 'Rate', 'Amount'])
            
            # Add "New Row" capability via Master Data
            master_prods = run_query("SELECT name, description, hsn, unit, default_rate FROM products", fetch=True)
            prod_names = [p[0] for p in master_prods] if master_prods else []
            
            # Product Selector to Add
            c_add, c_btn = st.columns([3,1])
            add_prod = c_add.selectbox("Add from Master", [""] + prod_names)
            if c_btn.button("Add Row") and add_prod:
                p_data = next((p for p in master_prods if p[0] == add_prod), None)
                if p_data:
                    run_query("INSERT INTO inv_items (inv_no, product_name, description, hsn, qty, unit, rate, amount) VALUES (?,?,?,?,?,?,?,?)",
                              (sel_inv, p_data[0], p_data[1], p_data[2], 1, p_data[3], p_data[4], p_data[4]))
                    st.rerun()

            # The Editable Grid
            edited_items = st.data_editor(
                df_items, 
                column_config={
                    "ID": None, # Hide ID
                    "Amount": st.column_config.NumberColumn(disabled=True) # Auto-calc
                },
                num_rows="dynamic", 
                use_container_width=True,
                key="inv_grid"
            )
            
            if st.button("💾 Save Invoice Items"):
                # Strategy: Update updated rows, Calculate Amount
                for i, row in edited_items.iterrows():
                    new_amt = float(row['Qty']) * float(row['Rate'])
                    run_query("UPDATE inv_items SET product_name=?, description=?, hsn=?, qty=?, unit=?, rate=?, amount=? WHERE id=?",
                              (row['Product'], row['Description'], row['HSN'], row['Qty'], row['Unit'], row['Rate'], new_amt, row['ID']))
                st.success("Invoice Saved!")
                st.rerun() # Refresh to show calc amounts

# 5. GENERATE DOCUMENTS
def generate_pdf(inv_no, doc_type):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=25, bottomMargin=25, leftMargin=25, rightMargin=25)
    elements = []
    S = get_styles()
    
    # DATA FETCH
    inv = run_query("SELECT * FROM invoices WHERE inv_no=?", (inv_no,), fetch=True)[0]
    client = run_query("SELECT * FROM clients WHERE id=?", (inv[3],), fetch=True)[0]
    items = run_query("SELECT product_name, description, hsn, qty, unit, rate, amount FROM inv_items WHERE inv_no=?", (inv_no,), fetch=True)
    
    # 1. HEADER
    logo = get_asset("logo.png")
    if logo: elements.append(RLImage(logo, width=2.2*inch, height=1.6*inch, kind='proportional'))
    
    elements.append(Paragraph("RUVELLO GLOBAL LLP", S['R_Title']))
    addr = """1305, Uniyaro Ka Rasta, Chandpol Bazar, Jaipur, Rajasthan, INDIA - 302001<br/>
    <b>www.ruvello.com</b> | ruvelloglobal@gmail.com | +91 9636648894"""
    elements.append(Paragraph(addr, ParagraphStyle('Ad', parent=S['R_Text'], alignment=1, textColor=DARK_GREY)))
    elements.append(Spacer(1, 10))
    
    # TITLE
    title = "COMMERCIAL INVOICE" if doc_type == "CI" else "PROFORMA INVOICE"
    elements.append(Paragraph(title, S['R_Sub']))
    elements.append(Drawing(500, 5).add(Line(0,0,535,0, strokeColor=GOLD, strokeWidth=1.5)))
    elements.append(Spacer(1, 15))
    
    # 2. INFO GRID
    grid_data = [
        [Paragraph(f"<b>INVOICE NO:</b> {inv[0]}<br/><b>DATE:</b> {inv[2]}", S['R_Text']),
         Paragraph(f"<b>BUYER:</b><br/>{client[1]}<br/>{client[2]}<br/>{client[3]}", S['R_Text'])],
        [Paragraph(f"<b>EXPORTER:</b><br/>RUVELLO GLOBAL LLP<br/>Jaipur, India", S['R_Text']),
         Paragraph(f"<b>LOGISTICS:</b><br/>Container: {inv[5] or 'TBA'}<br/>Terms: {inv[11]} / {inv[10] or ''}", S['R_Text'])]
    ]
    t_grid = Table(grid_data, colWidths=[265, 265])
    t_grid.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, HexColor('#DDDDDD')), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('PADDING', (0,0), (-1,-1), 8)]))
    elements.append(t_grid)
    elements.append(Spacer(1, 20))
    
    # 3. ITEMS TABLE
    headers = ["Product / Description", "HSN", "Qty", "Unit", "Rate", "Amount"]
    data = [headers]
    total = 0
    for i in items:
        # i = name, desc, hsn, qty, unit, rate, amount
        desc = f"<b>{i[0]}</b><br/>{i[1]}"
        data.append([Paragraph(desc, S['R_Text']), i[2], f"{i[3]:.2f}", i[4], f"{i[5]:.2f}", f"{i[6]:.2f}"])
        total += i[6]
    
    data.append(["TOTAL", "", "", "", "", f"<b>{total:,.2f}</b>"])
    
    t = Table(data, colWidths=[200, 60, 60, 40, 70, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), GOLD),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#EEEEEE')),
        ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,-1), (-1,-1), GOLD),
        ('TEXTCOLOR', (0,-1), (-1,-1), BLACK),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))
    
    # 4. SIGNATURE
    sig = get_asset("signature.png")
    sig_img = RLImage(sig, width=1.5*inch, height=0.6*inch) if sig else Spacer(1, 40)
    
    footer = [[Paragraph("Bank: HDFC BANK LTD<br/>A/C: RUVELLO GLOBAL LLP", S['R_Text']), 
               [Paragraph("For RUVELLO GLOBAL LLP", S['R_Text']), sig_img, Paragraph("Auth. Signatory", S['R_Text'])]]]
    
    t_foot = Table(footer, colWidths=[270, 270])
    t_foot.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (1,0), (1,0), 'CENTER')]))
    elements.append(t_foot)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def module_docs():
    st.markdown("## 🖨️ Document Center")
    invs = run_query("SELECT inv_no FROM invoices", fetch=True)
    sel_inv = st.selectbox("Select Invoice to Print", [i[0] for i in invs] if invs else [])
    
    if sel_inv:
        c1, c2 = st.columns(2)
        pdf_pi = generate_pdf(sel_inv, "PI")
        c1.download_button("📥 Proforma Invoice (PDF)", pdf_pi, f"PI_{sel_inv.replace('/','_')}.pdf", "application/pdf")
        
        pdf_ci = generate_pdf(sel_inv, "CI")
        c2.download_button("📥 Commercial Invoice (PDF)", pdf_ci, f"CI_{sel_inv.replace('/','_')}.pdf", "application/pdf")

# --- LOGIN ---
def login():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.image(get_asset("logo.png") or "https://via.placeholder.com/150", width=200)
        st.title("RUVELLO ERP LOGIN")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login", type="primary"):
            user = run_query("SELECT * FROM users WHERE username=?", (u,), fetch=True)
            if user and check_hash(p, user[0][1]):
                st.session_state['user'] = {'name': u, 'role': user[0][2]}
                st.rerun()
            else:
                st.error("Invalid Credentials")

# --- MAIN ---
def main():
    init_db()
    
    if 'user' not in st.session_state:
        login()
    else:
        # SIDEBAR
        with st.sidebar:
            if get_asset("logo.png"): st.image("logo.png")
            st.title(f"User: {st.session_state['user']['name'].upper()}")
            st.caption(f"Role: {st.session_state['user']['role'].upper()}")
            
            nav = st.radio("Navigation", 
                ["Dashboard", "Client CRM", "Master Data", "Sales (Invoice)", "Measurement", "Documents", "Settings"])
            
            if st.button("Logout"):
                del st.session_state['user']
                st.rerun()

        # ROUTING
        if nav == "Dashboard":
            st.title("Executive Dashboard")
            st.metric("Total Invoices", len(run_query("SELECT * FROM invoices", fetch=True) or []))
            st.metric("Total Clients", len(run_query("SELECT * FROM clients", fetch=True) or []))
            
        elif nav == "Client CRM": module_crm()
        elif nav == "Master Data": module_master()
        elif nav == "Sales (Invoice)": module_sales()
        elif nav == "Measurement": st.info("Link your existing measurement module here using similar DB logic.")
        elif nav == "Documents": module_docs()
        elif nav == "Settings": module_settings()

if __name__ == "__main__":
    main()
