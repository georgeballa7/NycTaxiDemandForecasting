from collections.abc import Sequence

import pandas as pd
from sqlalchemy import MetaData, Table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine


def upsert_dataframe(
    dataframe: pd.DataFrame,
    table_name: str,
    key_columns: Sequence[str],
    db_engine: Engine,
    schema: str,
    update_columns: Sequence[str] | None = None,
    chunk_size: int = 5000,
) -> None:
    """Insert a DataFrame into PostgreSQL and update matching primary keys."""

    if dataframe.empty:
        return

    metadata = MetaData()
    table = Table(
        table_name,
        metadata,
        schema=schema,
        autoload_with=db_engine,
    )

    records = dataframe.where(
        pd.notna(dataframe), None
    ).to_dict(orient="records")

    if update_columns is None:
        update_columns = [
            column
            for column in dataframe.columns
            if column not in key_columns
        ]

    with db_engine.begin() as connection:
        for start in range(0, len(records), chunk_size):
            batch = records[start:start + chunk_size]
            statement = insert(table).values(batch)

            if update_columns:
                statement = statement.on_conflict_do_update(
                    index_elements=list(key_columns),
                    set_={
                        column: getattr(statement.excluded, column)
                        for column in update_columns
                    },
                )
            else:
                statement = statement.on_conflict_do_nothing(
                    index_elements=list(key_columns)
                )

            connection.execute(statement)
