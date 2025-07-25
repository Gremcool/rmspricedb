import streamlit as st
import pandas as pd
import requests
from io import BytesIO
import altair as alt

# --- Constants ---
GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/Gremcool/gremcool/main/excel_files"
LOGO_URL = "https://raw.githubusercontent.com/Gremcool/gremcool/main/assets/logo.jpg"

EXCEL_FILE_NAMES = [
    "FINAL MASTER LIST RMS JULY 2024.xlsx",
    "RMS Price list 2025.xlsx",
    "SA Price List 2022.xlsx",
    "Sri Lanka Price List 2024.xlsx",
    "Unicef African Price List.xlsx",
]

# --- Load Excel Files from GitHub ---
@st.cache_data
def load_files_from_github():
    files = {}
    for file_name in EXCEL_FILE_NAMES:
        file_url = f"{GITHUB_RAW_BASE_URL}/{file_name}"
        response = requests.get(file_url)
        if response.status_code == 200:
            df = pd.read_excel(BytesIO(response.content))
            files[file_name] = df
        else:
            st.warning(f"⚠️ Could not load {file_name}")
    return files

# --- Highlight matches in table ---
def highlight_matches(data, query):
    return data.style.applymap(
        lambda val: "background-color: yellow" if query.lower() in str(val).lower() else ""
    ).set_table_styles([
        {
            "selector": "thead th",
            "props": [
                ("background-color", "black"),
                ("color", "white"),
                ("font-weight", "bold"),
                ("text-align", "center"),
            ],
        }
    ])

# --- Search all files ---
def search_across_files(query, files):
    result = {}
    query_lower = query.lower()
    for file_name, df in files.items():
        matches = df[df.astype(str).apply(lambda row: row.str.contains(query_lower, case=False, na=False).any(), axis=1)]
        if not matches.empty:
            result[file_name] = highlight_matches(matches, query)
    return result

# --- Sidebar: logo + download buttons ---
def add_sidebar(files):
    st.sidebar.image(LOGO_URL, width=200)
    st.sidebar.markdown("### 📥 Download Full Excel Files")
    for file_name, df in files.items():
        towrite = BytesIO()
        df.to_excel(towrite, index=False, sheet_name="Sheet1")
        towrite.seek(0)
        st.sidebar.download_button(
            label=f"Download {file_name}",
            data=towrite,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# --- Show elegant graph for matched item prices ---
def show_price_graph(search_results, price_column="Unit Price (USD)", product_column="Product Name", unit_column="Unit"):
    price_data = []

    for file_name, styled_data in search_results.items():
        df = styled_data.data if hasattr(styled_data, 'data') else styled_data.copy()

        if price_column in df.columns:
            try:
                prod_col = product_column if product_column in df.columns else df.columns[0]
                unit_col = unit_column if unit_column in df.columns else None

                df[price_column] = pd.to_numeric(df[price_column], errors="coerce")
                df = df.dropna(subset=[price_column])

                for _, row in df.iterrows():
                    price_data.append({
                        "File": file_name,
                        "Product": str(row.get(prod_col, "N/A")),
                        "Price (USD)": round(row[price_column], 2),
                        "Unit": str(row.get(unit_col, "N/A")) if unit_col else "N/A",
                    })

            except Exception as e:
                st.warning(f"Error processing {file_name}: {e}")

    if price_data:
        df_plot = pd.DataFrame(price_data)
        df_plot.sort_values("Price (USD)", ascending=False, inplace=True)

        st.markdown("### 📊 Price Comparison of Searched Item Across Files")

        chart = alt.Chart(df_plot).mark_bar(size=25).encode(
            x=alt.X("File:N", title="File", sort="-y"),
            y=alt.Y("Price (USD):Q", title="Price (USD)"),
            color=alt.Color("File:N", legend=None),
            tooltip=[
                alt.Tooltip("File", title="Source File"),
                alt.Tooltip("Product", title="Product Name"),
                alt.Tooltip("Price (USD):Q", title="Price"),
                alt.Tooltip("Unit", title="Unit"),
            ],
        ).properties(width=800, height=400)

        st.altair_chart(chart, use_container_width=True)

        with st.expander("🔍 View Chart Data"):
            st.dataframe(df_plot, use_container_width=True)
    else:
        st.info("No valid price data found for the searched item.")

# --- Main App ---
def main():
    st.markdown("""
        <div style='background-color: #50a3f0; padding: 20px; border-radius: 5px; text-align: center; color: white; font-size: 24px;'>
            💊 Welcome to the RMS Price Database!
        </div>
    """, unsafe_allow_html=True)

    uploaded_files = load_files_from_github()
    add_sidebar(uploaded_files)

    search_query = st.text_input("🔍 Enter product name to search:")

    if st.button("Clear Search"):
        search_query = ""

    if search_query:
        st.header("🔎 Search Results")
        search_results = search_across_files(search_query, uploaded_files)
        if search_results:
            for file_name, styled_data in search_results.items():
                st.markdown(f"#### 📁 {file_name}")
                st.write(styled_data)

            st.markdown("---")
            show_price_graph(search_results, price_column="Unit Price (USD)")
        else:
            st.warning("No matches found.")
    else:
        st.header("📂 Preview of All Files")
        for file_name, df in uploaded_files.items():
            st.markdown(f"#### 📁 {file_name}")
            st.write(df.head())

# --- Run App ---
if __name__ == "__main__":
    main()
