import streamlit as st
import os
import datetime
import json
import requests


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

    response = requests.post(
        url, headers=headers, data=json.dumps(payload), stream=True
    )

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
    for line in rbody:
        if line:
            if line.strip() == b"data: [DONE]":
                # return here will cause GeneratorExit exception in urllib3
                # and it will close http connection with TCP Reset
                return
            elif line.startswith(b"data: "):
                line = line[len(b"data: "):]
                yield json.loads(line.decode("utf-8"))
