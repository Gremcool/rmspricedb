import streamlit as st
import pandas as pd
import random
import requests
from io import BytesIO

# GitHub repository URL where Excel files are stored
GITHUB_REPO_URL = "https://github.com/Gremcool/gremcool/tree/main/excel_files"

# Raw GitHub content base URL
GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/Gremcool/gremcool/main/excel_files"

# Logo URL from GitHub
LOGO_URL = "https://raw.githubusercontent.com/Gremcool/gremcool/main/assets/logo.jpg"

# List of filenames to load from the GitHub repository
EXCEL_FILE_NAMES = [
    "FINAL MASTER LIST RMS JULY 2024.xlsx",
    "RMS Price list 2025.xlsx",
    "SA Price List 2022.xlsx",
    "Sri Lanka Price List 2024.xlsx",
    "Unicef African Price List.xlsx",  # Add all your file names here
]

# Function to fetch and cache Excel files from GitHub
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
            st.warning(f"Failed to load {file_name} from GitHub. Please check the URL.")
    return files

# Function to style DataFrame and highlight matches
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

# Optimized search function
def search_across_files(query, files):
    result = {}
    query_lower = query.lower()
    for file_name, data in files.items():
        matches = data[data.astype(str).apply(lambda row: row.str.contains(query_lower, case=False, na=False).any(), axis=1)]
        if not matches.empty:
            result[file_name] = highlight_matches(matches, query)
    return result

# Function to add a sidebar for logo and downloading Excel files
def add_sidebar(files):
    st.sidebar.image(LOGO_URL, width=200)
    st.sidebar.markdown("**Download Full Excel Files**")
    
    for file_name, data in files.items():
        towrite = BytesIO()
        data.to_excel(towrite, index=False, sheet_name="Sheet1")
        towrite.seek(0)
        st.sidebar.download_button(
            label=f"Download {file_name}",
            data=towrite,
            file_name=f"{file_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# Main function for the app
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
            for file_name, styled_data in search_results.items():
                st.markdown(f"### {file_name}")
                st.write(styled_data)
        else:
            st.write("No matches found.")
    else:
        st.header("All Files")
        for file_name, data in uploaded_files.items():
            st.markdown(f"### {file_name}")
            st.write(data.head())

if __name__ == "__main__":
    main()
