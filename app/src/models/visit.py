import datetime
import uuid
from sqlalchemy import LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from app.src.core.database import Base

class Visit(Base):
    """A row in the Visit log register (`_inforg5071`)."""

    __tablename__ = "_inforg5071"

    period: Mapped[datetime.datetime] = mapped_column("_period", primary_key=True)
    supervisor_individual_ref: Mapped[bytes] = mapped_column("_fld5072rref", LargeBinary(16), primary_key=True)
    agent_ref: Mapped[bytes] = mapped_column("_fld5073rref", LargeBinary(16), primary_key=True)
    outlet_ref: Mapped[bytes] = mapped_column("_fld5074rref", LargeBinary(16), primary_key=True)
    outcome_ref: Mapped[bytes] = mapped_column("_fld5386rref", LargeBinary(16))

    def __repr__(self) -> str:
        return f"<Visit period={self.period!r} agent_ref={self.agent_ref!r}>"


# Visit outcome ids inside `_reference4541`. See DATA/CLIENT.md.
VISIT_OUTCOME_CHECK_IN = uuid.UUID("a738005056070e0911f04071d0141858")  # Дуконга кирдим
VISIT_OUTCOME_CHECK_OUT = uuid.UUID("b512f0d4155608d711f08a4607a91bfb")  # Дукондан чикдим
