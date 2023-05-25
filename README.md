## AI Marketing

- `app` : Streamlit app that integrates with Snowflake to generate prompts for OpenAI ChatGPT API and write the results back to Snowflake tables. 
- `app/main.py`: App Homepage
- `app/extraordinary_events.json`: JSON file with system prompts for email generation.
- `app/pages/1_Generate_E-mails.py`: Streamlit page with interface for crafting prompts and reading generated emails
- `app/pages/2_Edit_Data.py`: Streamlit page for editting persistent app data.
- `app/pages/4_Browse_Log.py`: Streamlit page that renders history of all prompts generated.
- `sql/setup.py`: Python script that uploads `extraordinary_events.csv` to Snowflake account and creates useful UDFs.
- `aimarketing/`: handful of utility functions.
- `environment.yml`: environment for streamlit app. Limits to Snowflake repository so app could be run in Snowflake.
- `pyproject.toml`: Allows `pip install -e .` for utility functions.


## Setup Environemnt

```bash
conda env create --file environment.yml --prefix ./.venv
pip install -e .
```
