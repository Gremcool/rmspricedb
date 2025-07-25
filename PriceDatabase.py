import streamlit as st
import pandas as pd
import zipfile
import io
import re
import requests
import plotly.express as px

st.set_page_config(page_title="💊 Price Database Search", layout="wide")
st.title("💊 Price Database Explorer")

@st.cache_data
def load_excel_file_from_github(file_url):
    response = requests.get(file_url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        file_data = {}
        for file in z.namelist():
            if file.endswith(".xlsx") or file.endswith(".xls"):
                with z.open(file) as f:
                    xls = pd.ExcelFile(f)
                    for sheet_name in xls.sheet_names:
                        df = xls.parse(sheet_name)
                        file_data[file] = df
                        break  # Only take the first sheet
        return file_data

def highlight_matches(val, pattern):
    if pd.isna(val):
        return ""
    try:
        val_str = str(val)
        match = re.search(pattern, val_str, flags=re.IGNORECASE)
        if match:
            return val_str.replace(match.group(0), f"🟨**{match.group(0)}**")
        return val_str
    except Exception:
        return str(val)

def search_data(file_data, search_term):
    if not search_term:
        return {}

    search_results = {}
    pattern = re.escape(search_term)
    for file_name, df in file_data.items():
        mask = df.apply(lambda row: row.astype(str).str.contains(pattern, case=False, na=False)).any(axis=1)
        filtered_df = df[mask]
        if not filtered_df.empty:
            styled_df = filtered_df.copy()
            styled_df = styled_df.applymap(lambda val: highlight_matches(val, pattern))
            search_results[file_name] = styled_df
    return search_results

def show_price_graph(search_results, price_column="Unit Price (USD)", product_column="Product Name", unit_column="Unit"):
    price_data = []

    for file_name, styled_data in search_results.items():
        df = styled_data.data if hasattr(styled_data, 'data') else styled_data.copy()

        if price_column in df.columns:
            df = df.dropna(subset=[price_column])
            df[price_column] = pd.to_numeric(df[price_column], errors="coerce")
            df = df.dropna(subset=[price_column])

            for _, row in df.iterrows():
                product = str(row.get(product_column, "N/A"))
                price = row[price_column]
                unit = str(row.get(unit_column, "N/A")) if unit_column in df.columns else "N/A"

                price_data.append({
                    "File": file_name,
                    "Product": product,
                    "Price (USD)": round(price, 2),
                    "Unit": unit,
                })

    if not price_data:
        st.info("🔍 No valid price data found for the searched item.")
        return

    df_plot = pd.DataFrame(price_data)
    df_plot = df_plot.sort_values("Price (USD)", ascending=False)

    fig = px.bar(
        df_plot,
        x="File",
        y="Price (USD)",
        color="File",
        hover_data=["Product", "Unit"],
        text="Price (USD)",
        title="💲 Price Comparison Chart",
        labels={"File": "Excel File", "Price (USD)": "Unit Price (USD)"},
    )

    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig.update_layout(
        height=500,
        showlegend=False,
        xaxis_title="Source File",
        yaxis_title="Price (USD)",
        font=dict(size=14),
        bargap=0.3
    )

    st.markdown("<div id='price-chart'></div>", unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🧾 View Matching Price Data"):
        st.dataframe(df_plot, use_container_width=True)

# --- MAIN APP ---
st.sidebar.header("📁 File Source")
github_url = st.sidebar.text_input("Enter GitHub ZIP URL:", value="https://github.com/nsongaphilip/pricedbtest/raw/main/datastore.zip")

with st.sidebar:
    if st.button("🔄 Reload Files"):
        st.cache_data.clear()

file_data = load_excel_file_from_github(github_url)
file_names = list(file_data.keys())

st.sidebar.markdown("### 🔍 Search")
search_term = st.sidebar.text_input("Search by medicine name or keyword:")

# 👉 Scroll Button
if search_term:
    st.sidebar.markdown(
        """
        <a href="#price-chart">
            <button style="background-color:#1f77b4;color:white;padding:8px 16px;border:none;border-radius:6px;cursor:pointer;">
                📉 Go to Chart
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

if search_term:
    search_results = search_data(file_data, search_term)
    if search_results:
        st.subheader(f"🔎 Search Results for: `{search_term}`")
        show_price_graph(search_results)

        for file_name, df in search_results.items():
            st.markdown(f"#### 📄 Results in: `{file_name}`")
            st.dataframe(df, use_container_width=True)
    else:
        st.warning("❌ No matches found for your search.")
else:
    st.info("👈 Enter a search term in the sidebar to begin.")
    st.markdown("### 📂 Available Files")
    for file_name in file_names:
        st.markdown(f"- {file_name}")
