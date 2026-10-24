from sqlalchemy import LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from agents.onec.database import OnecBase


class Visit(OnecBase):
    """Visit log (`_inforg5071`), agent column only."""

    __tablename__ = "_inforg5071"

    agent_ref: Mapped[bytes] = mapped_column("_fld5073rref", LargeBinary(16), primary_key=True)
