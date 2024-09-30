
from typing import Any, Dict
from snowflake.snowpark.session import Session


class SnowflakeConnection:
    
    def __init__(self, user_email, oauth_access_token: str):
        self.oauth_access_token = oauth_access_token
        self.user_email = user_email
        self.connection_parameters = self._get_connection_parameters()
        self.session = None

    def _get_connection_parameters(self) -> Dict[str, Any]:

        connection_parameters = {
            "default": {
                "account": 'servicenow-edpdev', 
                "user": self.user_email,
                "host": "servicenow-edpdev.snowflakecomputing.com",
                "authenticator": "oauth",
                "token": self.oauth_access_token,
                "database": 'POC_DB',
                "schema": 'GAI',
                "warehouse": 'DE_STD_WH'
                
                },
            "lab": {
                "account": 'servicenow-edpdev2', 
                "user": self.user_email,
                "host": "servicenow-edpdev2.snowflakecomputing.com",
                "authenticator": "oauth",
                "token": self.oauth_access_token,
                "database": 'EDP_LAB',
                "schema": 'DEMO',
                "warehouse": 'DE_PERF_L0_WH'
                },
            "prod": {
                "account": 'servicenow-edp',
                "user": self.user_email,
                "host": "servicenow-edp.snowflakecomputing.com",
                "authenticator": "oauth",
                "token": self.oauth_access_token,
                "database": 'CDL_LS',
                "schema": 'FINANCE_FPA_RPT',
                "warehouse": 'DE_STD_WH'
            }

        }
        return connection_parameters


    def get_session(self) -> Session:
        if self.session is None:
            connection_parameters = self._get_connection_parameters()["default"]
            self.session = Session.builder.configs(connection_parameters).create()
            self.session.sql_simplifier_enabled = True
        return self.session

    def get_lab_session(self) -> Session:
        if self.session is None:
            connection_parameters_lab = self._get_connection_parameters()["lab"]
            self.session = Session.builder.configs(connection_parameters_lab).create()
            self.session.sql_simplifier_enabled = True
        return self.session

    def get_prod_session(self) -> Session:
        if self.session is None:
            connection_parameters_lab = self._get_connection_parameters()["prod"]
            self.session = Session.builder.configs(connection_parameters_lab).create()
            self.session.sql_simplifier_enabled = True
        return self.session
