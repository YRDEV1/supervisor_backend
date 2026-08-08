# Branches

Database: `tatriw` (1C:Enterprise on PostgreSQL)
Source table: `_reference1054` (Branches / "Филиалы" catalog)

Small, flat catalog (13 rows, no folders/hierarchy). Every employee row in
`_reference1109` links to one of these via `_fld1116rref` (and a duplicate
`_fld4481rref`, likely a separate "salary branch" reference that happens to
match in most observed rows).

Total branches: **13**

| Code | Name | `_idrref` |
|---|---|---|
| 1 | Шерин | `9cf1c32162bcc65e11eeb6b68a66468b` |
| 2 | Салари | `a738005056070e0911f035fe9679e686` |
| 3 | Сагбан | `a738005056070e0911f035fe9f6d7ffd` |
| 4 | Лимонария | `a738005056070e0911f035fea84b5c66` |
| 5 | Зайчик | `a738005056070e0911f035feaf4ea9d2` |
| 6 | Япрок | `a738005056070e0911f035feb88e2cfc` |
| 7 | Добрый | `a738005056070e0911f035feb88e2cfd` |
| 8 | Волида | `a73b005056070e0911f06594e49ed821` |
| 9 | Сагбан Ташкент | `8046cc7bb6606cf611f08a502a89b691` |
| 10 | Bai yun fix (BY) | `8047e4da2ef2491211f0a2b2db071eaa` |
| 11 | YR Express | `b065bc0358aa6a1811f10e491e81e7ad` |
| 12 | Тошкент Хорека | `8050db5938726dd811f13320a022e428` |
| 13 | Titon fix | `8059a3e1875d42a811f149cc0962f318` |

## How this was found

There's no column literally named "branch" — the link was found by taking a
sample employee's `_fld1116rref` value and searching every `_reference*`
table for a matching `_idrref`:

```sql
SELECT _idrref, _description
FROM _reference1054
WHERE _idrref = '\x9cf1c32162bcc65e11eeb6b68a66468b';
```

That's how `_reference1054` was identified as the branch catalog (13 short,
plain names — a good fit, unlike the thousands of rows in the outlet/product
catalogs also named "Шерин"-adjacent).

Caution: `_reference1085` (products/nomenclature) and `_reference1099`
(outlets) both also contain entries with `Шерин` in the name — e.g.
`Шерин Макаронлари` (a product) or outlet names ending in `Шерин`. Those are
*not* the branches catalog; they just happen to share the brand/company name
"Шерин". Confirm you're querying `_reference1054` specifically.

## Filtering agents by branch

To get all agents (`ТП` role) belonging to a given branch, filter
`_reference1109` by role parent **and** by `_fld1116rref` together:

```sql
SELECT _idrref, _code, _description
FROM _reference1109
WHERE _parentidrref = '\xa73a005056070e0911f04f17e018d4c6'  -- ТП role
  AND _fld1116rref  = '\x9cf1c32162bcc65e11eeb6b68a66468b'  -- Шерин branch
```

Tested against the live database: returns **25 agents** for branch "Шерин",
e.g. `Нилуфархон Халикова К`, `Диёрбек Хусанов Ку2`, `Илхомжон Раимжонов Ёз`.

The same pattern works for supervisors — swap the role id for the `СВ` role
(`a73a005056070e0911f050e1332c7fcd`, see `DATA/SUPERVISORS.md`) to get
supervisors assigned to a specific branch instead of agents.

Notes:
- `_fld1116rref` is `bytea` (16 bytes) — bind raw bytes, not a hex string, in
  application code (e.g. `bytes.fromhex(...)` with asyncpg).
- If you only have the branch name, resolve its `_idrref` first:
  `SELECT _idrref FROM _reference1054 WHERE _description = 'Шерин'` — but
  remember `_description` has no default collation (see `DATA/TABLES.md`),
  so exact `=` works fine, just avoid `ORDER BY`/`LIKE` without an explicit
  `COLLATE`.
