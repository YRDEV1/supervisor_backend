import datetime
import decimal
import uuid
from sqlalchemy import LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from supervisor.src.core.database import Base

class Order(Base):
    """A row in the Orders document header (`_document4542`)."""

    __tablename__ = "_document4542"

    id: Mapped[bytes] = mapped_column("_idrref", LargeBinary(16), primary_key=True)
    number: Mapped[decimal.Decimal] = mapped_column("_number", Numeric)
    date_time: Mapped[datetime.datetime] = mapped_column("_date_time")
    is_posted: Mapped[bool] = mapped_column("_posted")
    client_ref: Mapped[bytes] = mapped_column("_fld4567_rrref", LargeBinary(16))
    branch_ref: Mapped[bytes] = mapped_column("_fld4561rref", LargeBinary(16))
    agent_ref: Mapped[bytes] = mapped_column("_fld4564rref", LargeBinary(16))
    status_ref: Mapped[bytes] = mapped_column("_fld4562rref", LargeBinary(16))
    total: Mapped[decimal.Decimal] = mapped_column("_fld4570", Numeric)

    def __repr__(self) -> str:
        return f"<Order number={self.number!r} total={self.total!r}>"


# `_fld4562rref` values, enum-backed via `_enum4544` (see DATA/ORDERS.md).
# 1C `_enum*` tables store no caption text in SQL, so only the dominant
# value (96.9% share) has a confident guessed label; the rest are unconfirmed.
ORDER_STATUS_LABELS: dict[uuid.UUID, str] = {
    uuid.UUID("8f44cc78-8478-ce0d-4b52-6daec28af15e"): "Доставлено",
}
ORDER_STATUS_UNKNOWN_LABEL = "Номаълум"


def get_order_status_label(status_ref: bytes | None) -> str:
    if status_ref is None:
        return ORDER_STATUS_UNKNOWN_LABEL
    return ORDER_STATUS_LABELS.get(uuid.UUID(bytes=status_ref), ORDER_STATUS_UNKNOWN_LABEL)


def get_order_status_filter(status: str):
    labeled_refs = [status_ref.bytes for status_ref, label in ORDER_STATUS_LABELS.items()]
    matching_refs = [status_ref.bytes for status_ref, label in ORDER_STATUS_LABELS.items() if label == status]
    if matching_refs:
        return Order.status_ref.in_(matching_refs)
    # Any label we can't map to a known enum ref (including "Номаълум") falls
    # back to "every ref that isn't one of the known/labeled ones".
    return Order.status_ref.notin_(labeled_refs) if labeled_refs else True
