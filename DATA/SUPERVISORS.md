* [ ] 

# Supervisors (role "СВ")

Database: `tatriw` (1C:Enterprise on PostgreSQL)
Source table: `_reference1109` (Employees catalog)
Role group node: `_description = 'СВ'`, `_idrref = a73a005056070e0911f050e1332c7fcd`

Employees are stored as flat items in `_reference1109`. Role isn't a separate
column — instead there are four "role" rows in the same table (`ТП`, `СВ`,
`ДСТ`, `ОХР`) that act as parent nodes, and each employee's `_parentidrref`
points to the row matching their role. So "supervisors" = rows whose
`_parentidrref` equals the `СВ` row's `_idrref`.

Total found: **19**

| Code | Name                                    | Phone         | Active                   | Hire date  |
| ---- | --------------------------------------- | ------------- | ------------------------ | ---------- |
| 11   | Абдуллох Улмасов         | +998990027900 | Yes                      | 1993-08-06 |
| 239  | Аброрбек СВ                   | 998624624     | No (marked for deletion) | —         |
| 98   | Азизбек Добрий             | 94 498 00 89  | Yes                      | 1984-03-21 |
| 240  | Акмалжон СВ                   | 771147471     | No (marked for deletion) | —         |
| 23   | Зухра СуперВайзер       | 908442848     | No (marked for deletion) | —         |
| 86   | Лилияхон СВ                   | 886667161     | No (marked for deletion) | —         |
| 507  | Мадинахон СВ                 | 911198900     | Yes                      | —         |
| 360  | Мадинахон СВР               | +998911198900 | Yes                      | —         |
| 120  | Махкамов Отаёр СВ        | 937328882     | Yes                      | —         |
| 267  | Мухаммад Расул             | +998902771449 | Yes                      | 1992-06-13 |
| 174  | МухаммадРасул СВ         | +998902771449 | No (marked for deletion) | —         |
| 6    | Мухаммадсодик ЛМ         | 911069070     | No (marked for deletion) | 2003-12-18 |
| 33   | Муштарийхон СВ             | +998936838600 | No (marked for deletion) | —         |
| 111  | Насибахон Алиева СВ    | 908365551     | Yes                      | —         |
| 285  | Носирбек                        | +998985760907 | Yes                      | —         |
| 289  | Саидганиев Саидислом | 935599933     | Yes                      | —         |
| 57   | Шохрухбек                      | +998950757002 | Yes                      | —         |
| 191  | Эргашев СВ                     | +998911069070 | No (marked for deletion) | —         |
| 208  | умидахон                        | (none)        | No (marked for deletion) | —         |

Notes:

- "Active" = `_marked = false` (1C uses `_marked = true` to flag a record as marked for deletion, not yet purged).
- `_idrref` (the internal UUID for each row) was fetched but omitted from the table above for readability; see the query below to retrieve it.
- Several names carry `СВ`/`СВР`/`СуперВайзер` suffixes as a human-readable hint, but the *authoritative* signal is the `_parentidrref` link, not the text of the name.

## How to write this query yourself

1. **Find the role catalog.** Role labels aren't a lookup table of their own —
   they're rows inside the employees catalog (`_reference1109`) with
   `_folder = false` and no parent, used as pseudo-groups. Find them by
   description:

   ```sql
   SELECT _idrref, _description
   FROM _reference1109
   WHERE _description IN ('ТП', 'СВ', 'ДСТ', 'ОХР');
   ```
2. **Get the target role's `_idrref`** (e.g. the row where `_description = 'СВ'`) from that result, in hex/bytea form.
3. **Select employees whose `_parentidrref` matches that id:**

   ```sql
   SELECT _idrref, _code, _description, _marked, _fld1117 AS phone, _fld2216 AS hire_date
   FROM _reference1109
   WHERE _parentidrref = '\xa73a005056070e0911f050e1332c7fcd';
   ```
4. **Caveats specific to this database (1C:Enterprise on Postgres):**

   - Text columns (`_description`, etc.) have a `USER-DEFINED` type with no
     default collation, so `ORDER BY` / `LIKE` on them can throw
     `IndeterminateCollationError` — sort/filter in application code instead,
     or add `COLLATE "default"` explicitly.
   - UUID-like columns (`_idrref`, `_parentidrref`, `*rref` columns) are raw
     `bytea` (16 bytes), not native `uuid`. Compare them as bytea literals
     (`'\xHEX'::bytea`) or bind bytes from your driver.
   - `_marked = true` means "flagged for deletion", not "inactive employee" in
     the business sense, but in practice it's a reasonable proxy for
     inactive/removed staff.

## Getting a single supervisor's details

Once you have a supervisor from the table above, you can look up their full
row two ways: by internal id (`_idrref`) or by their catalog `_code`.

**By `_idrref`** (the 16-byte internal UUID, shown in hex — e.g. the id for
"Мадинахон СВ" is `b077f22363d4fde911f16024a884ca8a`):

```sql
SELECT _idrref, _code, _description, _marked, _parentidrref,
       _fld1117 AS phone, _fld2216 AS hire_date,
       _fld2503 AS shift_start, _fld2504 AS shift_end
FROM _reference1109
WHERE _idrref = '\xb077f22363d4fde911f16024a884ca8a';
```

**By `_code`** (the short numeric catalog code, e.g. `507` for "Мадинахон СВ"
— note `_code` is `numeric`, and 1C often zero-pads/right-aligns it, so cast
or compare numerically rather than as text):

```sql
SELECT _idrref, _code, _description, _marked, _parentidrref,
       _fld1117 AS phone, _fld2216 AS hire_date,
       _fld2503 AS shift_start, _fld2504 AS shift_end
FROM _reference1109
WHERE _code = 507;
```

With asyncpg, pass the id as raw `bytes` (not a hex string) since the column
is `bytea`:

```python
row = await conn.fetchrow(
    "SELECT * FROM _reference1109 WHERE _idrref = $1",
    bytes.fromhex("b077f22363d4fde911f16024a884ca8a"),
)
```

Tip: to confirm a looked-up row is actually a supervisor (and not, say, a
`ТП` employee with a code collision across roles), also check that its
`_parentidrref` equals the `СВ` role id
(`a73a005056070e0911f050e1332c7fcd`).

## Getting a supervisor's agents

"Each supervisor can see its agents" isn't a static column on
`_reference1109` — there's no field on an employee row that names their
supervisor. Instead, the relationship is recorded as **visit events** in
`_inforg5071`, a register that logs each time a supervisor visits an agent
(likely a field-visit/audit log feeding this dashboard):

- `_fld5072rref` — the **visiting supervisor's individual reference**
  (`_reference1109._fld1116rref`, *not* the supervisor's own `_idrref`)
- `_fld5073rref` — the **visited agent's `_idrref`** (a row under the `ТП`
  role)
- `_period` — timestamp of the visit

This was verified against live data: across 356,969 rows in `_inforg5071`,
81.4% of `_fld5072rref` values match a known supervisor's `_fld1116rref`, and
88.0% of `_fld5073rref` values match a known `ТП` agent's `_idrref` — strong
enough correlation to treat this as the real assignment/visit link (the
remainder are most likely visits by roles other than `ТП`/`СВ`, or by
inactive/deleted staff).

So an agent "belongs to" a supervisor in the sense of "has been visited by"
that supervisor. To list the distinct agents a given supervisor currently
sees, join through the individual reference and take the latest visit per
agent:

```sql
SELECT DISTINCT ON (agent._idrref)
    agent._idrref       AS agent_id,
    agent._code         AS agent_code,
    agent._description  AS agent_name,
    visits._period      AS last_visit_at
FROM "_inforg5071" AS visits
JOIN _reference1109 AS supervisor
    ON supervisor._fld1116rref = visits._fld5072rref
JOIN _reference1109 AS agent
    ON agent._idrref = visits._fld5073rref
WHERE supervisor._idrref = '\xb077f22363d4fde911f16024a884ca8a'  -- Мадинахон СВ
ORDER BY agent._idrref, visits._period DESC;
```

Tested against "Мадинахон СВ" (`_idrref = b077f22363d4fde911f16024a884ca8a`):
returned 26 distinct agents with recent visit timestamps (through mid-2026),
e.g. `Умидахон О2`, `Сарвинозхон Ф1`, `Ёкутхон Т`, `Асадулло Ку12`.

Notes:

- No `ORDER BY`/`WHERE` is applied directly to `_description` here, so the
  `USER-DEFINED` collation issue from earlier doesn't come up — the join and
  filter keys are all `bytea`.
- Swap `DISTINCT ON (agent._idrref) ... ORDER BY agent._idrref, visits._period DESC`
  for a plain `WHERE visits._period > now() - interval '30 days'` (no
  `DISTINCT ON`) if you want a visit history instead of a current-roster
  snapshot.
- If a supervisor has multiple `_fld1116rref`-linked individual records over
  time (e.g. re-hired under a new employee row), this query only matches
  visits tied to the specific employee row you passed in — check for other
  `_reference1109` rows sharing the same `_fld1116rref` if the agent count
  looks too low.
