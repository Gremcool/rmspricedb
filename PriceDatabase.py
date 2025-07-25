import streamlit as st
import pandas as pd
import requests
from io import BytesIO
import plotly.express as px

# GitHub URLs and file names
GITHUB_REPO_URL = "https://github.com/Gremcool/gremcool/tree/main/excel_files"
GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/Gremcool/gremcool/main/excel_files"
LOGO_URL = "https://raw.githubusercontent.com/Gremcool/gremcool/main/assets/logo.jpg"

EXCEL_FILE_NAMES = [
    "FINAL MASTER LIST RMS JULY 2024.xlsx",
    "RMS Price list 2025.xlsx",
    "SA Price List 2022.xlsx",
    "Sri Lanka Price List 2024.xlsx",
    "Unicef African Price List.xlsx",
]

# Load and cache Excel files from GitHub
@st.cache_data
def load_files_from_github():
    files = {}
    for file_name in EXCEL_FILE_NAMES:
        file_url = f"{GITHUB_RAW_BASE_URL}/{file_name}"
        response = requests.get(file_url)
        if response.status_code == 200:
            file_data = pd.read_excel(BytesIO(response.content))
            files[file_name] = file_data
        else:
            st.warning(f"Failed to load {file_name}.")
    return files

# Highlight matched search terms
def highlight_matches(data, query):
    return data.style.applymap(
        lambda val: "background-color: yellow" if query.lower() in str(val).lower() else ""
    ).set_table_styles(
        [
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "black"),
                    ("color", "white"),
                    ("font-weight", "bold"),
                    ("text-align", "center"),
                ],
            }
        ]
    )

# Search logic
def search_across_files(query, files):
    result = {}
    query_lower = query.lower()
    for file_name, data in files.items():
        if data is not None:
            matches = data[
                data.astype(str).apply(lambda row: row.str.contains(query_lower, case=False, na=False).any(), axis=1)
            ]
            if not matches.empty:
                result[file_name] = matches
    return result

# Sidebar setup
def add_sidebar(files):
    st.sidebar.image(LOGO_URL, width=200)
    st.sidebar.markdown("**Download Full Excel Files**")
    for file_name, data in files.items():
        towrite = BytesIO()
        data.to_excel(towrite, index=False)
        towrite.seek(0)
        st.sidebar.download_button(
            label=f"Download {file_name}",
            data=towrite,
            file_name=f"{file_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# Plot bar chart of Unit Price (USD) for search result
def plot_price_chart(search_results, query):
    prices = []
    for file_name, df in search_results.items():
        if "Unit Price (USD)" in df.columns:
            filtered = df[
                df.astype(str).apply(lambda row: row.str.contains(query, case=False, na=False).any(), axis=1)
            ]
            for _, row in filtered.iterrows():
                price = row.get("Unit Price (USD)")
                if pd.notna(price):
                    prices.append({
                        "File": file_name,
                        "Unit Price (USD)": float(price),
                        "Item": query,
                    })
                    break  # Take only the first match per file to avoid duplicates

    if prices:
        df_chart = pd.DataFrame(prices)
        fig = px.bar(
            df_chart,
            x="File",
            y="Unit Price (USD)",
            color="File",
            text="Unit Price (USD)",
            title=f"Price Comparison for '{query}'",
            labels={"File": "Price Source File"},
        )
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig.update_layout(yaxis_title="Unit Price (USD)", xaxis_title="", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# Main app
def main():
    st.markdown("""
        <div style='background-color: #50a3f0; padding: 20px; border-radius: 5px; text-align: center; color: white; font-size: 24px;'>
            Welcome to the RMS Price Database!
        </div>
    """, unsafe_allow_html=True)

    uploaded_files = load_files_from_github()
    add_sidebar(uploaded_files)

    search_query = st.text_input("Enter product you want to search:")
    if st.button("Clear Search"):
        search_query = ""

    if search_query:
        st.header("Search Results")
        search_results = search_across_files(search_query, uploaded_files)

        if search_results:
            for file_name, df in search_results.items():
                st.markdown(f"### {file_name}")
                st.write(highlight_matches(df, search_query))
            
            # Show price chart after search results
            st.markdown("---")
            st.subheader("Price Chart")
            plot_price_chart(search_results, search_query)

        else:
            st.warning("No matches found.")
    else:
        st.header("All Files")
        for file_name, data in uploaded_files.items():
            st.markdown(f"### {file_name}")
            st.write(data.head())

if __name__ == "__main__":
    main()
