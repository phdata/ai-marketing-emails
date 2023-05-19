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


def print_prompt(user_prompt):
    st.markdown("  \n".join(f"**{line}**" for line in user_prompt.split("\n")))


@st.cache
def get_contacts(campaign):
    session = get_session()
    contacts_table = session.table("SALES_CONTACTS")
    if campaign == "Returning Customer":
        contacts_table = contacts_table.select(
            [
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
        ).filter(col("PREVIOUS_EVENT").isNotNull())
    elif campaign == "New Customer":
        contacts_table = contacts_table.select(
            [
                "COMPANY_NAME",
                "INDUSTRY",
                "NOTES",
                "SALES_REP",
                "SALES_REP_EMAIL",
            ]
        ).filter(col("PREVIOUS_EVENT").isNull())

    contacts = contacts_table.to_pandas().set_index("COMPANY_NAME")

    return contacts


st.header("Generate Email using a Template")

# Current date using natural language
current_date = time.strftime("%B %d, %Y")

company_data = json.load(open("app/extraordinary_events.json"))

campaign = st.selectbox("Email Campaign", company_data["system_prompt"].keys())
system_prompt = st.text_area(
    "System Prompt",
    company_data["system_prompt"][campaign].format(current_date=current_date),
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

st.dataframe(
    get_session()
    .table("SALES_CONTACTS")
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

            submit_prompt(system_prompt, user_prompt)

            if bar:
                bar.progress((i + 1) / len(user_prompts))
    st.success("Done!")
