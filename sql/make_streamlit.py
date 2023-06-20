import click
from aimarketing.snowflake_utils import embed_imports_for_streamlit, get_snowpark_session
from tempfile import TemporaryDirectory


from pathlib import Path


@click.command()
@click.option("--update", is_flag=True, help="Update streamlit file.")
def main(update):
    """
    Create streamlit app in snowflake environment and upload files to it.
    """
    session = get_snowpark_session()

    session.sql("CREATE OR REPLACE STAGE generate_email_stage").collect()

    streamlit_app_filename = str(
        Path(__file__).parent.parent / "app/pages/1_Generate_E-mails.py"
    )
    streamlit_app_source = open(streamlit_app_filename, "r").read()

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/streamlit_app.py", "w") as f:
            f.write(embed_imports_for_streamlit(streamlit_app_source))

        session.file.put(
            f"{temp_dir}/streamlit_app.py",
            "@generate_email_stage",
            overwrite=True,
            auto_compress=False,
        )

    session.file.put(
        "extraordinary_events.json",
        "@generate_email_stage",
        overwrite=True,
        auto_compress=False,
    )
    session.sql(
        f"""
    create or replace STREAMLIT generate_email
    ROOT_LOCATION = '@{session.get_current_database()}.{session.get_current_schema()}.generate_email_stage'
    MAIN_FILE = '/streamlit_app.py'
    QUERY_WAREHOUSE = {session.get_current_warehouse()}
    TITLE = 'Generate E-mails with GPT';
    """).collect()

    session.sql("grant usage on streamlit generate_email to ROLE DE_ARCHITECTS;").collect()
    session.sql("grant usage on streamlit generate_email to ROLE MLE_ARCHITECTS;").collect()


if __name__ == "__main__":
    main()
