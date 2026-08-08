import decimal
from sqlalchemy import LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.src.core.database import Base

class Territory(Base):
    """A row in the Territories catalog (`_reference4540`)."""

    __tablename__ = "_reference4540"

    # --- Identity & hierarchy -------------------------------------------------
    id: Mapped[bytes] = mapped_column("_idrref", LargeBinary(16), primary_key=True)
    version: Mapped[int] = mapped_column("_version")
    is_marked_for_deletion: Mapped[bool] = mapped_column("_marked")
    predefined_id: Mapped[bytes] = mapped_column("_predefinedid", LargeBinary(16))
    code: Mapped[decimal.Decimal] = mapped_column("_code", Numeric)
    territory_name: Mapped[str] = mapped_column("_description")

    # --- Linked catalog references ------------------------------------------------
    employee_ref: Mapped[bytes] = mapped_column("_fld4547rref", LargeBinary(16))  # Сотрудник
    user_ref: Mapped[bytes] = mapped_column("_fld4548rref", LargeBinary(16))  # Пользователь

    def __repr__(self) -> str:
        return f"<Territory code={self.code!r} name={self.territory_name!r}>"
