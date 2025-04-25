import streamlit as st
import pandas as pd
import os
import gspread  # Need gspread for interacting with sheets after auth
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build # To potentially list sheets or check access

# --- App Configuration & Title ---
st.set_page_config(layout="wide")
st.title("💰 Employee Compensation Calculator (Google Auth)")

# --- Load Secrets ---
try:
    CLIENT_ID = st.secrets["google_oauth"]["client_id"]
    CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
    REDIRECT_URI = st.secrets["google_oauth"]["redirect_uri"]
    SCOPES = st.secrets["google_oauth"]["scopes"]
except KeyError as e:
    st.error(f"Missing OAuth configuration in secrets.toml: {e}")
    st.stop()
except Exception as e:
    st.error(f"Error loading secrets: {e}")
    st.stop()


# --- Helper Functions ---

# Function to create the OAuth flow
def create_oauth_flow():
    """Creates the Google OAuth Flow object."""
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

# Function to get authenticated gspread client
def get_gspread_client(credentials):
    """Gets an authenticated gspread client."""
    try:
        # Check if credentials are valid Credentials object, otherwise create it
        if isinstance(credentials, dict):
             # Handle credentials stored directly as dict from flow.credentials
             creds = Credentials(
                 token=credentials.get('token'),
                 refresh_token=credentials.get('refresh_token'),
                 token_uri=credentials.get('token_uri'),
                 client_id=credentials.get('client_id'),
                 client_secret=credentials.get('client_secret'),
                 scopes=credentials.get('scopes')
             )
        elif isinstance(credentials, Credentials):
             creds = credentials
        else:
             st.error("Invalid credentials format.")
             return None

        # Validate credentials (optional but good)
        # You might need googleapiclient for this
        # service = build('sheets', 'v4', credentials=creds)

        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Failed to authorize gspread client: {e}")
        # Potentially clear credentials if they are invalid
        if 'st.session_state.credentials' in st.session_state:
            del st.session_state.credentials
        st.button("Re-authenticate with Google") # Prompt user to retry
        return None


# --- Authentication Flow ---

# Initialize session state for credentials if not present
if 'credentials' not in st.session_state:
    st.session_state.credentials = None

# Check URL query parameters for the authorization code from Google redirect
query_params = st.query_params # Use new way to get query params
auth_code = query_params.get("code")

# If code exists in URL and we don't have credentials yet, fetch token
if auth_code and not st.session_state.credentials:
    try:
        flow = create_oauth_flow()
        flow.fetch_token(code=auth_code)
        # Store credentials (as dictionary for serialization, or directly if safe)
        st.session_state.credentials = flow.credentials
        # Clear the code from the URL using experimental_set_query_params (or rerun)
        st.query_params.clear() # Clear params to avoid re-fetching on refresh
        st.rerun() # Rerun script to update state and UI without code in URL
    except Exception as e:
        st.error(f"Failed to fetch OAuth token: {e}")
        st.session_state.credentials = None # Ensure creds are None on failure


# --- Main App Logic ---

# If user is NOT authenticated, show login button
if not st.session_state.credentials:
    st.header("Authenticate with Google")
    st.write("This app needs permission to access your Google Sheets.")

    flow = create_oauth_flow()
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    # access_type='offline' is needed to potentially get a refresh_token

    # Using st.link_button for a cleaner UI
    st.link_button("Login with Google", auth_url)
    st.stop() # Stop execution until authenticated


# --- If user IS authenticated ---
st.header("Connect to Google Sheet")
st.success(f"Successfully authenticated with Google!") # Indicate success

# Get authenticated gspread client
gc = get_gspread_client(st.session_state.credentials)

if gc:
    gsheet_url = st.text_input("Enter Google Sheet URL", key="gsheet_url_oauth")
    worksheet_name = st.text_input("Enter Worksheet Name (optional, defaults to first sheet)", value=None, key="worksheet_oauth")

    if st.button("Load Data from Google Sheet", key="load_gsheet_oauth"):
        if gsheet_url:
            df = None
            try:
                st.info(f"Attempting to read data from sheet: {gsheet_url}...")
                spreadsheet = gc.open_by_url(gsheet_url)

                if worksheet_name:
                    worksheet = spreadsheet.worksheet(worksheet_name)
                else:
                    worksheet = spreadsheet.get_worksheet(0) # Get the first sheet

                # Fetch all data and convert to DataFrame
                data = worksheet.get_all_values()
                if data:
                    # Use first row as header
                    df = pd.DataFrame(data[1:], columns=data[0])
                    st.success("Successfully loaded data from Google Sheet!")
                else:
                    st.warning("The worksheet appears to be empty.")

            except gspread.exceptions.SpreadsheetNotFound:
                 st.error("Spreadsheet not found. Check the URL or ensure you have access.")
            except gspread.exceptions.WorksheetNotFound:
                 st.error(f"Worksheet '{worksheet_name}' not found in the spreadsheet.")
            except Exception as e:
                st.error(f"Failed to load data from Google Sheet: {e}")
                df = None # Ensure df is None on error

            # --- Process and Display Data (if df is loaded) ---
            if df is not None:
                 # Ensure process_and_display_data is defined (copy from previous example)
                 # Make sure numpy is imported if needed in that function
                 try:
                     import numpy as np # Import only if needed for processing
                     from compensation_calculator_functions import process_and_display_data # Assuming you moved it
                     process_and_display_data(df)
                 except ImportError:
                      st.error("Helper function 'process_and_display_data' not found.")
                 except Exception as e:
                      st.error(f"Error during data processing: {e}")

        else:
            st.warning("Please enter a Google Sheet URL.")
else:
    st.warning("Could not establish connection to Google Sheets. Please try re-authenticating.")
    # Optionally add a button here to clear credentials and rerun
    if st.button("Clear Credentials and Retry"):
        st.session_state.credentials = None
        st.rerun()

# ----- Placeholder for process_and_display_data function -----
# You need to copy the `process_and_display_data` function from the
# previous Service Account example code here, ensuring it imports numpy
# if necessary. For clarity, you could put it in a separate file
# (e.g., compensation_calculator_functions.py) and import it.

# Example structure if function is defined in this file:
# def process_and_display_data(df):
#     import numpy as np # Import if needed
#     st.subheader("Data Preview")
#     st.dataframe(df.head())
#     # ... rest of the processing logic ...
#     # ... column selection, calculation, display metrics, download ...