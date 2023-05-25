import streamlit as st
import json
from datetime import date, timedelta
import pandas as pd
import re

from aimarketing.utils import submit_prompt, get_session
from snowflake.snowpark.functions import (
    col,
    lit,
    current_session,
    udf,
    call_udf,
)
from snowflake.snowpark.types import StringType


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


class Campaign:
    """
    A class that represents a campaign.
    """

    names = ["Returning Customer", "New Customer"]

    def __init__(self, campaign_name):
        self.campaign_name = campaign_name
        self.system_prompt = json.load(open("app/extraordinary_events.json"))[
            "system_prompt"
        ][campaign_name]

        if campaign_name == "Returning Customer":
            self.select_expr = [
                "UID",
                "COMPANY_NAME",
                "INDUSTRY",
                "PREVIOUS_EVENT",
                call_udf(
                    "humanize_date", col("PREVIOUS_EVENT_DATE"), date.today()
                ).alias("PREVIOUS_EVENT_DATE"),
                "NOTES",
                "CONTACT_NAME",
                "CONTACT_EMAIL",
            ]

            self.filter_expr = col("PREVIOUS_EVENT").isNotNull()
        elif campaign_name == "New Customer":
            self.select_expr = [
                "UID",
                "COMPANY_NAME",
                "INDUSTRY",
                "NOTES",
                "CONTACT_NAME",
                "CONTACT_EMAIL",
            ]
            self.filter_expr = col("PREVIOUS_EVENT").isNull()

    def get_table(self):
        session = get_session()
        contacts_table = session.table("SALES_CONTACTS")
        contacts_table = contacts_table.filter(self.filter_expr)
        return contacts_table

    def system_prompt_with_date(self, current_date=date.today()):
        today = current_date.strftime("%B %d, %Y")
        couple_years_ago = current_date - timedelta(days=365 * 2 + 50)
        last_month = current_date - timedelta(days=30)
        date_prompt = f"""The current date is {today}.
        Only use relative language when talking about dates,
        for example {couple_years_ago} would be "a couple years ago" and {last_month} would be "last month."
        """
        return re.sub(
            "^[ \t]+|[ \t]+$", "", date_prompt + self.system_prompt, flags=re.MULTILINE
        )

    def __hash__(self) -> int:
        return self.campaign_name.__hash__() + self.system_prompt.__hash__()


@st.cache
def get_contacts(campaign):
    return (
        campaign.get_table().select(campaign.select_expr).to_pandas().set_index("UID")
    )


@st.cache()
def eval_gpt_prompts(campaign, current_date=date.today(), uid=None):
    return make_gpt_prompts(campaign, current_date, uid).to_pandas()


def make_gpt_prompts(campaign, current_date=date.today(), uid=None):
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

    table = campaign.get_table()
    if uid:
        table = table.filter(col("UID") == uid)

    system_prompt = campaign.system_prompt_with_date(current_date)
    return table.select(
        current_session(),
        col("CONTACT_EMAIL"),
        lit(system_prompt).alias("SYSTEM_PROMPT"),
        user_prompt_udf(
            col("COMPANY_NAME"),
            col("INDUSTRY"),
            col("NOTES"),
            col("CONTACT_NAME"),
            col("PREVIOUS_EVENT"),
            call_udf("humanize_date", col("PREVIOUS_EVENT_DATE"), date.today()),
        ).alias("USER_PROMPT"),
    )


st.header(":snowflake: Generate Email using a Snowflake Data")

campaign = Campaign(st.selectbox("Email Campaign", Campaign.names))

campaign.system_prompt = st.text_area(
    "System Prompt",
    campaign.system_prompt,
    height=400,
)
contacts = get_contacts(campaign)
st.subheader("Select contact data")
all_data = st.checkbox("Generate Emails for All Contacts")
if all_data:
    prompts_df = eval_gpt_prompts(campaign)
else:
    contact_id = st.selectbox(
        "Contact", contacts.index, format_func=contacts.COMPANY_NAME.to_dict().get
    )
    prompts_df = eval_gpt_prompts(campaign, uid=contact_id)

if st.button("Generate"):
    if len(prompts_df) > 1:
        bar = st.progress(0)
    else:
        bar = None
    emails = pd.Series(index=prompts_df.index, name="EMAIL", dtype=str)
    with st.spinner("Generating..."):
        for i, (contact_id, row) in enumerate(prompts_df.iterrows()):
            print_prompt(row.USER_PROMPT)
            response = submit_prompt(row.SYSTEM_PROMPT, row.USER_PROMPT)

            emails.loc[contact_id] = response

            if bar:
                bar.progress((i + 1) / len(prompts_df))
    prompts_response = pd.concat([prompts_df, emails], axis=1).reset_index()

    # Write to Snowflake

    output_table_name = "GPT_EMAIL_PROMPTS"
    write_result = get_session().write_pandas(
        prompts_response,
        output_table_name,
        auto_create_table=True,
    )
    full_output_table_name = (
        get_session().get_current_database()
        + "."
        + get_session().get_current_schema()
        + "."
        + output_table_name
    )
    st.success(f"Wrote {len(prompts_response)} rows to `{full_output_table_name}`")
