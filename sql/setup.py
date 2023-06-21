import click
from aimarketing.snowflake_utils import get_snowpark_session

from snowflake.snowpark.types import (
    StructType,
    StructField,
    StringType,
    DateType,
    IntegerType,
)

from pathlib import Path


@click.command()
@click.option("--drop-tables", is_flag=True, help="Drop all tables")
def main(drop_tables):
    print(
        """
    Run this one time to setup Network Rules
```
create or replace network rule openai_api_network_rule
    mode = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = ('api.openai.com');

create or replace secret openai_token
    type = GENERIC_STRING
    SECRET_STRING = 'sk-*****';


CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION openai_api_access_integration
  ALLOWED_NETWORK_RULES = (openai_api_network_rule)
  ALLOWED_AUTHENTICATION_SECRETS = (openai_token)
  ENABLED = true;
```
"""
    )
    session = get_snowpark_session()

    session.sql("create schema if not exists SANDBOX.AI_MARKETING;").collect()
    session.sql("GRANT ALL PRIVILEGES ON SCHEMA AI_MARKETING to role DE_ARCHITECTS;")
    session.sql("GRANT ALL PRIVILEGES ON SCHEMA AI_MARKETING to role MLE_ARCHITECTS;")

    session.sql("drop table if exists SANDBOX.AI_MARKETING.SALES_CONTACTS").collect()
    session.sql("create or replace temporary stage temp_stage").collect()
    session.file.put(
        str(Path("extraordinary_events.csv").absolute()),
        "@temp_stage/extraordinary_events",
        overwrite=True,
    )
    user_schema = StructType(
        [
            StructField("UID", IntegerType()),
            StructField("COMPANY_NAME", StringType()),
            StructField("CONTACT_NAME", StringType()),
            StructField("CONTACT_EMAIL", StringType()),
            StructField("INDUSTRY", StringType()),
            StructField("PREVIOUS_EVENT", StringType()),
            StructField("PREVIOUS_EVENT_DATE", DateType()),
            StructField("NOTES", StringType()),
        ]
    )

    session.sql("drop table if exists copied_into_table").collect()
    df = (
        session.read.schema(user_schema)
        .options(
            dict(SKIP_HEADER=1, FIELD_OPTIONALLY_ENCLOSED_BY='"', FIELD_DELIMITER=",")
        )
        .csv("@temp_stage/extraordinary_events")
    )
    df.copy_into_table("SALES_CONTACTS", force=True)

    if drop_tables:
        session.sql(
            "drop table if exists SANDBOX.AI_MARKETING.GPT_EMAIL_PROMPTS"
        ).collect()

    session.sql(
        """
    create TABLE if not exists SANDBOX.AI_MARKETING.GPT_EMAIL_PROMPTS (
        SESSION_ID string,
        UID NUMBER(38,0),
        CONTACT_EMAIL string,
        CAMPAIGN_NAME string,
        SYSTEM_PROMPT string,
        USER_PROMPT string,
        EMAIL string,
        TIMESTAMP TIMESTAMP_NTZ(9)
    );"""
    ).collect()

    session.sql(
        """create or replace view SANDBOX.AI_MARKETING.GPT_EMAIL_PROMPTS_LATEST(
            SESSION_ID, UID, CONTACT_EMAIL, CAMPAIGN_NAME, SYSTEM_PROMPT, USER_PROMPT, EMAIL, TIMESTAMP
        ) as
        SELECT SESSION_ID, UID, CONTACT_EMAIL, CAMPAIGN_NAME, SYSTEM_PROMPT, USER_PROMPT, EMAIL, TIMESTAMP
        FROM (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY UID ORDER BY TIMESTAMP DESC) AS rn
            FROM GPT_EMAIL_PROMPTS
        ) t
        WHERE rn = 1;"""
    ).collect()


if __name__ == "__main__":
    main()
