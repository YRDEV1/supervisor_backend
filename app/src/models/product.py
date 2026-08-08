import decimal
from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.src.core.database import Base

class Product(Base):
    """A row in the Products ("Nomenclature") catalog (`_reference1085`)."""

    __tablename__ = "_reference1085"

    id: Mapped[bytes] = mapped_column("_idrref", LargeBinary(16), primary_key=True)
    is_group: Mapped[bool] = mapped_column("_folder")
    is_marked_for_deletion: Mapped[bool] = mapped_column("_marked")
    parent_id: Mapped[bytes] = mapped_column("_parentidrref", LargeBinary(16))
    code: Mapped[str] = mapped_column("_code", String)
    full_name: Mapped[str] = mapped_column("_description")

    def __repr__(self) -> str:
        return f"<Product code={self.code!r} name={self.full_name!r}>"


# Root `_parentidrref` value shared by category headers (see DATA/TABLES.md).
ROOT_PARENT_ID = b"\x00" * 16
