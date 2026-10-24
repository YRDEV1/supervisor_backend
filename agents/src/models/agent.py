import datetime

from sqlalchemy import Index, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agents.src.core.database import Base
from agents.src.utils.utils import utcnow


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("agent_name", name="uq_agents_agent_name"),
        Index("ix_agents_supervisor_id", "supervisor_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supervisor_id: Mapped[bytes] = mapped_column(LargeBinary(16))
    agent_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime.datetime] = mapped_column(default=utcnow)
