import datetime
import decimal
from sqlalchemy import LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from supervisor.src.core.database import Base

class PlanDocument(Base):
    """Header of a monthly plan document (`_document5553`).

    Several docs get issued per month (observed: 2-4, likely one revision
    round per branch), and a plan persists unchanged in an agent's later
    docs until explicitly revised - see DATA/SALE_TREND.md. So "an agent's
    plan for month M" means the most recent tabular-part row for that agent
    dated on or before the end of M, not "the row from a doc dated in M."
    """

    __tablename__ = "_document5553"

    id: Mapped[bytes] = mapped_column("_idrref", LargeBinary(16), primary_key=True)
    number: Mapped[decimal.Decimal] = mapped_column("_number", Numeric)
    date_time: Mapped[datetime.datetime] = mapped_column("_date_time")
    # Branch this plan doc was issued for - only on the header, not the
    # tabular part. 100% match against a sample; see DATA/SALE_TREND.md.
    branch_ref: Mapped[bytes] = mapped_column("_fld5554rref", LargeBinary(16))
    is_posted: Mapped[bool] = mapped_column("_posted")
    is_marked_for_deletion: Mapped[bool] = mapped_column("_marked")


class PlanLineItem(Base):
    """Tabular part of a plan document (`_document5553_vt5564`) - one row
    per agent's plan amount. Row-number column confirmed as `_lineno5565`
    (checked live: unique per (document, lineno), 484 rows / 40 docs)."""

    __tablename__ = "_document5553_vt5564"

    document_ref: Mapped[bytes] = mapped_column("_document5553_idrref", LargeBinary(16), primary_key=True)
    line_no: Mapped[decimal.Decimal] = mapped_column("_lineno5565", Numeric, primary_key=True)
    agent_ref: Mapped[bytes] = mapped_column("_fld5566rref", LargeBinary(16))
    plan_amount: Mapped[decimal.Decimal] = mapped_column("_fld5568", Numeric)


class MonthlySalesRecord(Base):
    """Row in the sales/margin accumulation register (`_accumrg2546`) - the
    source of "actual revenue" for plan-vs-actual comparisons.

    Verified in DATA/SALE_TREND.md against two independent agents: `_fld2566`
    matched known actual-sales figures to within 0.0015%. The raw Orders
    total (`_document4542`) runs ~1.7% higher for the same period - it
    doesn't net out returns/corrections the way this register does, so it is
    NOT used here even though it's otherwise the "actual" source everywhere
    else in this codebase.

    1C accumulation registers have no single-row id; (period, agent_ref) is
    used as a read-only quasi-key here, matching how `Visit` (`_inforg5071`,
    also a register) is modeled - see models/visit.py.
    """

    __tablename__ = "_accumrg2546"

    period: Mapped[datetime.datetime] = mapped_column("_period", primary_key=True)
    agent_ref: Mapped[bytes] = mapped_column("_fld2554rref", LargeBinary(16), primary_key=True)
    amount: Mapped[decimal.Decimal] = mapped_column("_fld2566", Numeric)
