import click
from aimarketing.snowflake_utils import get_snowpark_session

from snowflake.snowpark.types import (
    StructType,
    StructField,
    StringType,
    DateType,
    IntegerType,
)

from pathlib import Path


@click.command()
@click.option("--drop-tables", is_flag=True, help="Drop all tables")
def main(drop_tables):
    session = get_snowpark_session()

    session.sql("drop table if exists SANDBOX.AI_MARKETING.SALES_CONTACTS").collect()
    session.sql("create or replace temporary stage temp_stage").collect()
    session.file.put(
        str(Path("extraordinary_events.csv").absolute()),
        "@temp_stage/extraordinary_events",
        overwrite=True,
    )
    user_schema = StructType(
        [
            StructField("UID", IntegerType()),
            StructField("COMPANY_NAME", StringType()),
            StructField("CONTACT_NAME", StringType()),
            StructField("CONTACT_EMAIL", StringType()),
            StructField("INDUSTRY", StringType()),
            StructField("PREVIOUS_EVENT", StringType()),
            StructField("PREVIOUS_EVENT_DATE", DateType()),
            StructField("NOTES", StringType()),
        ]
    )

    session.sql("drop table if exists copied_into_table").collect()
    df = (
        session.read.schema(user_schema)
        .options(
            dict(SKIP_HEADER=1, FIELD_OPTIONALLY_ENCLOSED_BY='"', FIELD_DELIMITER=",")
        )
        .csv("@temp_stage/extraordinary_events")
    )
    df.copy_into_table("SALES_CONTACTS", force=True)

    session.sql("create or replace stage udf_stage").collect()
    session.udf.register_from_file(
        file_path="aimarketing/date_utils.py",
        func_name="humanize_date",
        name="humanize_date",
        is_permanent=True,
        replace=True,
        stage_location="@udf_stage",
    )

    print(
        session.sql(
            "select humanize_date(date_from_parts(2022,12,1), date_from_parts(2023,5,22)) as event;"
        ).collect()
    )

    session.sql(
        """create or replace view SANDBOX.AI_MARKETING.GPT_EMAIL_PROMPTS_LATEST(
            UID, CONTACT_EMAIL, CAMPAIGN_NAME, EMAIL
        ) as
        SELECT UID, CONTACT_EMAIL, CAMPAIGN_NAME, EMAIL
        FROM (
            SELECT UID, CONTACT_EMAIL, CAMPAIGN_NAME, EMAIL,
                ROW_NUMBER() OVER (PARTITION BY UID ORDER BY TIMESTAMP DESC) AS rn
            FROM GPT_EMAIL_PROMPTS
        ) t
        WHERE rn = 1;"""
    )
    if drop_tables:
        session.sql(
            "drop table if exists SANDBOX.AI_MARKETING.GPT_EMAIL_PROMPTS"
        ).collect()


if __name__ == "__main__":
    main()
