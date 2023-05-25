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

    return full_reply_content


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


def humanize_with_gpt(
    date: datetime.date, current_date: datetime.date = datetime.date.today()
):
    url = "https://api.openai.com/v1/completions"

    payload = {
        "model": "text-davinci-003",
        "prompt": f"""Answer each question about dates. Prefer imprecise but accurate answers like "last month" instead of "four weeks ago" and "last week" instead of "5 days ago".
Q: The current date is May 25th, 2023. How long ago is May 18th, 2023?
A: last Thursday

Q: The current date is October 9th, 2023. How long ago is May 18th, 2023?
A: last May

Q: The current date is Monday, May 22nd, 2023. How long ago is Saturday, May 20th, 2023?
A: last weekend

Q: The current date is April 3rd, 2021. How long ago is December 15th, 2020
A: a few months ago

Q: The current date is July 3rd, 2023. How long ago is April 2nd, 2021
A: a couple years back

Q: The current date is Wednesday, August 17th, 2022. How long ago is Saturday, August 6th, 2022?
A: a couple weeks ago

Q: The current date is {current_date.strftime("%A, %B %d, %Y")}. How long ago is {date.strftime("%A, %B %d, %Y")}?
A:""",
        "temperature": 0.0,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.environ.get("OPENAI_API_KEY"),
    }

    # retry until response is valid
    retry = 0
    while retry < 5:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            break
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            retry += 1
            if retry == 5:
                raise Exception("Failed to get response from OpenAI")

    return json.loads(response.content)["choices"][0]["text"]


if __name__ == "__main__":
    current_date = datetime.date.today()

    for i in range(0, 45, 3):
        date = current_date - datetime.timedelta(days=i)
        print(date, "=>", humanize_with_gpt(date, current_date))

    for i in range(45, 600, 30):
        date = current_date - datetime.timedelta(days=i)
        print(date, "=>", humanize_with_gpt(date, current_date))
