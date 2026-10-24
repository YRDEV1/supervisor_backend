import decimal

from sqlalchemy import LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from agents.onec.database import OnecBase


class OrderLineItem(OnecBase):
    """Order product lines (`_document4542_vt4599`)."""

    __tablename__ = "_document4542_vt4599"

    order_ref: Mapped[bytes] = mapped_column("_document4542_idrref", LargeBinary(16), primary_key=True)
    line_no: Mapped[int] = mapped_column("_lineno", primary_key=True)
    product_ref: Mapped[bytes] = mapped_column("_fld4604rref", LargeBinary(16))
    quantity: Mapped[decimal.Decimal] = mapped_column("_fld4608", Numeric)
    sale_total: Mapped[decimal.Decimal] = mapped_column("_fld4617", Numeric)
    cost_total: Mapped[decimal.Decimal] = mapped_column("_fld4616", Numeric)
