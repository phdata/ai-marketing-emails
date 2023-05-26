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
conda activate ./.venv
pip install -e .
```

## Setup Snowflake Connector
Create `~/.snowsql/config`
```toml
[connections.aws]
accountname = ACCOUNT_IDENTIFIER
username = USERNAME
dbname = SANDBOX
schemaname = AI_MARKETING
warehousename = PHDATA
rolename = DATASCIENCE
private_key_path = /path/to//rsa_key.p8
```
If you want to authenticate with password, replace `private_key_path` with `password`. The Snowflake Python connector expects an environment variable "PRIVATE_KEY_PASSPHRASE" to use the specified private key.

## Run
```bash
export OPENAI_API_KEY="sk-****"
python sql/setup.py
python -m streamlit run app/main.py
```
