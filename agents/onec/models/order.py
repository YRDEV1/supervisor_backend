import datetime
import decimal

from sqlalchemy import LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from agents.onec.database import OnecBase


class Order(OnecBase):
    """Orders header (`_document4542`)."""

    __tablename__ = "_document4542"

    id: Mapped[bytes] = mapped_column("_idrref", LargeBinary(16), primary_key=True)
    date_time: Mapped[datetime.datetime] = mapped_column("_date_time")
    client_ref: Mapped[bytes] = mapped_column("_fld4567_rrref", LargeBinary(16))
    agent_ref: Mapped[bytes] = mapped_column("_fld4564rref", LargeBinary(16))
    total: Mapped[decimal.Decimal] = mapped_column("_fld4570", Numeric)
