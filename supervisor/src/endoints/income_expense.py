import datetime

from fastapi import APIRouter, Depends
from typing import List

from supervisor.src.repositories.income_expense import IncomeExpenseRepository
from supervisor.src.schemas.income_expense import IncomeExpenseResponse
from supervisor.src.core.auth import require_supervisor
from supervisor.src.core.types import NaiveDatetime

income_expense_router = APIRouter(tags=["Income/Expense details"], prefix="/income-expense",
                                   dependencies=[Depends(require_supervisor)])

# Disabled for now.
# @income_expense_router.get("/all", summary="Get income/expense records")
# async def get_all_income_expense(from_date: NaiveDatetime, to_date: NaiveDatetime, employee_id: str,
#                                   branch_id: str | None = None,
#                                   income_expense_repo: IncomeExpenseRepository = Depends()) -> List[IncomeExpenseResponse]:
#     return await income_expense_repo.get_all(from_date=from_date, to_date=to_date,
#                                               employee_id=bytes.fromhex(employee_id),
#                                               branch_id=bytes.fromhex(branch_id) if branch_id else None)
