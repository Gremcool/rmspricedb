import streamlit as st
import pandas as pd
import random

# Set up session state to store uploaded files and search query
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# Function to cache the uploaded file
def cache_uploaded_file(file, file_name):
    if file_name not in st.session_state.uploaded_files:
        st.session_state.uploaded_files[file_name] = pd.read_excel(file)

# Define the main search function
def search_across_files(query, files):
    """
    Search for a query across multiple DataFrames and return matches with file references.

    Parameters:
    - query: The search string.
    - files: Dictionary of file names and their corresponding DataFrames.

    Returns:
    - A DataFrame with rows containing the search query and a column indicating the source file.
    """
    result_df = pd.DataFrame()
    for file_name, data in files.items():
        matches = data[data.apply(lambda row: row.astype(str).str.contains(query, case=False, na=False).any(), axis=1)]
        if not matches.empty:
            matches["Source File"] = file_name  # Add a column indicating the source file
            result_df = pd.concat([result_df, matches], ignore_index=True)
    return result_df

# Define the main page
def main_page():
    st.title("Search Across Excel Files")

    # Upload multiple Excel files
    uploaded_files = st.file_uploader("Upload Excel files", type=["xlsx"], accept_multiple_files=True, key="excel")
    if uploaded_files:
        for file in uploaded_files:
            file_name = file.name.split(".")[0]
            cache_uploaded_file(file, file_name)

    # Search bar
    search_query = st.text_input("Enter your search query:")
    st.session_state.search_query = search_query

    # Display search results
    if search_query and st.session_state.uploaded_files:
        st.subheader("Search Results")
        search_results = search_across_files(search_query, st.session_state.uploaded_files)
        if not search_results.empty:
            st.write(search_results)
        else:
            st.write("No matches found across the uploaded files.")

    # Display uploaded file previews
    if st.session_state.uploaded_files:
        st.subheader("Uploaded File Previews")
        for file_name, data in st.session_state.uploaded_files.items():
            st.write(f"Preview of {file_name}")
            st.write(data.head())

# Main application logic
if __name__ == "__main__":
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Main"], index=0)
    if page == "Main":
        main_page()
