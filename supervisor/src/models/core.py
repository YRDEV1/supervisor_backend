from sqlalchemy.types import UserDefinedType


class MVARCHAR(UserDefinedType):
    """Tells asyncpg/SQLAlchemy to treat parameters as 1C's native mvarchar.

    This DB export's `mvarchar` columns have no operator against a plain
    `varchar`/`character varying` bind (SQLAlchemy's asyncpg dialect casts
    string parameters to `::VARCHAR` by default) - comparisons like
    `Employee.login == "7002"` fail with "operator does not exist: mvarchar
    = character varying". Typing the column as MVARCHAR instead of the
    inferred `String` stops that cast from being added, so the parameter
    reaches Postgres untyped and coerces against `mvarchar` the same way a
    plain SQL string literal does.
    """
    cache_ok = True

    def get_col_spec(self, **kw):
        return "mvarchar"

    # Optional: ensure values are bound correctly as strings
    def bind_processor(self, dialect):
        def process(value):
            return str(value) if value is not None else None
        return process
