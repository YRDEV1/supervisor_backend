import decimal
from sqlalchemy import LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from supervisor.src.core.database import Base
from supervisor.src.models.core import MVARCHAR

# Territories to hide from every endpoint that lists/filters by territory -
# closed/test/non-field entries the business asked to be excluded everywhere,
# not just from one endpoint.
EXCLUDED_TERRITORY_NAMES = [
    "Bekabod", "Boka", "Oqqorgon", "Oxangaron", "Toytepa 2",
    "Алмалык", "Ангрен", "Андижон", "Андижон 2", "Асака", "Ахангаран",
    "Кондитер", "Курилиш Моллари", "Мархамат", "Машкалар",
    "Наманган курилиш", "Тест", "Тошкент 1", "Тошкент 2",
    "Тугатилганлар",
]

class Territory(Base):
    """A row in the Territories catalog (`_reference4540`)."""

    __tablename__ = "_reference4540"

    # --- Identity & hierarchy -------------------------------------------------
    id: Mapped[bytes] = mapped_column("_idrref", LargeBinary(16), primary_key=True)
    version: Mapped[int] = mapped_column("_version")
    is_marked_for_deletion: Mapped[bool] = mapped_column("_marked")
    predefined_id: Mapped[bytes] = mapped_column("_predefinedid", LargeBinary(16))
    code: Mapped[decimal.Decimal] = mapped_column("_code", Numeric)
    territory_name: Mapped[str] = mapped_column("_description", MVARCHAR())

    # --- Linked catalog references ------------------------------------------------
    employee_ref: Mapped[bytes] = mapped_column("_fld4547rref", LargeBinary(16))  # Сотрудник
    user_ref: Mapped[bytes] = mapped_column("_fld4548rref", LargeBinary(16))  # Пользователь

    def __repr__(self) -> str:
        return f"<Territory code={self.code!r} name={self.territory_name!r}>"

class SupervisorTerritoryAssignment(Base):
    """A row in one of the Employee catalog's territory-assignment tabular
    parts (`_reference1109_vt4705`) - the direct, authoritative link between
    a supervisor (or agent) and their assigned territories, found by
    searching every bytea column for rows referencing both a known
    supervisor id and a known territory id together (see
    DATA/SUPERVISOR_TERRITORY.md). Supersedes every branch/visit-pooled
    proxy used elsewhere in this codebase - those silently mix together
    every supervisor sharing a branch, since the visit register only
    records branch-level identity, not the individual supervisor.

    Eight near-identical duplicate tabular parts exist
    (`_reference1109_vt4705` through `_vt4726`); this is one of them,
    picked arbitrarily since spot-checks found them in sync."""

    __tablename__ = "_reference1109_vt4705"

    employee_ref: Mapped[bytes] = mapped_column("_reference1109_idrref", LargeBinary(16), primary_key=True)
    line_no: Mapped[int] = mapped_column("_lineno4706", primary_key=True)
    territory_ref: Mapped[bytes] = mapped_column("_fld4707rref", LargeBinary(16))

class SupervisorActiveTerritoryAssignment(Base):
    """A row in the Employee catalog's `_reference1109_vt4708` tabular part -
    NOT a duplicate of `_vt4705` above despite the identical shape (see
    DATA/SUPERVISOR_TERRITORY.md's "Correction - the 8 tables are NOT
    duplicates"). `_vt4705` is the full historical superset, including
    territories no longer assigned ("excess"); `_vt4708` is a cleaner
    active-only subset that excludes exactly those excess entries -
    verified against a real 1C report for "Махкамов Отаёр СВ" (excludes all
    5 confirmed-excess territories, at the cost of also dropping one
    genuinely-current one no membership rule over these tables can recover).
    Neither table is fully authoritative for every employee (confirmed wrong
    for "Фазлиддин СВ"), but `_vt4708` is the best available approximation
    of an employee's *current* territory list - use `_vt4705` instead only
    when the full historical superset is actually what's wanted."""

    __tablename__ = "_reference1109_vt4708"

    employee_ref: Mapped[bytes] = mapped_column("_reference1109_idrref", LargeBinary(16), primary_key=True)
    line_no: Mapped[int] = mapped_column("_lineno4709", primary_key=True)
    territory_ref: Mapped[bytes] = mapped_column("_fld4710rref", LargeBinary(16))
