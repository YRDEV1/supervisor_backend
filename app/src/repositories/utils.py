from sqlalchemy.future import select


async def fetch_names(session, id_column, name_column, ids: list[bytes]) -> dict[bytes, str]:
    """Resolve id -> name for `mvarchar` name columns.

    `_description`-style columns are `mvarchar` with no collation, so Postgres
    rejects them in GROUP BY/ORDER BY/LIKE. Aggregate queries therefore group
    by the `bytea` id only and resolve names with this plain SELECT, which
    needs no collation.
    """
    if not ids:
        return {}
    query = select(id_column, name_column).where(id_column.in_(ids))
    rows = (await session.execute(query)).all()
    return {row[0]: row[1] for row in rows}
