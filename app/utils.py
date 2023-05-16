import openai
import streamlit as st
import os
import datetime

openai.api_key = os.environ.get("OPENAI_API_KEY")


def submit_prompt(system_prompt, user_prompt, log=True):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
    )
    response_container = st.empty()
    collected_messages = []

    # print out partial progress
    for chunk in response:
        chunk_message = chunk["choices"][0]["delta"]
        collected_messages.append(chunk_message)
        full_reply_content = "".join([m.get("content", "") for m in collected_messages])
        response_container.write(full_reply_content)

    with open("app/log.md", "a") as f:
        f.write(f"# {datetime.datetime.now()}\n")
        prompt_markdown = "  \n".join(system_prompt.split("\n"))
        f.write(f"## System Prompt\n{prompt_markdown}\n")
        prompt_markdown = "  \n".join(user_prompt.split("\n"))
        f.write(f"## User Prompt\n{prompt_markdown}\n")
        f.write(f"## Reply\n{full_reply_content}\n")
