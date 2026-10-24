import decimal
from sqlalchemy import LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from supervisor.src.core.database import Base
from supervisor.src.models.core import MVARCHAR

class Client(Base):
    """A row in the Outlets/Clients catalog (`_reference1099`)."""

    __tablename__ = "_reference1099"

    id: Mapped[bytes] = mapped_column("_idrref", LargeBinary(16), primary_key=True)
    version: Mapped[int] = mapped_column("_version")
    is_marked_for_deletion: Mapped[bool] = mapped_column("_marked")
    predefined_id: Mapped[bytes] = mapped_column("_predefinedid", LargeBinary(16))
    parent_id: Mapped[bytes] = mapped_column("_parentidrref", LargeBinary(16))
    is_group: Mapped[bool] = mapped_column("_folder")
    code: Mapped[decimal.Decimal] = mapped_column("_code", Numeric)
    full_name: Mapped[str] = mapped_column("_description", MVARCHAR())
    phone: Mapped[str] = mapped_column("_fld1102", MVARCHAR())
    territory_ref: Mapped[bytes] = mapped_column("_fld4696rref", LargeBinary(16))
    agent_ref: Mapped[bytes] = mapped_column("_fld2267rref", LargeBinary(16))
    latitude: Mapped[str] = mapped_column("_fld4697")
    longitude: Mapped[str] = mapped_column("_fld4698")

    def __repr__(self) -> str:
        return f"<Client code={self.code!r} name={self.full_name!r}>"
