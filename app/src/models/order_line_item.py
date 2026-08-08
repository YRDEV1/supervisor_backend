import decimal
from sqlalchemy import LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.src.core.database import Base

class OrderLineItem(Base):
    """A row in the Orders tabular part (`_document4542_vt4599`) - one
    product line per order. `_lineno` is assumed (standard 1C tabular-part
    row-number column, not explicitly confirmed in DATA/ORDERS.md).
    """

    __tablename__ = "_document4542_vt4599"

    order_ref: Mapped[bytes] = mapped_column("_document4542_idrref", LargeBinary(16), primary_key=True)
    line_no: Mapped[int] = mapped_column("_lineno", primary_key=True)
    product_ref: Mapped[bytes] = mapped_column("_fld4604rref", LargeBinary(16))
    quantity: Mapped[decimal.Decimal] = mapped_column("_fld4608", Numeric)
    sale_total: Mapped[decimal.Decimal] = mapped_column("_fld4617", Numeric)  # Line total, sale side
    cost_total: Mapped[decimal.Decimal] = mapped_column("_fld4616", Numeric)  # Line total, cost side

    def __repr__(self) -> str:
        return f"<OrderLineItem product_ref={self.product_ref!r} quantity={self.quantity!r}>"
