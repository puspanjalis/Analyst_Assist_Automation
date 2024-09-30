# main.py
import streamlit as st
from Cortex_Analyst import Cortex_Analyst
from streamlit_option_menu import option_menu
from graphlit import Graphlit
from components import header, sidebar

# Define a function to clear the session state
def clear_session_state():
    for key in st.session_state.keys():
        del st.session_state[key]

# Set the page configuration
st.set_page_config(
    page_icon="💡",
    page_title="D&A Analyst Assist",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Create the header with branding
header.create_header()

def main():
    with st.sidebar:
        app = option_menu(
            menu_title='D&A AI Apps',
            options=["Home","SN KPI Analyst"],
            # icons=['arrow-right', 'arrow-right', 'arrow-right', 'arrow-right', 'arrow-right'],
            # menu_icon='chat-text-fill',
            default_index=0,
            styles = {
                "container": {
                    "padding": "5!important",
                    "background-color": 'transparent'  # Light gray background for the container
                },
                "icon": {
                    "color": "#606060",  # Medium gray for the icon
                    "font-size": "0px",
                    "font-weight": "bold"
                },
                "nav-link": {
                    "color": "#333333",  # Dark gray for text
                    "font-size": "18px",
                    "text-align": "left",
                    "font-family": "'Roboto', sans-serif",
                    "margin": "0px",
                    "--hover-color": "#e3e7ee"  # Light gray on hover
                },
                "nav-link-selected": {
                    "background-color": "#d1d5db",  # Very light gray for selected item
                    "color": "#333333"
                },
                "menu-title": {
                    "font-weight": "bold",
                    "font-family": "'Roboto', sans-serif",
                    "color": "#333333"  # Dark gray for the menu title
                }
            }


        )
        st.markdown("<hr style='border: 1px solid #ddd; margin: 20px 0;'>", unsafe_allow_html=True)

    # Clear the session state when switching apps
    if "current_app" not in st.session_state or st.session_state.current_app != app:
        clear_session_state()
        st.session_state.current_app = app

    # Display the selected page 
    if app == "Home":
        # Set the title of the application
        # st.title("Welcome to D&A - AI Suite! 🌟", anchor="welcome")

        # Create sidebar 
        sidebar.create_sidebar()   

        # Add a detailed introduction with increased font size and styling
        # <h2 style="font-size: 28px; font-weight: bold;">Data & Analytics AI Apps for ServiceNow 🚀</h2>

        st.subheader("Data & Analytics AI Apps for ServiceNow 🚀")
        st.markdown("""
            <p style="font-size: 16px;">
                Welcome to the D&A AI Apps, where innovation meets intelligence!
            </p>
            <p style="font-size: 16px;">  
                Our AI products are designed to transform your data experience.
                Explore diverse range of capabilities & features available through the sidebar and unlock new possibilities for data analysis and decision-making.
            </p>
        """, unsafe_allow_html=True)

        st.subheader("Featured AI Products ✨")

        kpi_info_url = f"https://servicenow.sharepoint.com/:x:/s/DataAndAnalytics/EdbPdb8fOgBMmMUB5OaYXYsBNTdGBAXwt0KF3NjMqqgLLQ?e=gQWbTZ"
        str_html =  f"""<p style="font-size: 16px;"> <strong>🔍 SN KPI Analyst:</strong>  
                        AI-powered Q&A chatbot to provide analytics & insights to your questions for 
                        <a href= {kpi_info_url} target="_blank"> ServiceNow KPIs </a>
                      </p>
                     """
        st.markdown(str_html, unsafe_allow_html=True)
        
    elif app ==  "SN KPI Analyst":
        Cortex_Analyst()

if __name__ == "__main__":
    main()