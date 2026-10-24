import decimal
import uuid

from sqlalchemy import LargeBinary, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from agents.onec.database import OnecBase


class Employee(OnecBase):
    """Employees catalog (`_reference1109`), used columns only."""

    __tablename__ = "_reference1109"

    id: Mapped[bytes] = mapped_column("_idrref", LargeBinary(16), primary_key=True)
    is_marked_for_deletion: Mapped[bool] = mapped_column("_marked")

    # Role group row (СВ / ТП)
    parent_id: Mapped[bytes] = mapped_column("_parentidrref", LargeBinary(16))

    code: Mapped[decimal.Decimal] = mapped_column("_code", Numeric)
    full_name: Mapped[str] = mapped_column("_description", String)


# Role group ids
ROLE_SUPERVISOR = uuid.UUID("a73a0050-5607-0e09-11f0-50e1332c7fcd")  # СВ
