import streamlit as st
import pandas as pd
import random

# Set up session state to store uploaded files and search query
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "uploaded_logo" not in st.session_state:
    st.session_state.uploaded_logo = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# Function to cache the uploaded files
def cache_uploaded_file(file, file_name):
    if file_name not in st.session_state.uploaded_files:
        st.session_state.uploaded_files[file_name] = pd.read_excel(file)

# Function to highlight matches in the DataFrame
def highlight_matches(data, query):
    """Highlight cells containing the search query in yellow and return HTML with scroll functionality."""
    
    # Create a style for highlighting
    highlighted_html = data.to_html(classes="table table-bordered", escape=False)
    
    # Highlight the matching cells in yellow and add an ID for scroll
    highlighted_html = highlighted_html.replace(
        "<td>", "<td style='background-color: white;'>"
    )  # Default background to white
    highlighted_html = highlighted_html.replace(
        f">{query.lower()}<", f" style='background-color: yellow;'>{query.lower()}<"
    )  # Highlight matching text in yellow
    
    # Add JavaScript to scroll to the first yellow-highlighted cell
    highlighted_html = f"""
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const firstYellowCell = document.querySelector('td[style*="background-color: yellow"]');
            if (firstYellowCell) {{
                firstYellowCell.scrollIntoView({{
                    behavior: 'smooth',
                    block: 'center'
                }});
            }}
        }});
        </script>
        {highlighted_html}
    """
    
    return highlighted_html

# Function to search across files and highlight results
def search_across_files(query, files):
    """Search for the query in all uploaded files and return highlighted results."""
    result = {}
    for file_name, data in files.items():
        matches = data[data.apply(lambda row: row.astype(str).str.contains(query, case=False, na=False).any(), axis=1)]
        if not matches.empty:
            result[file_name] = highlight_matches(matches, query)
    return result

# Function for the Admin page
def admin_page():
    st.title("Admin Page")
    st.sidebar.header("Admin Controls")

    # Upload RMS logo
    logo = st.sidebar.file_uploader("Upload RMS Logo", type=["png", "jpg", "jpeg"], key="logo")
    if logo is not None:
        st.session_state.uploaded_logo = logo

    # Upload multiple Excel files
    st.header("Upload Excel Files")
    uploaded_files = st.file_uploader("Upload Excel files", type=["xlsx"], accept_multiple_files=True, key="excel")
    if uploaded_files:
        for file in uploaded_files:
            file_name = file.name.split(".")[0]  # Use file name as header
            cache_uploaded_file(file, file_name)

# Function for the Main page
def main_page():
    # Apply custom styling for a polished design
    st.markdown(
        """
        <style>
        body {
            background-color: #eaf4fc;
            color: #333;
            font-family: 'Helvetica Neue', sans-serif;
        }
        .stApp {
            padding: 20px;
            border-radius: 10px;
        }
        .header {
            color: white;
            padding: 15px;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Display logo if uploaded
    if st.session_state.uploaded_logo is not None:
        st.image(st.session_state.uploaded_logo, width=150, output_format="PNG")

    # Page title
    st.markdown("<div class='page-title'>Search Price Lists</div>", unsafe_allow_html=True)

    # Predictive search bar
    search_query = st.text_input("Enter your search query:", key="search")
    st.session_state.search_query = search_query

    # Clear search button
    if st.button("Clear Search"):
        st.session_state.search_query = ""

    # Display search results or uploaded files
    if st.session_state.search_query:
        st.markdown("<div class='search-results-header'>Search Results</div>", unsafe_allow_html=True)
        search_results = search_across_files(st.session_state.search_query, st.session_state.uploaded_files)
        if search_results:
            for file_name, styled_data in search_results.items():
                title_bg_color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                st.markdown(f"<div class='header' style='background-color: {title_bg_color};'>{file_name}</div>", unsafe_allow_html=True)
                st.markdown(styled_data, unsafe_allow_html=True)
        else:
            st.write("No matches found across the uploaded files.")
    else:
        if st.session_state.uploaded_files:
            for file_name, data in st.session_state.uploaded_files.items():
                title_bg_color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                st.markdown(f"<div class='header' style='background-color: {title_bg_color};'>{file_name}</div>", unsafe_allow_html=True)
                st.write(data.head())  # Show preview of the uploaded files

# Navigation menu with Main Page as default
page = st.sidebar.selectbox("Choose a page", ["Main", "Admin"], index=0)
if page == "Admin":
    admin_page()
else:
    main_page()
