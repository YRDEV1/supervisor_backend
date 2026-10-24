import datetime

from sqlalchemy.future import select

from supervisor.src.core.database import ASYNC_SESSION
from supervisor.src.models.income_expense import IncomeExpense

class IncomeExpenseRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_all(self, from_date: datetime.datetime, to_date: datetime.datetime, employee_id: bytes,
                       branch_id: bytes | None = None):
        query = select(IncomeExpense.period, IncomeExpense.record_kind, IncomeExpense.amount,
                       IncomeExpense.branch_ref, IncomeExpense.employee_ref).where(
            IncomeExpense.period >= from_date, IncomeExpense.period < to_date,
            IncomeExpense.employee_ref == employee_id)
        if branch_id is not None:
            query = query.where(IncomeExpense.branch_ref == branch_id)
        execution = await self.session.execute(query)
        return execution.all()
