import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.set_page_config(
    page_title="Rozana CSV Cleaner",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔁 File loader that supports CSV and Excel
def load_file(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        return pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(uploaded_file)
    else:
        return None

# 📤 CSV export helper
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# Sidebar UI
st.sidebar.image("https://firesideventures.com/cdn/shop/files/Logo_of_Rozana_2048x.png?v=1732534274", width=180)
st.sidebar.title("📊 Rozana Automation")
selected_tab = st.sidebar.radio("Select Task", [
    "Order Summary Cleaner",
    "Closing Stock Report",
    "LKO Z18 Report",
    "RBL Report",
    "TEMP Stock Summary",
    "FBD Stock Report"
])

# Optional Dark Mode
dark_mode = st.sidebar.toggle("🌙 Dark Mode", value=False)
if dark_mode:
    st.markdown("""
        <style>
            body, .stApp { background-color: #1e1e1e; color: white; }
            .stButton>button { background-color: #444; color: white; border: 1px solid #999; }
        </style>
    """, unsafe_allow_html=True)

# --- Tab 1: Order Summary Cleaner ---
if selected_tab == "Order Summary Cleaner":
    st.header("📦 Order Summary Cleaner")
    os_file = st.file_uploader("📄 Upload Order_Summary (CSV or Excel)", type=["csv", "xlsx", "xls"], key="os")
    sr_file = st.file_uploader("📄 Upload Sales_Returns (CSV or Excel)", type=["csv", "xlsx", "xls"], key="sr")

    if os_file and sr_file and st.button("🚀 Process Order Summary"):
        with st.spinner("Cleaning order summary..."):
            df = load_file(os_file)
            sr = load_file(sr_file)

            df['WareHouse'] = df['WareHouse'].str.strip().str.lower()
            df = df[df['WareHouse'].str.contains(r'hm1|ls1', na=False)]
            df = df[~df['Order Reference'].str.lower().str.contains('st')]
            df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
            df['SKU Code'] = df['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)
            df = df[~df['Order Status'].str.lower().eq('cancelled')]

            sr['SKU Code'] = sr['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
            sr['SKU Code'] = sr['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)
            sr['Merge'] = sr['Invoice / Challan Number'].astype(str) + sr['SKU Code'].astype(str)
            df['Merge_temp'] = df['Invoice Number'].astype(str) + df['SKU Code'].astype(str)
            df = df.merge(sr[['Merge', 'Quantity', 'Total Credit Note Amount']], left_on='Merge_temp', right_on='Merge', how='left')
            df['Return Qty'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
            df['Return Value'] = pd.to_numeric(df['Total Credit Note Amount'], errors='coerce').fillna(0)
            df = df.drop(columns=['Merge_temp', 'Merge', 'Quantity', 'Total Credit Note Amount'])

            for col in ['Invoice Number', 'Invoice Amount', 'Invoice Qty']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            df['Sales Qty'] = df['Invoice Qty'] - df['Return Qty']
            df['Sales Value'] = df['Invoice Amount'] - df['Return Value']
            df['WareHouse'] = df['WareHouse'].str.upper()
            df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce').dt.normalize()
            df['Merge'] = df['WareHouse'] + df['SKU Code']

            today = datetime.today()
            start_month = datetime(today.year, today.month, 1)
            final_cols = ['Merge', 'SKU Code', 'SKU Description', 'Sales Qty', 'Sales Value']

            df_up = df[df['WareHouse'].str.startswith('UP') & (df['Order Date'] >= start_month)][final_cols]
            df_hr = df[df['WareHouse'].str.startswith('HR') & (df['Order Date'] >= start_month)][final_cols]

            st.success("✅ Order summary cleaned!")
            st.download_button("⬇️ MTD UP Summary", convert_df(df_up), "MTD_UP_Order_Summary.csv")
            st.download_button("⬇️ MTD HR Summary", convert_df(df_hr), "MTD_HR_Order_Summary.csv")

# --- Tab 2: Closing Stock Report ---
elif selected_tab == "Closing Stock Report":
    st.header("🏬 Closing Stock Report")
    file = st.file_uploader("📄 Upload Closing Stock (CSV or Excel)", type=["csv", "xlsx", "xls"], key="csr")

    if file and st.button("🚀 Process Closing Stock"):
        with st.spinner("Cleaning closing stock report..."):
            df = load_file(file)
            df['Warehouse'] = df['Warehouse'].str.strip().str.upper()
            df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
            df['SKU Code'] = df['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)
            df = df[df['Warehouse'].str.contains(r'HM1|LS1', na=False)]
            excluded_categories = ["Accessories", "Apparel", "Asset", "Capex", "Clothing And Accessories", "Consumables", "Footwears", "Rajeev Colony_CxEC Lite"]
            df = df[~df['SKU Category'].isin(excluded_categories)]
            df = df[~df['zone'].str.contains(r'damaged|expiry|qc_zone|short', case=False, na=False)]
            df['Stock Quantity'] = pd.to_numeric(df['Stock Quantity'], errors='coerce').fillna(0)
            df['Stock WAC'] = pd.to_numeric(df['Stock WAC'], errors='coerce').fillna(0)
            df['Final Value'] = df['Stock Quantity'] * df['Stock WAC']
            df = df[['SKU Code', 'Stock Quantity', 'Stock WAC', 'Final Value', 'Warehouse']]
            df_up = df[df['Warehouse'].str.startswith('UP')]
            df_hr = df[df['Warehouse'].isin(['HR007_RJV_LS1', 'HR009_PLA_LS1'])]
            st.success("✅ Closing stock cleaned!")
            st.download_button("⬇️ Download UP Stock", convert_df(df_up), "UP_Closing_Stock_Report.csv")
            st.download_button("⬇️ Download HR Stock", convert_df(df_hr), "HR_Closing_Stock_Report.csv")

# --- Tab 3: LKO Z18 ---
elif selected_tab == "LKO Z18 Report":
    st.header("📦 LKO Z18 Report")
    ndr_stock = st.file_uploader("📄 Upload NDR_Stock Detail (CSV or Excel)", type=["csv", "xlsx", "xls"])
    ndr_view = st.file_uploader("📄 Upload NDR_View Order (CSV or Excel)", type=["csv", "xlsx", "xls"])

    if ndr_stock and ndr_view and st.button("🚀 Process LKO Z18"):
        with st.spinner("Processing LKO Z18 report..."):
            df = load_file(ndr_stock)
            view_df = load_file(ndr_view)
            df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
            excluded_categories = ["Accessories", "Apparel", "Asset", "Capex", "Clothing And Accessories", "Consumables", "Footwears", "Rajeev Colony_CxEC Lite"]
            df = df[~df['SKU Category'].isin(excluded_categories)]
            df = df[df['Zone'].str.upper() == 'STORAGEZONE18']
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
            df['Stock Value'] = pd.to_numeric(df['Stock Value'], errors='coerce').fillna(0)
            grouped = df.groupby('SKU Code', as_index=False).agg({'Quantity': 'sum', 'Stock Value': 'sum'})
            grouped['BP'] = grouped['Stock Value'] / grouped['Quantity']

            view_df = view_df[view_df['Customer Name'].str.contains(r'hm1|ls1', case=False, na=False)]
            view_df['SKU Code'] = view_df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
            view_df = view_df[~view_df['SKU Category'].isin(excluded_categories)]
            view_df['Open Quantity'] = pd.to_numeric(view_df['Open Quantity'], errors='coerce').fillna(0)
            open_pivot = view_df.groupby('SKU Code', as_index=False)['Open Quantity'].sum()

            merged = grouped.merge(open_pivot, on='SKU Code', how='left')
            merged['Open Quantity'] = merged['Open Quantity'].fillna(0)
            merged['Final Quantity'] = (merged['Quantity'] - merged['Open Quantity']).clip(lower=0)
            merged['Final Value'] = merged['Final Quantity'] * merged['BP']
            final_df = merged[['SKU Code', 'Quantity', 'Stock Value', 'BP', 'Open Quantity', 'Final Quantity', 'Final Value']]
            st.success("✅ LKO Z18 cleaned!")
            st.download_button("⬇️ Download Cleaned LKO Z18", convert_df(final_df), "cleaned_ndr_stock.csv")

# --- Tab 4: RBL ---
elif selected_tab == "RBL Report":
    st.header("🏭 RBL Stock Report")
    rbl_file = st.file_uploader("📄 Upload RBL_Stock Detail (CSV or Excel)", type=["csv", "xlsx", "xls"])

    if rbl_file and st.button("🚀 Process RBL Stock"):
        with st.spinner("Processing RBL report..."):
            df = load_file(rbl_file)
            df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
            df = df[df['Zone'].str.lower() == 'storagezone18']
            excluded_categories = ["Accessories", "Apparel", "Asset", "Capex", "Clothing And Accessories", "Consumables", "Footwears", "Rajeev Colony_CxEC Lite"]
            df = df[~df['SKU Category'].isin(excluded_categories)]
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
            df['Stock Value'] = pd.to_numeric(df['Stock Value'], errors='coerce').fillna(0)
            result_df = df.groupby('SKU Code', as_index=False).agg({'Quantity': 'sum', 'Stock Value': 'sum'})
            st.success("✅ RBL stock cleaned!")
            st.download_button("⬇️ Download Cleaned RBL Stock", convert_df(result_df), "cleaned_rbl_stock.csv")

# --- Tab 5: TEMP ---
elif selected_tab == "TEMP Stock Summary":
    st.header("🌡 TEMP Stock Summary")
    temp_file = st.file_uploader("📄 Upload TEMP_Stock Summary (CSV or Excel)", type=["csv", "xlsx", "xls"])

    if temp_file and st.button("🚀 Process TEMP Summary"):
        with st.spinner("Processing TEMP stock summary..."):
            df = load_file(temp_file)
            df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
            excluded_categories = ["Accessories", "Apparel", "Asset", "Capex", "Clothing And Accessories", "Consumables", "Footwears", "Rajeev Colony_CxEC Lite"]
            df = df[~df['SKU Category'].isin(excluded_categories)]
            df['Available Qty'] = pd.to_numeric(df['Available Qty'], errors='coerce').fillna(0)
            df['Open Order Qty'] = pd.to_numeric(df['Open Order Qty'], errors='coerce').fillna(0)
            df['Stock WAC'] = pd.to_numeric(df['Stock WAC'], errors='coerce').fillna(0)
            df['Final Quantity'] = (df['Available Qty'] - df['Open Order Qty']).clip(lower=0)
            df['Final Value'] = df['Final Quantity'] * df['Stock WAC']
            result_df = df[['SKU Code', 'Final Quantity', 'Final Value']]
            st.success("✅ TEMP stock summary cleaned!")
            st.download_button("⬇️ Download Cleaned TEMP Stock", convert_df(result_df), "cleaned_temp_stock.csv")

# --- Tab 6: FBD ---
elif selected_tab == "FBD Stock Report":
    st.header("🏢 FBD Stock Report")
    fbd_stock = st.file_uploader("📄 Upload FBD_Stock Detail (CSV or Excel)", type=["csv", "xlsx", "xls"])
    fbd_view = st.file_uploader("📄 Upload FBD_View Order (CSV or Excel)", type=["csv", "xlsx", "xls"])

    if fbd_stock and fbd_view and st.button("🚀 Process FBD Stock"):
        with st.spinner("Processing FBD stock report..."):
            df = load_file(fbd_stock)
            view_df = load_file(fbd_view)
            df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
            excluded_categories = ["Accessories", "Apparel", "Asset", "Capex", "Clothing And Accessories", "Consumables", "Footwears", "Rajeev Colony_CxEC Lite"]
            df = df[~df['SKU Category'].isin(excluded_categories)]
            df = df[df['Zone'].str.upper() == 'STORAGEZONE18']
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
            df['Stock Value'] = pd.to_numeric(df['Stock Value'], errors='coerce').fillna(0)
            grouped = df.groupby('SKU Code', as_index=False).agg({'Quantity': 'sum', 'Stock Value': 'sum'})
            grouped['BP'] = grouped['Stock Value'] / grouped['Quantity']

            view_df = view_df[view_df['Customer Name'].str.contains(r'hm1|ls1', case=False, na=False)]
            view_df['SKU Code'] = view_df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
            view_df = view_df[~view_df['SKU Category'].isin(excluded_categories)]
            view_df['Open Quantity'] = pd.to_numeric(view_df['Open Quantity'], errors='coerce').fillna(0)
            open_pivot = view_df.groupby('SKU Code', as_index=False)['Open Quantity'].sum()

            merged = grouped.merge(open_pivot, on='SKU Code', how='left')
            merged['Open Quantity'] = merged['Open Quantity'].fillna(0)
            merged['Final Quantity'] = (merged['Quantity'] - merged['Open Quantity']).clip(lower=0)
            merged['Final Value'] = merged['Final Quantity'] * merged['BP']
            final_df = merged[['SKU Code', 'Quantity', 'Stock Value', 'BP', 'Open Quantity', 'Final Quantity', 'Final Value']]
            st.success("✅ FBD stock summary cleaned!")
            st.download_button("⬇️ Download Cleaned FBD Stock", convert_df(final_df), "cleaned_fbd_stock.csv")
