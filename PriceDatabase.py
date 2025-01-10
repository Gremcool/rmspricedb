import streamlit as st
import pandas as pd
import random

# Function to style DataFrame and highlight matches
def highlight_matches(data, query):
    """Highlight cells containing the search query in yellow and return the column indices."""
    column_indices = set()
    
    # Apply highlights and collect matching column indices
    styled_data = data.style.applymap(
        lambda val: "background-color: yellow" if query.lower() in str(val).lower() else ""
    )
    for col in data.columns:
        if data[col].astype(str).str.contains(query, case=False, na=False).any():
            column_indices.add(data.columns.get_loc(col))
    return styled_data, sorted(column_indices)

# Function to search across files and return highlighted results
def search_across_files(query, files):
    """Search for the query in all uploaded files and return highlighted results with column indices."""
    results = {}
    for file_name, data in files.items():
        matches = data[data.apply(lambda row: row.astype(str).str.contains(query, case=False, na=False).any(), axis=1)]
        if not matches.empty:
            styled_data, matching_columns = highlight_matches(matches, query)
            results[file_name] = (styled_data, matching_columns)
    return results

# Display search results with automatic scrolling
def display_search_results(search_results):
    """Display search results and automatically scroll to the first highlighted column."""
    for file_name, (styled_data, matching_columns) in search_results.items():
        # Random background color for the section header
        title_bg_color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        
        st.markdown(f"<div class='header' style='background-color: {title_bg_color};'>{file_name}</div>", unsafe_allow_html=True)
        st.write(styled_data)

        # Embed JavaScript for scrolling
        if matching_columns:
            first_col = matching_columns[0]  # Scroll to the first matching column
            js_code = f"""
            <script>
            const table = document.querySelectorAll('div[data-testid="stDataFrame"] table')[
                document.querySelectorAll('div[data-testid="stDataFrame"] table').length - 1
            ];
            table.parentElement.scrollLeft = {first_col * 150};  // Approximate column width
            </script>
            """
            st.components.v1.html(js_code, height=0)

# Define the main page
def main_page():
    st.title("Search Across Excel Files")

    # Upload multiple Excel files
    st.header("Upload Excel Files")
    uploaded_files = st.file_uploader("Upload Excel files", type=["xlsx"], accept_multiple_files=True, key="excel")
    if uploaded_files:
        for file in uploaded_files:
            file_name = file.name.split(".")[0]  # Use file name as header
            if file_name not in st.session_state.uploaded_files:
                st.session_state.uploaded_files[file_name] = pd.read_excel(file)

    # Predictive search bar
    search_query = st.text_input("Enter your search query:", key="search")
    st.session_state.search_query = search_query

    # Clear search button
    if st.button("Clear Search"):
        st.session_state.search_query = ""

    # Display search results
    if st.session_state.search_query:
        search_results = search_across_files(st.session_state.search_query, st.session_state.uploaded_files)
        if search_results:
            display_search_results(search_results)
        else:
            st.write("No matches found across the uploaded files.")
    else:
        # Display uploaded files if no search query is entered
        if st.session_state.uploaded_files:
            for file_name, data in st.session_state.uploaded_files.items():
                title_bg_color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                st.markdown(f"<div class='header' style='background-color: {title_bg_color};'>{file_name}</div>", unsafe_allow_html=True)
                st.write(data.head())  # Display preview of the file

main_page()
