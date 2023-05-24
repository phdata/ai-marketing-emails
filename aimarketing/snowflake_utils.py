from snowflake.snowpark import Session
import os
from typing import Optional
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


# Class to store a singleton connection option
class SnowflakeConnection(object):
    _connection = None

    @property
    def connection(self) -> Optional[Session]:
        return type(self)._connection

    @connection.setter
    def connection(self, val):
        type(self)._connection = val


# Function to return a configured Snowpark session
def get_snowpark_session() -> Session:
    if os.path.exists(os.path.expanduser("~/.snowsql/config")):
        snowpark_config = get_snowsql_config()
    # otherwise configure from environment variables
    elif "SNOWSQL_ACCOUNT" in os.environ:
        snowpark_config = {
            "account": os.environ.get("SNOWSQL_ACCOUNT"),
            "user": os.environ.get("SNOWSQL_USER"),
            "password": os.environ.get("SNOWSQL_PWD"),
            "role": os.environ.get("SNOWSQL_ROLE"),
            "warehouse": os.environ.get("SNOWSQL_WAREHOUSE"),
            "database": os.environ.get("SNOWSQL_DATABASE"),
            "schema": os.environ.get("SNOWSQL_SCHEMA"),
        }
        # Remove any keys with empty values
        snowpark_config = {k: v for k, v in snowpark_config.items() if v}

    SnowflakeConnection().connection = Session.builder.configs(snowpark_config).create()

    if SnowflakeConnection().connection:
        return SnowflakeConnection().connection  # type: ignore
    else:
        raise Exception("Unable to create a Snowpark session")


# Mimic the snowcli logic for getting config details, but skip the app.toml processing
# since this will be called outside the snowcli app context.
# TODO: It would be nice to get rid of this entirely and always use creds.json but
# need to update snowcli to make that happen
def get_snowsql_config(
    connection_name: str = "aws",
    config_file_path: str = os.path.expanduser("~/.snowsql/config"),
) -> dict:
    import configparser

    snowsql_to_snowpark_config_mapping = {
        "account": "account",
        "accountname": "account",
        "username": "user",
        "password": "password",
        "rolename": "role",
        "warehousename": "warehouse",
        "dbname": "database",
        "schemaname": "schema",
        "private_key_path": "private_key_path",
    }
    try:
        config = configparser.ConfigParser(inline_comment_prefixes="#")
        connection_path = "connections." + connection_name

        config.read(config_file_path)
        session_config = config[connection_path]
        # Convert snowsql connection variable names to snowcli ones
        session_config_dict = {
            snowsql_to_snowpark_config_mapping[k]: v.strip('"')
            for k, v in session_config.items()
        }
        if "private_key_path" in session_config:
            session_config_dict["private_key"] = get_private_key(
                session_config.pop("private_key_path")
            )
        return session_config_dict
    except Exception as e:
        raise Exception(f"Error getting snowsql config details: {e}")


def get_private_key(path):
    with open(os.path.expanduser(path), "rb") as key:
        PRIVATE_KEY_PASSPHRASE = os.environ.get("PRIVATE_KEY_PASSPHRASE", "")
        p_key = serialization.load_pem_private_key(
            key.read(),
            password=PRIVATE_KEY_PASSPHRASE.encode(),
            backend=default_backend(),
        )

    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return pkb
