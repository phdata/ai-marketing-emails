import streamlit as st
import json
import time
import pandas as pd

from utils import submit_prompt


def format_user_prompt(contact_name, **kwargs):
    user_prompt = f"Company: {contact_name}\n"
    user_prompt += f"Industry: {kwargs.get('industry', 'N/A')}\n"
    user_prompt += f"Contact Type: {kwargs.get('contact_type', 'N/A')}\n"
    return user_prompt


def print_prompt(user_prompt):
    st.markdown("  \n".join(f"**{line}**" for line in user_prompt.split("\n")))


st.header("Generate Email using a Template")

# Current date using natural language
current_date = time.strftime("%B %d, %Y")

company_data = json.load(open("app/extraordinary_events.json"))
contacts = company_data['contacts']

system_prompt = st.text_area(
    "System Prompt",
    company_data['system_prompt'].format(current_date=current_date),
    height=400,
)

st.subheader("Select contact data")
all_data = st.checkbox("Generate Emails for All Contacts")
if all_data:
    contact_df = pd.DataFrame(contacts).T
    contact_df.index.name = "Company Name"
    contact_df = contact_df.reset_index()
    st.dataframe(contact_df.style.hide())
    user_prompts = {
        contact: format_user_prompt(contact_name=contact, **contacts[contact])
        for contact in contacts.keys()
    }
else:
    contact = st.selectbox("Contact", contacts.keys())
    user_prompt = format_user_prompt(contact_name=contact, **contacts[contact])
    print_prompt(user_prompt)
    user_prompts = {contact: user_prompt}


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
