from aimarketing.snowflake_utils import get_snowpark_session
import click


@click.command()
def main():
    session = get_snowpark_session()

    session.sql("create or replace stage udf_stage").collect()
    session.udf.register_from_file(
        file_path="aimarketing/date_utils.py",
        func_name="humanize_date",
        name="humanize_date",
        is_permanent=True,
        replace=True,
        stage_location="@udf_stage",
    )
    session.file.put(
        "aimarketing/utils.py",
        "@udf_stage/submit_gpt_prompt",
        overwrite=True,
    )
    session.sql(
        """
CREATE OR REPLACE
FUNCTION  submit_gpt_prompt(systemprompt STRING, userprompt STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION=3.8
HANDLER='utils.submit_prompt_udf'
EXTERNAL_ACCESS_INTEGRATIONS = (openai_api_access_integration)
PACKAGES=('requests','tenacity','cloudpickle==2.0.0')
IMPORTS=('@udf_stage/submit_gpt_prompt/utils.py')
SECRETS = ('OPENAI_API_KEY' = openai_token)
    """
    ).collect()

    print(
        session.sql(
            "select humanize_date(date_from_parts(2022,12,1), date_from_parts(2023,5,22)) as event;"
        ).collect()
    )
    system_prompt = r"""
    You are a poet that specializes in limericks. The standard form of a
    limerick is a stanza of five lines, with the first, second and fifth rhyming
    with one another and having three feet of three syllables each; and the
    shorter third and fourth lines also rhyming with each other, but having only
    two feet of three syllables. Start the limerick with \'there was once\'
    """
    user_prompt = "Write a limerick about data and Snowflake"
    print(
        session.sql(
            f"select submit_gpt_prompt('{system_prompt}', '{user_prompt}') as response;"
        ).collect()
    )


if __name__ == "__main__":
    main()
