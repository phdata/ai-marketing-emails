import click
from aimarketing.utils import get_session
from snowflake.snowpark.types import StructType, StructField, StringType, DateType

from pathlib import Path


@click.command()
def main():
    session = get_session()

    session.sql("drop table if exists SANDBOX.AI_MARKETING.SALES_CONTACTS").collect()
    session.sql("create or replace temporary stage temp_stage").collect()
    session.file.put(
        str(Path("extraordinary_events.csv").absolute()),
        "@temp_stage/extraordinary_events",
        overwrite=True,
    )
    user_schema = StructType(
        [
            StructField("COMPANY_NAME", StringType()),
            StructField("SALES_REP", StringType()),
            StructField("SALES_REP_EMAIL", StringType()),
            StructField("INDUSTRY", StringType()),
            StructField("PREVIOUS_EVENT", StringType()),
            StructField("PREVIOUS_EVENT_DATE", DateType()),
            StructField("NOTES", StringType()),
        ]
    )

    session.sql("drop table if exists copied_into_table").collect()
    df = (
        session.read.schema(user_schema)
        .options(dict(SKIP_HEADER=1, FIELD_OPTIONALLY_ENCLOSED_BY='"', FIELD_DELIMITER=","))
        .csv("@temp_stage/extraordinary_events")
    )
    df.copy_into_table("SALES_CONTACTS", force=True)


if __name__ == "__main__":
    main()
