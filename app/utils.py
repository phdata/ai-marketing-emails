import openai
import streamlit as st
import os

openai.api_key = os.environ.get("OPENAI_API_KEY")


def submit_prompt(system_prompt, user_prompt):
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
        chunk_message = chunk["choices"][0]["delta"]  # extract the message
        collected_messages.append(chunk_message)
        full_reply_content = "".join([m.get("content", "") for m in collected_messages])
        response_container.write(full_reply_content)
