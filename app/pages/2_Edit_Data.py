import streamlit as st
import json
from pathlib import Path
import time


def save(data, filename):
    json.dump(data, open(filename, "w"), indent=2)
    st.success(f"Saved {filename}")


def main(data, data_file):
    st.header("Edit Data")
    data_file = Path(data_file)
    if st.button("Backup File"):
        backup_file = data_file.with_name(
            f"{data_file.stem}_{time.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        )
        save(data, backup_file)
    data_field = st.selectbox("Edit", data.keys())

    if isinstance(data[data_field], dict):
        with st.expander("Add/Remove Key"):
            col1, col2 = st.columns(2)
            with col1:
                new_key = st.text_input("Key")
            with col2:
                if st.button("Add Key"):
                    data[data_field].append(new_key)
                    save(data, data_file)
                if st.button("Remove Key"):
                    data[data_field].remove(new_key)
                    save(data, data_file)

        key = st.selectbox("Key", data[data_field].keys(), key="selectkeys")
        value = st.text_area("Value", data[data_field][key], height=200)

        if st.button("Save"):
            data[data_field][key] = value
            save(data, data_file)
    elif isinstance(data[data_field], list):
        for row in data[data_field]:
            if row == "":
                continue
            st.markdown(f" - {row}")
        st.markdown("#### Add/Remove Value")
        col1, col2 = st.columns(2)
        with col1:
            new_key = st.text_input("Value")
        with col2:
            if st.button("Add Value"):
                data[data_field].append(new_key)
                save(data, data_file)
            if st.button("Remove Value"):
                data[data_field].remove(new_key)
                save(data, data_file)
    elif isinstance(data[data_field], str):
        value = st.text_area("Value", data[data_field], height=200)

        if st.button("Save"):
            data[data_field] = value
            save(data, data_file)


DATA_FILE = "app/data.json"
data = json.load(open(DATA_FILE))
main(data, DATA_FILE)