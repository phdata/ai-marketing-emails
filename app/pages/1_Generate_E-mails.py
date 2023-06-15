import streamlit as st
import json
import datetime
import pandas as pd
import re

from aimarketing.utils import submit_prompt
from snowflake.snowpark.functions import (
    col,
    lit,
    current_session,
    udf,
    call_udf,
    current_timestamp,
)
from snowflake.snowpark.exceptions import SnowparkSessionException
from snowflake.snowpark.types import StringType

from aimarketing.snowflake_utils import get_snowpark_session
from snowflake.snowpark.context import get_active_session


@st.cache_resource
def get_session():
    try:
        return get_active_session()
    except SnowparkSessionException:
        return get_snowpark_session()


OUTPUT_TABLE_NAME = "GPT_EMAIL_PROMPTS"
LATEST_VIEW_NAME = "GPT_EMAIL_PROMPTS_LATEST"
FULL_OUTPUT_TABLE_NAME = (
    get_session().get_current_database()
    + "."
    + get_session().get_current_schema()
    + "."
    + OUTPUT_TABLE_NAME
)


def format_user_prompt(
    COMPANY_NAME,
    INDUSTRY,
    NOTES,
    CONTACT_NAME,
    PREVIOUS_EVENT=None,
    PREVIOUS_EVENT_DATE=None,
):
    user_prompt = f"COMPANY: {COMPANY_NAME}\n"
    user_prompt += f"INDUSTRY: {INDUSTRY}\n"
    user_prompt += f"NOTES: {NOTES}\n"
    user_prompt += f"CONTACT_NAME: {CONTACT_NAME}\n"
    if PREVIOUS_EVENT:
        user_prompt += f"PREVIOUS_EVENT: {PREVIOUS_EVENT}\n"
        user_prompt += f"PREVIOUS_EVENT_DATE: {PREVIOUS_EVENT_DATE}\n"

    return user_prompt


def print_prompt(user_prompt):
    st.markdown("  \n".join(f"**{line}**" for line in user_prompt.split("\n")))


campaign_names = ["Returning Customer", "New Customer"]
TABLE_NAME = "SALES_CONTACTS"


def get_system_prompt(campaign_name):
    prompt = json.load(open("extraordinary_events.json"))["system_prompt"][
        campaign_name
    ]
    return re.sub("^[ \t]+|[ \t]+$", "", prompt, flags=re.MULTILINE)


def get_campaign_select(campaign_name):
    if campaign_name == "Returning Customer":
        return [
            "UID",
            "COMPANY_NAME",
            "INDUSTRY",
            "PREVIOUS_EVENT",
            call_udf(
                "humanize_date", col("PREVIOUS_EVENT_DATE"), datetime.date.today()
            ).alias("PREVIOUS_EVENT_DATE"),
            "NOTES",
            "CONTACT_NAME",
            "CONTACT_EMAIL",
        ]

    elif campaign_name == "New Customer":
        return [
            "UID",
            "COMPANY_NAME",
            "INDUSTRY",
            "NOTES",
            "CONTACT_NAME",
            "CONTACT_EMAIL",
        ]


def get_campaign_filter(campaign_name):
    if campaign_name == "Returning Customer":
        return col("PREVIOUS_EVENT").isNotNull()
    elif campaign_name == "New Customer":
        return col("PREVIOUS_EVENT").isNull()


def get_table(campaign_name):
    session = get_session()
    contacts_table = session.table(TABLE_NAME)
    contacts_table = contacts_table.filter(get_campaign_filter(campaign_name))
    return contacts_table


@st.cache_data
def get_contacts(campaign_name):
    return (
        get_table(campaign_name)
        .select(get_campaign_select(campaign_name))
        .to_pandas()
        .set_index("UID")
    )


@st.cache_data
def cache_gpt_prompts(
    campaign_name,
    system_prompt,
    current_date=datetime.date.today(),
    uid=None,
):
    return make_gpt_prompts(
        campaign_name,
        system_prompt,
        current_date=current_date,
        uid=uid,
    ).to_pandas()


def make_gpt_prompts(
    campaign_name,
    system_prompt,
    current_date=datetime.date.today(),
    uid=None,
):
    # Make UDF for user prompt
    user_prompt_udf = udf(
        format_user_prompt,
        return_type=StringType(),
        input_types=[
            StringType(),  # COMPANY
            StringType(),  # INDUSTRY
            StringType(),  # NOTE
            StringType(),  # SALES_REP
            StringType(),  # PREVIOUS_EVENT
            StringType(),  # PREVIOUS_EVENT_DATE
        ],
        session=get_session(),
    )

    table = get_table(campaign_name)
    if uid:
        table = table.filter(col("UID") == uid)

    prompts = table.select(
        current_session().alias("SESSION_ID"),
        col("UID"),
        col("CONTACT_EMAIL"),
        lit(campaign_name).alias("CAMPAIGN_NAME"),
        lit(system_prompt).alias("SYSTEM_PROMPT"),
        user_prompt_udf(
            col("COMPANY_NAME"),
            col("INDUSTRY"),
            col("NOTES"),
            col("CONTACT_NAME"),
            col("PREVIOUS_EVENT"),
            call_udf(
                "humanize_date", col("PREVIOUS_EVENT_DATE"), datetime.date.today()
            ),
        ).alias("USER_PROMPT"),
    )
    return prompts


def add_gpt_to_select(df):
    return df.select(
        col("SESSION_ID"),
        col("UID"),
        col("CONTACT_EMAIL"),
        col("CAMPAIGN_NAME"),
        col("SYSTEM_PROMPT"),
        col("USER_PROMPT"),
        call_udf(
            "submit_gpt_prompt",
            col("SYSTEM_PROMPT"),
            col("USER_PROMPT"),
        ).alias("EMAIL"),
        current_timestamp().alias("TIMESTAMP"),
    )


st.header(":snowflake: Generate Email using Snowflake Data")
st.markdown(
    """This application serves as an interface for using GPT-3 to generate emails for contacts in Snowflake Data.
First, you can select from a list of email campaigns. Depending on the campaign, a prewritten prompt is shown."""
)


campaign_name = st.selectbox("Email Campaign", campaign_names)

system_prompt = st.text_area(
    "System Prompt",
    get_system_prompt(campaign_name),
    height=300,
)
contacts = get_contacts(campaign_name)

st.subheader("Select contact data")
st.markdown(
    "In addition, the email campaign specifies which set of contacts to retrieve from the Snowflake table."
)
st.info(f"Found {len(contacts)} contacts in the {TABLE_NAME} table")
use_udf_for_gpt = st.checkbox("Run ChatGPT in Snowflake")
all_data = st.checkbox("Generate Emails for All Contacts")

contact_id = None
if not all_data:
    contact_id = st.selectbox(
        "Contact", contacts.index, format_func=contacts.COMPANY_NAME.to_dict().get
    )

if use_udf_for_gpt:
    prompts_df = make_gpt_prompts(campaign_name, system_prompt, uid=contact_id)
else:
    prompts_df = cache_gpt_prompts(campaign_name, system_prompt, uid=contact_id)

if st.button("Generate"):
    with st.spinner("Generating..."):
        if use_udf_for_gpt:
            prompts_responses_df = add_gpt_to_select(prompts_df)
            prompts_responses_df.write.save_as_table(
                OUTPUT_TABLE_NAME, mode="append", column_order="name"
            )
            latest_response_in_session = (
                prompts_df.select(col("UID"), "SESSION_ID")
                .join(
                    get_session()
                    .table(LATEST_VIEW_NAME)
                    .select(
                        col("UID"),
                        "SESSION_ID",
                        col("USER_PROMPT"),
                        col("EMAIL"),
                    ),
                    on=["UID", "SESSION_ID"],
                )
                .to_pandas()
            )
            st.success(
                f"Wrote {len(latest_response_in_session) } rows to `{FULL_OUTPUT_TABLE_NAME}`"
            )
            for i, row in latest_response_in_session.iterrows():
                print_prompt(row.USER_PROMPT)
                st.markdown(row.EMAIL)

        else:
            if len(prompts_df) > 1:
                bar = st.progress(0)
            else:
                bar = None
            emails = pd.Series(index=prompts_df.index, name="EMAIL", dtype=str)
            for i, (contact_id, row) in enumerate(prompts_df.iterrows()):
                print_prompt(row.USER_PROMPT)
                response = submit_prompt(row.SYSTEM_PROMPT, row.USER_PROMPT)

                emails.loc[contact_id] = response

                if bar:
                    bar.progress((i + 1) / len(prompts_df))

                prompts_response = pd.concat(
                    [prompts_df.loc[[contact_id]], emails.loc[[contact_id]]], axis=1
                )

                prompts_response["TIMESTAMP"] = datetime.datetime.now()
                prompts_response["TIMESTAMP"] = (
                    prompts_response["TIMESTAMP"]
                    .astype("datetime64[ns]")
                    .dt.tz_localize("UTC")
                )

                # Write to Snowflake

                write_result = get_session().write_pandas(
                    prompts_response,
                    OUTPUT_TABLE_NAME,
                    auto_create_table=True,
                )
                st.success(
                    f"Wrote {len(prompts_response)} rows to `{FULL_OUTPUT_TABLE_NAME}`"
                )
