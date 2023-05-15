import streamlit as st
import json
import time

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

system_prompt = st.text_area(
    "System Prompt",
    f"""You are a sales representative for Extraordinary Events, an event-planning
business that focuses on the planning and execution of marketing events for
other companies.  Current date: {current_date}. You are writing emails as concisely
as possible to potential customers that the company recently had contact with.
You are trying to start a relationship with this company and find out what needs
they have.  The email should be very brief.  Write an effective call to action
using action-oriented language and creating a sense of urgency.

Hi [Company Name],
[Short greeting]
[Respond to method of contact]
[Call to action]
Sincerely,
Peter Hansen""",
    height=400,
)
contacts = json.load(open("app/contacts.json"))["contacts"]

st.subheader("Select a contact or Generate All")
all_emails = st.button("Generate All Emails")
contact = st.selectbox("Contact", contacts.keys())

if not all_emails:
    user_prompt = format_user_prompt(contact_name=contact, **contacts[contact])
    print_prompt(user_prompt)


if st.button("Generate One Email") or all_emails:
    # create a chat completion
    if not all_emails:
        user_prompts = {contact: user_prompt}
    else:
        user_prompts = {
            contact: format_user_prompt(contact_name=contact, **contacts[contact])
            for contact in contacts.keys()
        }

    if len(user_prompts) > 1:
        bar = st.progress(0)
    else:
        bar = None
    with st.spinner("Generating..."):
        for i, (contact, user_prompt) in enumerate(user_prompts.items()):
            if all_emails:
                st.subheader(contact)
                print_prompt(user_prompt)

            submit_prompt(system_prompt, user_prompt)

            if bar:
                bar.progress((i + 1) / len(user_prompts))
    st.success("Done!")
