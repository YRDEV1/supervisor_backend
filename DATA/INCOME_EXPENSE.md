# Employee Income / Expense (Cash Movements)

Database: `tatriw` (1C:Enterprise on PostgreSQL)
Source table: `_accumrg1466` (accumulation register; totals variant: `_accumrgt1471`)

## Table structure

| Column | Meaning |
|---|---|
| `_period` | Timestamp of the transaction |
| `_recordertref` / `_recorderrref` | Type + id of the document that generated this movement |
| `_lineno` | Line number within that document |
| `_active` | Whether the record counts toward totals |
| `_recordkind` | `0` = income/receipt ("Приход"), `1` = expense/disbursement ("Расход") — inferred from standard 1C convention and observed pattern (one large receipt followed by many smaller disbursements), not confirmed against the 1C configurator |
| `_fld1467rref` | Branch (`_reference1054._idrref`) |
| `_fld1468rref` | Counterparty — the employee (`_reference1109._idrref`) in the overwhelming majority of rows |
| `_fld1469rref` | Constant across every row observed; likely a currency reference (single-currency company) |
| `_fld1470` | Amount |

## How this was found

`_fld1468rref` was flagged during a broader "which tables reference this
employee id" scan (see `DATA/TABLES.md`). Verifying at the whole-table level
(not tied to any one person) confirmed it's a general employee register, not
a coincidental hit:

```sql
-- of 26,112 total rows, 26,111 have _fld1468rref matching a real employee,
-- spanning 426 distinct employees
SELECT count(*) FROM _accumrg1466;
```

## Query: an employee's income/expense in a date range

```sql
SELECT _period, _recordkind, _fld1470 AS amount
FROM _accumrg1466
WHERE _fld1468rref = '\xHEX'  -- employee's _reference1109._idrref
  AND _period >= '2026-03-01' AND _period < '2026-04-01'
ORDER BY _period;
```

## Example: "Равшанбек IT" (code 298), 2026-03-01 to 2026-04-01

Employee lookup:

```sql
SELECT _idrref, _code, _description FROM _reference1109 WHERE _description = 'Равшанбек IT';
-- code=298, _idrref=b514f0d4155608d411f09f9e87361888
```

Result (7 rows):

| Date/time | Type | Amount |
|---|---|---|
| 2026-03-01 19:17:41 | Income | 5,500,000 |
| 2026-03-02 15:39:19 | Expense | 11,500 |
| 2026-03-03 12:09:57 | Expense | 14,000 |
| 2026-03-04 14:11:21 | Expense | 125,000 |
| 2026-03-06 17:21:11 | Expense | 5,089,000 |
| 2026-03-11 09:27:24 | Expense | 40,000 |
| 2026-03-18 13:02:47 | Expense | 39,000 |

**Totals**: Income = 5,500,000 · Expense = 5,318,500 · Net = +181,500

Note: the income/expense *labels* (which `_recordkind` value means which) are
a reasonable inference, not a verified fact — the raw amounts, dates, and
document links are directly from the register.
