# Streamlit app that has drop down fields and passes selections to OpenAPI call

import streamlit as st
import json
from pages import edit, generate_email

DATA_FILE = "app/data.json"

data = json.load(open(DATA_FILE))

with st.sidebar:
    mode = st.selectbox("Mode", ["Generate", "Edit Data"])

if mode == "Generate":
    generate_email.main(data)
elif mode == "Edit Data":
    edit.main(data, DATA_FILE)
