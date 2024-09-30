from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import snowflake.connector
import streamlit as st
from sf_connect_user import SnowflakeConnection
from cryptography.fernet import Fernet
from snowflake.connector import ProgrammingError, DatabaseError
from datetime import datetime
from components import sidebar
import os
from snowflake.snowpark.context import get_active_session
from dotenv import load_dotenv
import streamlit_ace as st_ace
# from code_editor import code_editor
load_dotenv()

SECRET_KEY = b'6ub-97q1U0aBvJb3d1Lyc2OssJB_qkXo-__6qEP0h_Y='
cipher_suite = Fernet(SECRET_KEY)

def user_info():
    if 'user_id' not in st.session_state or 'user_name' not in st.session_state or 'user_email' not in st.session_state:
        token = st.query_params.get("token", "")
        if token:
            decrypted_token = cipher_suite.decrypt(token.encode())
            user_eval = eval(decrypted_token.decode())
            st.session_state['user_id'] = user_eval['user_id']
            st.session_state['user_name'] = user_eval['user_name']
            st.session_state['user_email'] = user_eval['user_email']
            st.session_state['oauth_access_token'] = user_eval['access_token']
        else:
            st.session_state['user_id'] = 'no_user_data_found'
            st.session_state['user_name'] = 'no_user_data_found'
            st.session_state['user_email'] = 'no_user_data_found'
            st.session_state['oauth_access_token'] = 'no_user_data_found'

    return (
        st.session_state['user_id'],
        st.session_state['user_name'],
        st.session_state['user_email'],
        st.session_state['oauth_access_token'],
    )

st.session_state['user_id'], st.session_state['user_name'], st.session_state['user_email'], st.session_state['oauth_access_token'] = user_info()

# Snowflake connection parameters
dev_snowflake_conn_params = {
    'user': os.getenv('edpdev2_svc_username'),
    'password' : os.getenv('edpdev2_svc_pw'),
    'account': 'servicenow-edpdev2',
    'role': 'DATA_PLATFORM_COE_ROLE',
    'warehouse': 'DE_PERF_L0_WH',
    'database': 'DATA_PLATFORM_COE',
    'schema': 'COE'
}

def handle_like(session, query: str, query_result: str, feedback: int, request_id: str):
    """Handles the 'like' button click event and logs feedback."""
    log_query_to_sf(session, st.session_state['user_id'], st.session_state['user_name'], st.session_state['user_email'], query, query_result, feedback="Like", request_id=request_id)
    # st.success(f"Feedback 'Like' logged successfully for request ID: {request_id}")

def handle_dislike(session, query: str, query_result: str, feedback: int, request_id: str):
    """Handles the 'dislike' button click event and logs feedback."""
    log_query_to_sf(session, st.session_state['user_id'], st.session_state['user_name'], st.session_state['user_email'], query, query_result, feedback="Dislike", request_id=request_id)
    # st.success(f"Feedback 'Dislike' logged successfully for request ID: {request_id}")


def send_message(prompt: str) -> Dict[str, Any]:
    """Calls the REST API and returns the response."""
    request_body = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "semantic_model_file": f"@EDP_LAB.DEMO.CORTEX_ANALYST/kpi.yaml",
    }
    # st.write(request_body)
    resp = requests.post(
        url=f"https://{dev_snowflake_conn_params['account']}.snowflakecomputing.com/api/v2/cortex/analyst/message",
        json=request_body,
        headers={
            "Authorization": f'Snowflake Token="{st.session_state.CONN.rest.token}"',
            "Content-Type": "application/json",
        },
    )
    # st.write(resp)
    request_id = resp.headers.get("X-Snowflake-Request-Id")
    if resp.status_code < 400:
        return {**resp.json(), "request_id": request_id}  # type: ignore[arg-type]
    else:
        raise Exception(
            f"Failed request (id: {request_id}) with status {resp.status_code}: {resp.text}"
        )

def log_query_to_sf(session, user_id, user_name, user_email, user_question, sql_generated, feedback=None, request_id=None):
    """Logs the user question, SQL generated, and feedback to the Snowflake table."""
    try:
        # Establish a Snowflake connection
        # conn = SnowflakeConnection(user_email, oauth_access_token).get_session()
        timestamp_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        if feedback is None:
            # Initial log without feedback
            log_data = {
                'APP_MODULE': 'Cortex Analyst',
                'USER_ID': user_id,
                'USER_NAME': user_name,
                'USER_EMAIL': user_email,
                'USER_QUESTION': user_question,
                'SQL_GENERATED': sql_generated,
                'FEEDBACK': 'No Feedback',
                'TS_UTC': timestamp_utc,
                'REQUEST_ID': request_id  # Ensure request_id is passed here
            }

            feedback_df = pd.DataFrame([log_data])

            # Insert the log into the Snowflake table
            snowpark_feedback_df = session.create_dataframe(feedback_df).to_df(
                ["APP_MODULE", "USER_ID", "USER_NAME", "USER_EMAIL", "USER_QUESTION", "SQL_GENERATED", "FEEDBACK", "TS_UTC", "REQUEST_ID"]
            )
            snowpark_feedback_df.write.mode("append").save_as_table("POC_DB.GAI.Cortex_Analyst_logging")

        else:
            # Update the feedback using the request_id for unique identification
            update_query =f"""
            UPDATE POC_DB.GAI.Cortex_Analyst_logging
            SET FEEDBACK = '{feedback}'
            WHERE REQUEST_ID = '{request_id}'
            """
            # Execute the update query
            session.sql(update_query).collect()

            st.toast(f"Thanks for the Feedback",icon='🎉')

    except DatabaseError as e:
        st.error(f"An error occurred in capturing your feedback {e}. Please contact the administrator.")
        return


def process_message(session, prompt: str) -> None:
    """Processes a message, generates the response, and logs the query to Snowflake."""
    st.session_state.messages.append(
        {"role": "user", "content": [{"type": "text", "text": prompt}]}
    )
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Wait a min..."):
            response = send_message(prompt=prompt)
            request_id = response["request_id"]
            content = response["message"]["content"]
            sql_generated = [item["statement"] for item in content if item["type"] == "sql"]

            if sql_generated:
                sql_statement = sql_generated[0]  # Assuming one SQL is generated
                sql_statement = sql_statement.replace("data_platform_coe.coe", "CDL_LS_SHARE.FINANCE_FPA_RPT".lower())
                # Log the query to Snowflake (initially without feedback, using request_id)
                log_query_to_sf(session,st.session_state['user_id'], st.session_state['user_name'], st.session_state['user_email'], prompt, sql_statement, request_id=request_id)

                # Display the content including SQL query and results
                display_content(session, content=content, request_id=request_id)

                # Add Like and Dislike buttons for feedback
                col1, col2, col3 = st.columns([1, 1, 20])
                with col1:
                    like_button = st.button("👍", on_click=lambda: handle_like(session, query=prompt, query_result=sql_statement, feedback=1, request_id=request_id))
                with col2:
                    dislike_button = st.button("👎", on_click=lambda: handle_dislike(session, query=prompt, query_result=sql_statement, feedback=0, request_id=request_id))
            else:
                display_content(session, content=content, request_id=request_id)

    st.session_state.messages.append(
        {"role": "assistant", "content": content, "request_id": request_id}
    )

def fetch_original_question(session, request_id: str) -> Optional[str]:
    """Fetches the original user question based on the request ID."""
    try:
        # Query Snowflake to fetch the original user question
        query = f"""
        SELECT USER_QUESTION
        FROM POC_DB.GAI.Cortex_Analyst_logging
        WHERE REQUEST_ID = '{request_id}'
        LIMIT 1
        """
        result = session.sql(query).collect()

        if result and len(result) > 0:
            return result[0]['USER_QUESTION']
        else:
            st.warning(f"No user question found for Request ID: {request_id}")
            return None
    except DatabaseError as e:
        st.error(f"Error fetching the original question: {e}")
        return None


def display_content(session, 
                    content: List[Dict[str, str]], 
                    request_id: Optional[str] = None, 
                    message_index: Optional[int] = None,) -> None:
    """Displays the content returned by the assistant, including SQL and results."""
    message_index = message_index or len(st.session_state.messages)

    for item in content:
        if item["type"] == "text":
            item["text"] = item["text"].replace("Below is the SQL that answers your question.","")
            st.markdown(item["text"])
        elif item["type"] == "suggestions":
            with st.expander("Suggestions", expanded=True):
                for suggestion_index, suggestion in enumerate(item["suggestions"]):
                    if st.button(suggestion, key=f"{message_index}_{suggestion_index}"):
                        st.session_state.active_suggestion = suggestion
        elif item["type"] == "sql":
            # Ensure the SQL expander stays open if edit mode is enabled
            edit_mode_key = f"edit_mode_{message_index}"
            edit_mode = st.session_state.get(edit_mode_key, False)
            with st.expander("SQL Query", expanded=edit_mode):
                item["statement"] = item["statement"].replace("data_platform_coe.coe", "CDL_LS_SHARE.FINANCE_FPA_RPT".lower())
                st.code(item["statement"], language="sql")
                
                # Checkbox to enable edit mode
                edit_mode = st.checkbox("Want to edit the SQL? **Select Checkbox**", key=edit_mode_key, value=edit_mode)
                
                if edit_mode:
                    st.warning("Please click on 'APPLY' to save your SQL code before running the modified query")
                    edited_sql = st_ace.st_ace(value=item["statement"], language="sql", theme="tomorrow", key=f"ace_{message_index}")
                    # edited_sql = code_editor(item["statement"], lang="sql")
                    if request_id:
                        original_question = fetch_original_question(session, request_id)
                
                # "Run Modified SQL" button inside the SQL expander
                if st.button("Run Modified Query", key=f"run_sql_{message_index}"):
                    with st.spinner("Running SQL..."):
                        # Run edited SQL if edit mode is enabled, else run the original SQL
                        sql_to_run = edited_sql if edit_mode and edited_sql else item["statement"]
                        df = session.sql(sql_to_run).to_pandas()

                        # Log the edited SQL to Snowflake
                        if edit_mode:
                            log_query_to_sf(session, st.session_state['user_id'], st.session_state['user_name'], st.session_state['user_email'], original_question, f"--[edited]: \n {edited_sql}", request_id=request_id)
        
                        # Replace previous result if new result comes
                        st.session_state[f"result_{message_index}"] = df
            
            # Run original SQL if the user hasn't clicked "Run Modified SQL" and store the results
            if f"result_{message_index}" not in st.session_state:
                with st.spinner("Running SQL..."):
                    df = session.sql(item["statement"]).to_pandas()
                    st.session_state[f"result_{message_index}"] = df
            
            # Show the results in the Results expander, with the new result replacing the old one
            with st.expander("Results", expanded=True):
                df = st.session_state.get(f"result_{message_index}", None)
                if df is not None:
                    if len(df.index) > 1:
                        data_tab, line_tab, bar_tab = st.tabs(["Data", "Line Chart", "Bar Chart"])
                        data_tab.dataframe(df)
                        if len(df.columns) > 1:
                            df = df.set_index(df.columns[0])
                        with line_tab:
                            st.line_chart(df)
                        with bar_tab:
                            st.bar_chart(df)
                    else:
                        st.dataframe(df)
                str_dashlink = f"https://app.powerbi.com/groups/me/apps/10fe4034-ee13-4749-95ca-cd9749b4feae/reports/ac685b42-8dc3-4baf-8536-3e9f2918f823/ReportSection036dd9f7d4e99a505411?experience=power-bi"
                str_dashinfo = f"For information, please check our [KPI Dashboard]({str_dashlink})"
                st.caption(str_dashinfo, unsafe_allow_html=True)


def Cortex_Analyst():
    st.session_state['user_id'], st.session_state['user_name'], st.session_state['user_email'], st.session_state['oauth_access_token'] = user_info()
    user_email_lst = [
        'prabitha.p@servicenow.com',
        'ankit.agrawal@servicenow.com',
        'vijay.kotu@servicenow.com',
        'aj.udechukwu@servicenow.com',
        'Siva.Prasad@servicenow.com',
        'cheris.bhatia@servicenow.com',
        'ravikiran.kandimalla@servicenow.com',
        'gaurav.totuka@servicenow.com',
        'manishankar.pasumarthy@servicenow.com',
        'manishank.pasumarthy@servicenow.com',
        'anne.chaithanya@servicenow.com',
        'sruthi.nairuk@servicenow.com',
        'reddyvamsi.krishna@servicenow.com',
        'swetha.bobba1@servicenow.com',
        'akhil.duvvuru@servicenow.com',
        'sarah.obrien@servicenow.com',
        'girish.srinivasan@servicenow.com',
        'meredith.machovoe@servicenow.com',
        'brian.hoffman@servicenow.com',
        'eric.cooperman@servicenow.com',
        'andrew.strieber@servicenow.com',
        'sarah.lim@servicenow.com',
        'venketesh.iyer@servicenow.com',
        'yeelo.ng@servicenow.com',
        'raviteja.kothi@servicenow.com'
    ]

    if st.session_state['user_email'] not in user_email_lst:
        st.error(f"We're in beta. Your email: {st.session_state['user_email']} is not authorized for this App yet. Please share your feedback if you like to get access")
        return
    # elif user_email in user_email_lst:
    #     st.success("email validated")
    try:
        session = SnowflakeConnection(st.session_state['user_email'], st.session_state['oauth_access_token']).get_session()
    except DatabaseError as e:
        if "OAuth access token expired" in str(e):
            st.error("Your session has expired. Please [click here](https://da-genai-app.servicenow.com/analyst)")
            #todo - clear the session and token
            st.write("If that did not work, please close the app and open the App again to start")
        elif "No default role has been assigned to the user" in str(e):
            st.error(f"No default role has been assigned to your account {st.session_state['user_email']}. Please contact Snowflake admin to assign a default role on your account {st.session_state['user_email']} for edpdev.")
        else:
            st.error(f"An error occurred while connecting to Snowflake. {e} Please contact Snowflake administrator.")
        return

    # Establish the Snowflake connection if not already established
    if 'CONN' not in st.session_state or st.session_state.CONN is None:
        st.session_state.CONN = snowflake.connector.connect(**dev_snowflake_conn_params)

    st.header("ServiceNow KPI Analyst")
    # st.markdown(f"Semantic Model: `kpi.yaml`")
    st.markdown(f" `AI-powered Q&A chatbot to provide analytics & insights to your questions for ServiceNow KPIs`")
    sidebar.create_sidebar_about()
    sidebar.create_sidebar1()
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.suggestions = []
        st.session_state.active_suggestion = None

    for message_index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            display_content(session,
                content=message["content"],
                request_id=message.get("request_id"),
                message_index=message_index,
            )

    if user_input := st.chat_input("What is your question?  You can also ask, what type of questions to ask!"):
        process_message(session,prompt=user_input)

    if st.session_state.active_suggestion:
        process_message(session,prompt=st.session_state.active_suggestion)
        st.session_state.active_suggestion = None


# if __name__ == "__main__":
#     main()