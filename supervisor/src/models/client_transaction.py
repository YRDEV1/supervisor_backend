import datetime
import decimal
from sqlalchemy import LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from supervisor.src.core.database import Base

class ClientTransaction(Base):
    """A row in the Client Income/Expense register (`_accumrg1435`)."""

    __tablename__ = "_accumrg1435"

    recorder_ref: Mapped[bytes] = mapped_column("_recorderrref", LargeBinary(16), primary_key=True)
    line_no: Mapped[int] = mapped_column("_lineno", primary_key=True)

    recorder_type_ref: Mapped[bytes] = mapped_column("_recordertref", LargeBinary(16))
    period: Mapped[datetime.datetime] = mapped_column("_period")
    is_active: Mapped[bool] = mapped_column("_active")
    record_kind: Mapped[int] = mapped_column("_recordkind")
    branch_ref: Mapped[bytes] = mapped_column("_fld1436rref", LargeBinary(16))
    client_ref: Mapped[bytes] = mapped_column("_fld1437rref", LargeBinary(16))
    currency_ref: Mapped[bytes] = mapped_column("_fld1438rref", LargeBinary(16))
    amount: Mapped[decimal.Decimal] = mapped_column("_fld1439", Numeric)

    def __repr__(self) -> str:
        return f"<ClientTransaction period={self.period!r} amount={self.amount!r}>"
