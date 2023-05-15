import streamlit as st
import json

DATA_FILE = "app/data.json"
data = json.load(open(DATA_FILE))

st.markdown(open("README.md").read())
