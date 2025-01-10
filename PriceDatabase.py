import streamlit as st
import pandas as pd

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

# Function to style the DataFrame with fixed column width
def style_headers_fixed_width(df, cell_width=100):
    """
    Apply styles to the DataFrame with a fixed cell width.

    Parameters:
    - df: The input DataFrame.
    - cell_width: The desired fixed width for columns, in pixels.
    """
    return df.style.set_table_styles(
        [
            # Style for table headers
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "black"),
                    ("color", "white"),
                    ("font-weight", "bold"),
                    ("text-align", "center"),
                    ("font-size", "12px"),
                    ("padding", "2px 5px"),
                    ("height", "15px"),
                    ("white-space", "nowrap"),
                    (f"width", f"{cell_width}px"),
                    (f"max-width", f"{cell_width}px"),
                    ("overflow", "hidden"),
                    ("text-overflow", "ellipsis"),
                ],
            },
            # Style for table cells
            {
                "selector": "td",
                "props": [
                    ("text-align", "left"),
                    ("padding", "2px 5px"),
                    ("height", "15px"),
                    ("white-space", "nowrap"),
                    (f"width", f"{cell_width}px"),
                    (f"max-width", f"{cell_width}px"),
                    ("overflow", "hidden"),
                    ("text-overflow", "ellipsis"),
                ],
            },
        ]
    )

# Display table with fixed width in Streamlit
def display_table_with_fixed_width(data, column_width):
    styled_df = style_headers_fixed_width(data, cell_width=column_width)
    st.write(styled_df.to_html(), unsafe_allow_html=True)

# Define the admin page
def admin_page():
    st.title("Admin Page")
    st.sidebar.header("Admin Controls")

    # Upload RMS logo
    logo = st.sidebar.file_uploader("Upload RMS Logo", type=["png", "jpg", "jpeg"], key="logo")
    if logo is not None:
        st.session_state.uploaded_logo = logo

    # Upload Excel files
    st.header("Upload Excel Files")
    file = st.file_uploader("Upload an Excel file", type=["xlsx"], key="excel")
    if file is not None:
        file_name = file.name.split(".")[0]  # Use file name as header
        cache_uploaded_file(file, file_name)

# Define the main page
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
            background-color: #2e86c1;
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

    # Display logo if uploaded, aligned to top-left
    if st.session_state.uploaded_logo is not None:
        st.image(st.session_state.uploaded_logo, width=150, output_format="PNG")

    # Page title
    st.markdown("<div class='page-title'>Search Price Lists</div>", unsafe_allow_html=True)

    # Predictive search bar
    search_query = st.text_input("Search Price Lists", st.session_state.search_query, key="search")
    st.session_state.search_query = search_query

    # Clear search button
    if st.button("Clear Search"):
        st.session_state.search_query = ""

    # Display search results
    if st.session_state.search_query:
        st.markdown("<div class='search-results-header'>Search Results</div>", unsafe_allow_html=True)

        def search_and_highlight(data, query):
            """Filter the data and highlight the rows containing the search query"""
            if data is not None:
                filtered_data = data[data.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)]
                if not filtered_data.empty:
                    highlighted_data = filtered_data.style.applymap(
                        lambda val: "background-color: yellow" if query.lower() in str(val).lower() else ""
                    )
                    return highlighted_data
            return None

        for file_name, data in st.session_state.uploaded_files.items():
            st.markdown(f"<div class='header'>{file_name}</div>", unsafe_allow_html=True)
            result = search_and_highlight(data, st.session_state.search_query)
            if result is not None:
                st.write(result)
            else:
                st.write(f"No matches found in {file_name}.")

    # Display uploaded files as sections
    if st.session_state.uploaded_files:
        for file_name, data in st.session_state.uploaded_files.items():
            st.markdown(f"<div class='header'>{file_name}</div>", unsafe_allow_html=True)
            
            # Allow user to set column width manually
            column_width = st.slider(f"Set column width for {file_name}", 50, 200, 100)  # Default width is 100px
            display_table_with_fixed_width(data, column_width)

# Navigation menu with Main Page as default
page = st.sidebar.selectbox("Choose a page", ["Main", "Admin"], index=0)
if page == "Admin":
    admin_page()
else:
    main_page()
