import streamlit as st
import json

from aimarketing.utils import submit_prompt


def main(data):
    products = data["products"]
    tones = data["tones"]
    if "edit_prompt" not in st.session_state:
        st.session_state["edit_prompt"] = False
    # Side by side select box for each field
    with st.container():
        st.subheader("Customer")
        cols = st.columns(2)
        with cols[0]:
            name = st.text_input("Name", "John")
            gender = st.selectbox("Gender", data["genders"])
        with cols[1]:
            demographic = st.selectbox("Demographics", data["demographics"])
            customer_segment = st.selectbox("Customer Segment", data["segment"])

    with st.container():
        st.subheader("Email Info")
        cols = st.columns(2)
        tone = cols[0].selectbox("Tone", tones.keys())
        product = cols[1].selectbox("Product", products.keys())

    # Create an OpenGPT prompt that generates a marketing email with the selections
    prompt = f"""Name: {name}
    Gender: {gender}
    Product: {product}
    Product Description: {products[product]}
    Demographics: {demographic}
    Customer Segment: {customer_segment}
    {tones[tone]}
    """
    st.header("OpenAI GPT Prompt")
    if st.button("Edit Prompt") or st.session_state.edit_prompt:
        st.session_state["edit_prompt"] = True
        final_prompt = st.text_area(
            "Prompt", prompt, height=500, max_chars=None, key=None
        )
    else:
        for line in prompt.split("\n"):
            st.write(line)
        final_prompt = prompt

    system_prompt = data["system_prompt"]
    # Create a button to call the OpenAI API
    if st.button("Generate Email"):
        # Load your API key from an environment variable or secret management service

        # create a chat completion
        with st.spinner("Generating..."):
            submit_prompt(system_prompt, final_prompt)
        st.success("Done!")


DATA_FILE = "app/cool_collectibles.json"
data = json.load(open(DATA_FILE))
main(data)
