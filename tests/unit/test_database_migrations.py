from unittest.mock import MagicMock, patch

from sqlalchemy import String
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import Engine

from backend.database import (
    CATALOG_NUMBER_MAX_LENGTH,
    VinylRecord,
    ensure_catalog_number_capacity,
)


def test_catalog_number_column_is_wide_enough():
    column = VinylRecord.__table__.c.catalog_number

    assert column.type.length == CATALOG_NUMBER_MAX_LENGTH


def test_existing_postgres_catalog_number_column_is_widened():
    engine = MagicMock(spec=Engine)
    engine.dialect = postgresql.dialect()
    connection = MagicMock()
    engine.begin.return_value.__enter__.return_value = connection

    with patch(
        "backend.database.inspect",
        return_value=MagicMock(
            get_columns=MagicMock(
                return_value=[{"name": "catalog_number", "type": String(50)}]
            )
        ),
    ):
        ensure_catalog_number_capacity(engine)

    connection.execute.assert_called_once()
    assert f"VARCHAR({CATALOG_NUMBER_MAX_LENGTH})" in str(
        connection.execute.call_args.args[0]
    )


def test_catalog_number_migration_is_idempotent():
    engine = MagicMock(spec=Engine)
    engine.dialect = postgresql.dialect()

    with patch(
        "backend.database.inspect",
        return_value=MagicMock(
            get_columns=MagicMock(
                return_value=[
                    {
                        "name": "catalog_number",
                        "type": String(CATALOG_NUMBER_MAX_LENGTH),
                    }
                ]
            )
        ),
    ):
        ensure_catalog_number_capacity(engine)

    engine.begin.assert_not_called()


def test_catalog_number_migration_skips_non_postgres_database():
    engine = MagicMock(spec=Engine)
    engine.dialect = sqlite.dialect()

    with patch("backend.database.inspect") as inspect_mock:
        ensure_catalog_number_capacity(engine)

    inspect_mock.assert_not_called()
    engine.begin.assert_not_called()
