from snowflake.snowpark import Session
import os
from typing import Optional
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import ast
import re


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


def embed_imports_for_streamlit(
    source,
    already_imported_packages=None,
    embed_packages=["aimarketing"],
):
    if already_imported_packages is None:
        already_imported_packages = []

    # Remove imports for specific packages
    lines = source.split("\n")
    for package in embed_packages:
        lines = [
            line
            for line in lines
            if not re.match(rf"^\s*(from|import)\s+{package}\b", line)
        ]
    output_source = "\n".join(lines)

    # find modules imported by source
    modules_to_embed = [
        (module, path)
        for module, path in get_imported_module_paths(source, embed_packages)
        if path not in already_imported_packages
    ]

    # add source of imported files
    if modules_to_embed:
        # prevent running __name__ == '__main__'
        import_source = ""
        for module, path in modules_to_embed:
            already_imported_packages += [path]
            import_source += f"__name__ = '{module}'\n"

            import_source += open(path).read()
            import_source += "\n"
        import_source = embed_imports_for_streamlit(
            import_source, already_imported_packages, embed_packages
        )
        output_source = import_source + "\n" + output_source

    return output_source


def get_imported_module_paths(code, embed_packages=["aimarketing"]):
    modules = []
    parsed_ast = ast.parse(code)

    module_names = []
    for node in ast.walk(parsed_ast):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                module_names.append(module_name)
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module
            module_names.append(module_name)

    for module_name in module_names:
        if not any(module_name.startswith(p) for p in embed_packages):
            continue
        try:
            print(module_name)
            module = __import__(module_name, fromlist=[""])
            module_path = getattr(module, "__file__", None)
            modules.append((module_name, module_path))
        except ImportError as e:
            print(f"Could not import {module_name} due to {e}")

    modules = list(set(modules))
    return modules


if __name__ == "__main__":
    source = """
import numpy as np
import streamlit as st
import aimarketing.date_utils
from aimarketing.snowflake_utils import get_snowpark_session
session = get_snowpark_session()
print("Test")
        """

    print("**** execute source ****")
    exec(source)
    print("**** execute source with embed ****")
    exec(embed_imports_for_streamlit(source))
