from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from agents.onec.database import OnecBase


class Product(OnecBase):
    """Products catalog (`_reference1085`)."""

    __tablename__ = "_reference1085"

    id: Mapped[bytes] = mapped_column("_idrref", LargeBinary(16), primary_key=True)
    full_name: Mapped[str] = mapped_column("_description", String)
