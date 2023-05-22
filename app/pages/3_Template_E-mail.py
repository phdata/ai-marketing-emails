import streamlit as st
import json
import time

from aimarketing.utils import submit_prompt, get_session
from snowflake.snowpark.functions import col, lit, to_varchar, current_session, udf
from snowflake.snowpark.types import StringType


def format_user_prompt(
    COMPANY_NAME,
    INDUSTRY,
    NOTES,
    SALES_REP,
    PREVIOUS_EVENT=None,
    PREVIOUS_EVENT_DATE=None,
):
    user_prompt = f"COMPANY: {COMPANY_NAME}\n"
    user_prompt += f"INDUSTRY: {INDUSTRY}\n"
    user_prompt += f"NOTES: {NOTES}\n"
    user_prompt += f"SALES_REP: {SALES_REP}\n"
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
                "COMPANY_NAME",
                "INDUSTRY",
                "PREVIOUS_EVENT",
                to_varchar("PREVIOUS_EVENT_DATE", "MMMM DD, YYYY").alias(
                    "PREVIOUS_EVENT_DATE"
                ),
                "NOTES",
                "SALES_REP",
                "SALES_REP_EMAIL",
            ]

            self.filter_expr = col("PREVIOUS_EVENT").isNotNull()
        elif campaign_name == "New Customer":
            self.select_expr = [
                "COMPANY_NAME",
                "INDUSTRY",
                "NOTES",
                "SALES_REP",
                "SALES_REP_EMAIL",
            ]
            self.filter_expr = col("PREVIOUS_EVENT").isNull()

    def get_table(self):
        session = get_session()
        contacts_table = session.table("SALES_CONTACTS")
        contacts_table = contacts_table.filter(self.filter_expr)
        return contacts_table

    def system_prompt_with_date(
        self, current_date=time.strftime("%B %d, %Y", time.gmtime())
    ):
        return f"The current date is {current_date}\n" + campaign.system_prompt

    def __hash__(self) -> int:
        return self.campaign_name.__hash__() + self.system_prompt.__hash__()


@st.cache
def get_contacts(campaign):
    return (
        campaign.get_table()
        .select(campaign.select_expr)
        .to_pandas()
        .set_index("COMPANY_NAME")
    )


@st.cache()
def make_gpt_prompts(campaign, current_date=time.strftime("%B %d, %Y", time.gmtime())):
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

    system_prompt = campaign.system_prompt_with_date(current_date)
    return (
        campaign.get_table()
        .select(
            current_session(),
            col("SALES_REP_EMAIL"),
            lit(system_prompt).alias("SYSTEM_PROMPT"),
            user_prompt_udf(
                col("COMPANY_NAME"),
                col("INDUSTRY"),
                col("NOTES"),
                col("SALES_REP"),
                col("PREVIOUS_EVENT"),
                to_varchar("PREVIOUS_EVENT_DATE", "MMMM DD, YYYY"),
            ).alias("USER_PROMPT"),
        )
        .to_pandas()
    )


st.header("Generate Email using a Template")

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
    st.dataframe(contacts)
    user_prompts = {
        contact: format_user_prompt(
            COMPANY_NAME=contact,
            **contacts.loc[contact].drop("SALES_REP_EMAIL").to_dict(),
        )
        for contact in contacts.index
    }
else:
    contact = st.selectbox("Contact", contacts.index)
    user_prompt = format_user_prompt(
        COMPANY_NAME=contact, **contacts.loc[contact].drop("SALES_REP_EMAIL").to_dict()
    )
    print_prompt(user_prompt)
    user_prompts = {contact: user_prompt}

st.dataframe(make_gpt_prompts(campaign))

if st.button("Generate"):
    if len(user_prompts) > 1:
        bar = st.progress(0)
    else:
        bar = None
    with st.spinner("Generating..."):
        for i, (contact, user_prompt) in enumerate(user_prompts.items()):
            if all_data:
                st.subheader(contact)
                print_prompt(user_prompt)

            submit_prompt(campaign.system_prompt, user_prompt)

            if bar:
                bar.progress((i + 1) / len(user_prompts))
    st.success("Done!")
