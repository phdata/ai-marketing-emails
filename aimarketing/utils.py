import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx
import os
import datetime
import json
import requests

from aimarketing.snowflake_utils import get_snowpark_session


def get_session():
    using_streamlit = get_script_run_ctx() is not None
    if using_streamlit and "snowflake_session" in st.session_state:
        return st.session_state.snowflake_session

    session = get_snowpark_session()

    if using_streamlit:
        st.session_state.snowflake_session = session

    return session


def submit_prompt(system_prompt, user_prompt, log=True, openai=False):
    url = "https://api.openai.com/v1/chat/completions"

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": True,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.environ.get("OPENAI_API_KEY"),
    }

    # retry until response is valid
    retry = 0
    while retry < 5:
        response = requests.post(
            url, headers=headers, data=json.dumps(payload), stream=True
        )
        if response.status_code == 200:
            break
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            retry += 1
            if retry == 5:
                raise Exception("Failed to get response from OpenAI")

    response_container = st.empty()
    collected_messages = []
    for chunk in parse_stream(response.iter_lines()):
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


def parse_stream(rbody):
    prefix = b"data: "
    len_prefix = len(prefix)
    for line in rbody:
        if line:
            if line.strip() == b"data: [DONE]":
                return
            elif line.startswith(prefix):
                line = line[len_prefix:]
                yield json.loads(line.decode("utf-8"))
