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
    chunk_size: int = 1000,
) -> None:
    """Insert or update Pandas rows in a PostgreSQL table in batches.

    Parameters
    ----------
    dataframe : pd.DataFrame
        Rows to persist; pandas missing values are converted to None.
    table_name : str
        Target table name.
    key_columns : Sequence[str]
        Columns used as the PostgreSQL conflict key.
    db_engine : Engine
        SQLAlchemy engine connected to the target database.
    schema : str
        PostgreSQL schema containing the target table.
    update_columns : Sequence[str] or None
        Columns updated on conflict. When omitted, all non-key DataFrame
        columns are updated.
    chunk_size : int
        Maximum number of records sent in each database statement.

    Returns
    -------
    None
        Database changes are committed as a side effect. Empty DataFrames
        return immediately.

    Notes
    -----
    When update_columns is empty, conflicts are ignored instead of updated.
    All batches run inside one SQLAlchemy transaction.
    """

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
