import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.set_page_config(
    page_title="Rozana CSV Cleaner",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.image("https://firesideventures.com/cdn/shop/files/Logo_of_Rozana_2048x.png?v=1732534274", width=180)
st.sidebar.title("📊 Planning Team")
selected_tab = st.sidebar.radio("Select Task", [
    "Order Summary",
    "Closing Stock Report",
    "LKO Z18",
    "RBL",
    "LKO Temp",
    "FBD"
])

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

def read_uploaded_file(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    else:
        st.warning("Unsupported file type. Please upload a CSV or Excel file.")
        return None

# --- Tab 1: Order Summary ---
if selected_tab == "Order Summary":
    st.header("📦 Order Summary")
    os_file = st.file_uploader("📄 Upload Order_Summary.csv or .xlsx", type=["csv", "xlsx", "xls"])
    sr_file = st.file_uploader("📄 Upload Sales_Returns.csv or .xlsx", type=["csv", "xlsx", "xls"])

    if os_file and sr_file and st.button("🚀 Process Order Summary"):
        df = read_uploaded_file(os_file)
        sr = read_uploaded_file(sr_file)

        if df is None or sr is None:
            st.stop()

        df['WareHouse'] = df['WareHouse'].str.strip().str.lower()
        df = df[df['WareHouse'].str.contains(r'hm1|ls1', na=False)]

        df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
        df['SKU Code'] = df['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)
        df = df[~df['SKU Code'].str.upper().str.startswith(('FR', 'CAP'))]

        excluded_categories = [
            "Accessories", "Apparel", "Asset", "Capex",
            "Clothing And Accessories", "Consumables",
            "Footwears", "Rajeev Colony_CxEC Lite"
        ]
        df = df[~df['SKU Category'].isin(excluded_categories)]
        df = df[~df['Order Reference'].str.lower().str.contains('st', na=False)]
        df = df[~df['Order Status'].str.lower().eq('cancelled')]

        df['Return Qty'] = 0
        df['Return Value'] = 0

        sr['SKU Code'] = sr['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
        sr['SKU Code'] = sr['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)
        sr['Merge'] = sr['Invoice / Challan Number'].astype(str) + sr['SKU Code'].astype(str)

        sr_lookup_agg = sr.groupby('Merge', as_index=False).agg({
            'Quantity': 'sum',
            'Total Credit Note Amount': 'sum'
        })

        df['Merge_temp'] = df['Invoice Number'].astype(str) + df['SKU Code'].astype(str)
        df = df.merge(sr_lookup_agg, left_on='Merge_temp', right_on='Merge', how='left')

        df['Return Qty'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
        df['Return Value'] = pd.to_numeric(df['Total Credit Note Amount'], errors='coerce').fillna(0)
        df = df.drop(columns=['Merge_temp', 'Merge', 'Quantity', 'Total Credit Note Amount'])

        df['Invoice Amount'] = pd.to_numeric(df['Invoice Amount'], errors='coerce').fillna(0)
        df['Invoice Qty'] = pd.to_numeric(df['Invoice Qty'], errors='coerce').fillna(0)

        df['Sales Qty'] = df['Invoice Qty'] - df['Return Qty']
        df['Sales Value'] = df['Invoice Amount'] - df['Return Value']

        df['WareHouse'] = df['WareHouse'].str.upper()
        df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce')
        df['Order Date'] = df['Order Date'].dt.normalize()
        df['Merge'] = df['WareHouse'] + df['SKU Code']

        df_up = df[df['WareHouse'].str.startswith('UP')].copy()
        df_hr = df[df['WareHouse'].str.startswith('HR')].copy()

        today = datetime.today()
        start_of_month = datetime(today.year, today.month, 1)
        df_up_mtd = df_up[df_up['Order Date'] >= start_of_month]
        df_hr_mtd = df_hr[df_hr['Order Date'] >= start_of_month]

        final_columns = ['Merge', 'SKU Code', 'SKU Description', 'Sales Qty', 'Sales Value']

        st.success("✅ Order summary cleaned!")
        st.download_button("⬇️ MTD UP Summary", convert_df(df_up_mtd[final_columns]), "MTD_UP_Order_Summary.csv")
        st.download_button("⬇️ MTD HR Summary", convert_df(df_hr_mtd[final_columns]), "MTD_HR_Order_Summary.csv")

# --- Tab 2: Closing Stock Report ---
elif selected_tab == "Closing Stock Report":
    st.header("🏬 Closing Stock Report")
    cs_file = st.file_uploader("📄 Upload Closing_Stock_Report.csv or .xlsx", type=["csv", "xlsx", "xls"])

    if cs_file and st.button("🚀 Process Closing Stock"):
        df = read_uploaded_file(cs_file)

        if df is None:
            st.stop()

        df['Warehouse'] = df['Warehouse'].str.strip().str.lower()
        df = df[df['Warehouse'].str.contains(r'hm1|ls1', na=False)]
        df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
        df['SKU Code'] = df['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)
        df = df[~df['SKU Code'].str.upper().str.startswith(('FR', 'CAP'))]

        # Remove excluded categories
        excluded_categories = [
            "Accessories", "Apparel", "Asset", "Capex", "Clothing And Accessories", "Consumables", "Footwears", "Rajeev Colony_CxEC Lite"
            ]
        df = df[~df['SKU Category'].isin(excluded_categories)]
        print(f"After SKU Category filter: {df.shape}")

        df['Merge'] = df['Warehouse'].astype(str) + df['SKU Code'].astype(str)

        excluded_zone_keywords = ['damaged_zone', 'damaged', 'DAMAGEZONE', 'expiry', 'qc_zone', 'short']
        zone_pattern = '|'.join([re.escape(z) for z in excluded_zone_keywords])
        df = df[~df['zone'].str.contains(zone_pattern, case=False, na=False)]

        df['Stock Quantity'] = pd.to_numeric(df['Stock Quantity'], errors='coerce').fillna(0)
        df['Stock WAC'] = pd.to_numeric(df['Stock WAC'], errors='coerce').fillna(0)
        df['Final Value'] = df['Stock Quantity'] * df['Stock WAC']

        df_up = df[df['Warehouse'].str.startswith('up')]
        df_hr = df[df['Warehouse'].isin(['hr007_rjv_ls1', 'hr009_pla_ls1'])]

        df_up_grouped = df_up.groupby(['Merge', 'SKU Code', 'SKU Description'], as_index=False).agg({
            'Stock Quantity': 'sum',
            'Final Value': 'sum'
        })

        df_hr_grouped = df_hr.groupby(['Merge', 'SKU Code', 'SKU Description'], as_index=False).agg({
            'Stock Quantity': 'sum',
            'Final Value': 'sum'
        })

        st.success("✅ Closing stock cleaned!")
        st.download_button("⬇️ Download UP Stock", convert_df(df_up_grouped), "UP_Closing_Stock_Report.csv")
        st.download_button("⬇️ Download HR Stock", convert_df(df_hr_grouped), "HR_Closing_Stock_Report.csv")

# --- Tab 3: LKO Z18 ---
elif selected_tab == "LKO Z18":
    st.header("📦 LKO Z18")
    ndr_stock = st.file_uploader("📄 Upload NDR_Stock Detail.csv or .xlsx", type=["csv", "xlsx", "xls"])
    ndr_view = st.file_uploader("📄 Upload NDR_View Order.csv or .xlsx", type=["csv", "xlsx", "xls"])

    if ndr_stock and ndr_view and st.button("🚀 Process LKO Z18"):
        df = read_uploaded_file(ndr_stock)
        view_df = read_uploaded_file(ndr_view)

        if df is None or view_df is None:
            st.stop()

        df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
        df['SKU Code'] = df['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)
        df = df[~df['SKU Code'].str.upper().str.startswith(('CAP', 'FR'))]

        excluded_categories = [
            "Accessories", "Apparel", "Asset", "Capex",
            "Clothing And Accessories", "Consumables",
            "Footwears", "Rajeev Colony_CxEC Lite"
        ]
        df = df[~df['SKU Category'].isin(excluded_categories)]
        df = df[df['Zone'].str.upper() == 'STORAGEZONE18']

        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
        df['Stock Value'] = pd.to_numeric(df['Stock Value'], errors='coerce').fillna(0)

        grouped = df.groupby(['SKU Code', 'SKU Description'], as_index=False).agg({
            'Quantity': 'sum',
            'Stock Value': 'sum'
        })

        grouped['BP'] = grouped['Stock Value'] / grouped['Quantity']

        view_df = view_df[view_df['Customer Name'].str.contains(r'hm1|ls1', case=False, na=False)]
        view_df['SKU Code'] = view_df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
        view_df['SKU Code'] = view_df['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)
        view_df = view_df[~view_df['SKU Code'].str.upper().str.startswith(('CAP', 'FR'))]
        view_df = view_df[~view_df['SKU Category'].isin(excluded_categories)]

        view_df['Open Quantity'] = pd.to_numeric(view_df['Open Quantity'], errors='coerce').fillna(0)
        open_pivot = view_df.groupby('SKU Code', as_index=False)['Open Quantity'].sum()

        merged = grouped.merge(open_pivot, on='SKU Code', how='left')
        merged['Open Quantity'] = merged['Open Quantity'].fillna(0)
        merged['Final Quantity'] = (merged['Quantity'] - merged['Open Quantity']).clip(lower=0)
        merged['Final Value'] = merged['Final Quantity'] * merged['BP']

        final_df = merged[['SKU Code', 'SKU Description', 'Quantity', 'Stock Value', 'BP', 'Open Quantity', 'Final Quantity', 'Final Value']]
        st.success("✅ LKO Z18 stock summary cleaned!")
        st.download_button("⬇️ Download Cleaned LKO Z18", convert_df(final_df), "cleaned_ndr_stock.csv")

# --- Tab 4: RBL ---
elif selected_tab == "RBL":
    st.header("🏢 RBL Stock")
    rbl_file = st.file_uploader("📄 Upload RBL_Stock Detail.csv or .xlsx", type=["csv", "xlsx", "xls"])

    if rbl_file and st.button("🚀 Process RBL Stock"):
        df = read_uploaded_file(rbl_file)

        if df is None:
            st.stop()

        df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
        df['SKU Code'] = df['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)
        df = df[df['Zone'].str.lower() == 'storagezone18']

        excluded_categories = [
            "Accessories", "Apparel", "Asset", "Capex",
            "Clothing And Accessories", "Consumables",
            "Footwears", "Rajeev Colony_CxEC Lite"
        ]
        df = df[~df['SKU Category'].isin(excluded_categories)]
        df = df[~df['SKU Code'].str.upper().str.startswith(('CAP', 'FR'))]

        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
        df['Stock Value'] = pd.to_numeric(df['Stock Value'], errors='coerce').fillna(0)

        grouped_df = df.groupby(['SKU Code', 'SKU Description'], as_index=False).agg({
            'Quantity': 'sum',
            'Stock Value': 'sum'
        })

        st.success("✅ RBL stock summary cleaned!")
        st.download_button("⬇️ Download Cleaned RBL Stock", convert_df(grouped_df), "cleaned_rbl_stock.csv")

# --- Tab 5: LKO Temp ---
elif selected_tab == "LKO Temp":
    st.header("🏷️ LKO Temp")
    temp_file = st.file_uploader("📄 Upload TEMP_Stock Summary.csv or .xlsx", type=["csv", "xlsx", "xls"])

    if temp_file and st.button("🚀 Process TEMP Stock"):
        df = read_uploaded_file(temp_file)

        if df is None:
            st.stop()

        df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
        df['SKU Code'] = df['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)

        excluded_categories = [
            "Accessories", "Apparel", "Asset", "Capex",
            "Clothing And Accessories", "Consumables",
            "Footwears", "Rajeev Colony_CxEC Lite"
        ]
        df = df[~df['SKU Category'].isin(excluded_categories)]
        df = df[~df['SKU Code'].str.upper().str.startswith(('CAP', 'FR'))]

        df['Available Qty'] = pd.to_numeric(df['Available Qty'], errors='coerce').fillna(0)
        df['Open Order Qty'] = pd.to_numeric(df['Open Order Qty'], errors='coerce').fillna(0)
        df['Stock WAC'] = pd.to_numeric(df['Stock WAC'], errors='coerce').fillna(0)

        df['Final Quantity'] = (df['Available Qty'] - df['Open Order Qty']).clip(lower=0)
        df['Final Value'] = df['Final Quantity'] * df['Stock WAC']

        final_df = df[['SKU Code', 'Product Description', 'Final Quantity', 'Final Value']]

        st.success("✅ LKO Temp cleaned!")
        st.download_button("⬇️ Download Cleaned LKO Temp", convert_df(final_df), "cleaned_temp_stock.csv")

# --- Tab 6: FBD ---
elif selected_tab == "FBD":
    st.header("🏬 FBD")
    fbd_stock_file = st.file_uploader("📄 Upload FBD_Stock Detail.csv or .xlsx", type=["csv", "xlsx", "xls"])
    fbd_view_file = st.file_uploader("📄 Upload FBD_View Order.csv or .xlsx", type=["csv", "xlsx", "xls"])

    if fbd_stock_file and fbd_view_file and st.button("🚀 Process FBD Stock"):
        df = read_uploaded_file(fbd_stock_file)
        view_df = read_uploaded_file(fbd_view_file)

        if df is None or view_df is None:
            st.stop()

        df['SKU Code'] = df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
        df['SKU Code'] = df['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)

        excluded_categories = [
            "Accessories", "Apparel", "Asset", "Capex",
            "Clothing And Accessories", "Consumables",
            "Footwears", "Rajeev Colony_CxEC Lite"
        ]
        df = df[~df['SKU Category'].isin(excluded_categories)]
        df = df[~df['SKU Code'].str.upper().str.startswith(('CAP', 'FR'))]
        df = df[df['Zone'].str.upper() == 'STORAGEZONE18']

        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
        df['Stock Value'] = pd.to_numeric(df['Stock Value'], errors='coerce').fillna(0)

        df_subset = df[['SKU Code', 'SKU Description', 'Quantity', 'Stock Value']]
        grouped = df_subset.groupby(['SKU Code', 'SKU Description'], as_index=False).agg({
            'Quantity': 'sum',
            'Stock Value': 'sum'
        })
        grouped['BP'] = grouped['Stock Value'] / grouped['Quantity']

        view_df = view_df[view_df['Customer Name'].str.contains(r'hm1|ls1', case=False, na=False)]
        view_df['SKU Code'] = view_df['SKU Code'].str.replace(r'(?i)loose', '', regex=True)
        view_df['SKU Code'] = view_df['SKU Code'].str.replace(r'[^A-Za-z0-9]', '', regex=True)
        view_df = view_df[~view_df['SKU Category'].isin(excluded_categories)]
        view_df = view_df[~view_df['SKU Code'].str.upper().str.startswith(('CAP', 'FR'))]

        view_df['Open Quantity'] = pd.to_numeric(view_df['Open Quantity'], errors='coerce').fillna(0)
        open_pivot = view_df.groupby('SKU Code', as_index=False)['Open Quantity'].sum()

        merged = grouped.merge(open_pivot, on='SKU Code', how='left')
        merged['Open Quantity'] = merged['Open Quantity'].fillna(0)
        merged['Final Quantity'] = (merged['Quantity'] - merged['Open Quantity']).clip(lower=0)
        merged['Final Value'] = merged['Final Quantity'] * merged['BP']

        final_df = merged[['SKU Code', 'SKU Description', 'Quantity', 'Stock Value', 'BP', 'Open Quantity', 'Final Quantity', 'Final Value']]

        st.success("✅ FBD stock summary cleaned!")
        st.download_button("⬇️ Download Cleaned FBD Stock", convert_df(final_df), "cleaned_fbd_stock.csv")