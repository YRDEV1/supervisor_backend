# Clients & Territories

Database: `tatriw` (1C:Enterprise on PostgreSQL)

- **Clients table**: `_reference1099` — this is the same "Outlets / points of
  sale" catalog documented in `DATA/TABLES.md`. In this business (a
  distribution company), a client *is* a retail point/outlet, so there's no
  separate "Clients" catalog — `_reference1099` serves both roles.
- **Territory table**: `_reference4540` — see `DATA/TABLES.md` for details
  (45 rows, plain geographic names like "Водил", "Ёзёвон", "Кувасой №1"/"№2").

## Query: get a client by their ID

```sql
SELECT _idrref, _code, _description
FROM _reference1099
WHERE _idrref = decode('HEX_IDRREF_HERE', 'hex');  -- replace with the real client idrref
```

## The link

Every client links to a territory via `_fld4696rref`:

```sql
_reference1099._fld4696rref  ->  _reference4540._idrref
```

Coverage: 6,741 of 6,760 clients (99.7%) resolve to a valid territory.

## Query: agent's visit history to clients

An agent's history of visits to clients — who they saw, when — comes from
`_inforg5071` (see `DATA/TABLES.md`), not from `_reference1099` directly.
`_fld5073rref` = the visiting agent, `_fld5074rref` = the client visited,
`_period` = visit timestamp. Filter by both agent and a date range:

```sql
SELECT o._code AS client_code, o._description AS client_name, v._period AS visit_time
FROM "_inforg5071" v
JOIN _reference1099 o ON o._idrref = v._fld5074rref
WHERE v._fld5073rref = decode('HEX_AGENT_IDRREF', 'hex')  -- replace with the real agent idrref
  AND v._period >= '2026-05-22' AND v._period < '2026-05-23'  -- adjust date range as needed
ORDER BY v._period;
```

Tested against live data for agent "Сарварбек Кува" (code 460) on
2026-05-22: returned 11 real visits with client names and timestamps,
matching the shape of a daily visit report (branch → employee → day →
client list with visit time).

**Correction from an earlier version of this doc**: `_inforg5071` *can* have
multiple rows per visit, not just one — `_fld5386rref` references
`_reference4541`, a small "visit outcome" catalog (`Дуконга кирдим` =
entered shop/check-in, `Дукондан чикдим` = exited shop/check-out, plus other
outcomes like `Товар етарли` = "enough stock", `Карзи бор` = "has debt",
`Магазин ёпик` = "shop closed", etc). Rows with `_fld5386rref` all-zero are
generic pings, not tied to a specific outcome.

## Query: agent's check-in/check-out per client visit

Reproduces a report shaped like: client, check-in time, check-out time,
request time, duration in minutes.

```sql
SELECT c._code AS client_code, c._description AS client_name,
       min(v._period) FILTER (WHERE v._fld5386rref = decode('a738005056070e0911f04071d0141858', 'hex')) AS check_in,
       max(v._period) FILTER (WHERE v._fld5386rref = decode('b512f0d4155608d711f08a4607a91bfb', 'hex')) AS check_out,
       max(v._period) AS request_time
FROM _inforg5071 v
JOIN _reference1099 c ON c._idrref = v._fld5074rref
WHERE v._fld5073rref = decode('HEX_AGENT_IDRREF', 'hex')  -- replace with the real agent idrref
  AND v._fld5072rref = decode('HEX_BRANCH_IDRREF', 'hex')  -- replace with the real branch idrref (agent's own branch)
  AND v._period >= '2026-06-04' AND v._period < '2026-06-05'  -- adjust date range
GROUP BY c._idrref, c._code, c._description
ORDER BY check_in;
```

The two `decode(...)` values in the `FILTER` clauses are fixed —
`a738005056070e0911f04071d0141858` = "Дуконга кирдим" (check-in) and
`b512f0d4155608d711f08a4607a91bfb` = "Дукондан чикдим" (check-out), both
rows in `_reference4541`. Compute duration in minutes in application code as
`(check_out - check_in)` (or `EXTRACT(EPOCH FROM (check_out - check_in)) /
60` in SQL).

Tested against live data for agent "Сарварбек" (code 148), branch Шерин, on
2026-06-04, client "Test " (code 6533): `check_in = 2026-06-04 18:17:14`,
`check_out = 2026-06-04 18:20:23`, `request_time = 2026-06-04 18:21:27`,
duration = **3.150 minutes** — an exact match to a real report row.

## Query: agent inactive/idle time on a given date

Uses `_inforg5071` (the visit register, see `DATA/TABLES.md`) — gaps
between consecutive visit events for an agent on a given day. Any gap over a
chosen threshold (10 minutes below) counts as an idle period:

```sql
WITH events AS (
    SELECT _period,
           LAG(_period) OVER (ORDER BY _period) AS prev_period
    FROM _inforg5071
    WHERE _fld5073rref = decode('HEX_AGENT_IDRREF', 'hex')  -- replace with the real agent idrref
      AND _period >= '2026-05-22' AND _period < '2026-05-23'  -- the date to check
)
SELECT prev_period AS idle_start, _period AS idle_end,
       _period - prev_period AS idle_duration
FROM events
WHERE _period - prev_period > interval '10 minutes'
ORDER BY idle_start;
```

**Use `_inforg5071`, not `_inforg1832`, for this.** An earlier version of
this doc used `_inforg1832`, which looked right for one specific user but
turned out to be a narrow-population log (only 29 employees ever appear in
it, mostly admin/office staff — see the corrected `DATA/TABLES.md` entry).
`_inforg5071` has real coverage across 216 of 250 `ТП` agents and is the
right source for a general "any agent, any date" idle-time query.

Tested with a 10-minute threshold against 5 **randomly selected** `ТП`
agents, each on a random date they had activity:

| Agent | Date | Events | Idle periods | Total idle |
|---|---|---|---|---|
| Темур Кувасой (351) | 2025-12-24 | 15 | 12 | 7:37:29 |
| Ёкутхон Т (82) | 2025-10-23 | 14 | 11 | 6:33:01 |
| Махмудхон ВЛД Олтиарик (385) | 2026-03-19 | 17 | 14 | 4:51:19 |
| Хуснидахон К 1 (447) | 2026-03-26 | 16 | 8 | 2:59:32 |
| Мухайо маргилон (222) | 2025-08-02 | 2 | 1 | 0:54:06 |

Example detail (Ёкутхон Т, 2025-10-23) — includes what looks like a lunch
break:

| Idle start | Idle end | Duration |
|---|---|---|
| 10:32:21 | 10:46:16 | 0:13:55 |
| 10:46:16 | 11:03:07 | 0:16:51 |
| 11:03:07 | 11:19:58 | 0:16:51 |
| 11:19:58 | 13:44:26 | 2:24:28 |
| 13:51:38 | 14:06:21 | 0:14:43 |
| 14:06:21 | 14:36:19 | 0:29:58 |

At a 10-minute threshold, nearly every gap between visits counts as "idle"
(agents visit clients roughly every 10-30 minutes when active) — this
threshold surfaces travel time between stops, not just meal breaks. Raise
it (e.g. to 30-60 minutes) if you only want to flag unusually long gaps.

Notes:
- This measures gaps **between logged visit events**, not true "off work"
  time — an agent could be actively traveling/working without a visit event
  firing. It's the best available proxy from this table, not a GPS-verified
  idle detector.
- To also flag time **before the first visit** or **after the last visit**
  relative to expected shift hours, cross-reference
  `_reference1109.default_shift_start`/`default_shift_end` (`_fld2503`/
  `_fld2504`, see the `Employee` model) rather than assuming a fixed workday.
- Not every `ТП` agent has `_inforg5071` activity (216 of 250 do) — check
  for that before assuming a silent/empty result means "fully idle" rather
  than "this agent doesn't use this feature at all."

## Query: clients by territory

```sql
SELECT o._idrref, o._code, o._description AS client_name, t._description AS territory
FROM _reference1099 o
JOIN _reference4540 t ON t._idrref = o._fld4696rref
WHERE t._description = 'Водил'
ORDER BY o._code;
```

To get a client-count summary across all territories instead of one:

```sql
SELECT t._description AS territory, count(*) AS client_count
FROM _reference1099 o
JOIN _reference4540 t ON t._idrref = o._fld4696rref
GROUP BY t._idrref, t._description
ORDER BY client_count DESC;
```

Tested against live data — top territories by client count:

| Territory                   | Clients |
| --------------------------- | ------- |
| Тугатилганлар* | 772     |
| Тошлок                | 393     |
| Ёзёвон                | 390     |
| Маргилон №1        | 360     |
| Олтиарик №1        | 321     |
| Кува №2                | 254     |
| Кувасой №2          | 252     |
| Фаргона №2          | 242     |
| Фаргона №1          | 235     |
| Бозор                  | 234     |

\* "Тугатилганлар" means "discontinued" — a catch-all bucket for
closed/inactive clients, not a real geographic territory. Filter it out
(`WHERE t._description != 'Тугатилганлар'`) if you only want active
territories.

## Getting clients only (excluding noise)

The raw `_reference1099` catalog (6,760 rows) mixes in records that aren't
real, active clients:

- **267 rows** have `_marked = true` (flagged for deletion)
- **772 rows** sit in the "Тугатилганлар" ("discontinued") territory —
  a catch-all bucket, not a real geographic area (25 of these overlap with
  the marked-for-deletion set above)
- **1 row** (code 6212, "Хорека") has `_folder = false`, unlike every other
  row in the table (`_folder = true`) — a data quirk, not meaningful for
  filtering; leave it as-is

Filtering out the first two gives the real, active client list:

```sql
SELECT o._idrref, o._code, o._description AS client_name, t._description AS territory
FROM _reference1099 o
JOIN _reference4540 t ON t._idrref = o._fld4696rref
WHERE o._marked = false
  AND t._description != 'Тугатилганлар'
ORDER BY o._code;
```

Tested against live data: **5,731 active clients** (out of 6,760 total rows
in the raw catalog).

## Query: clients by agent

`_reference1099._fld2267rref` holds the assigned agent's id
(`_reference1109._idrref`).

```sql
SELECT o._idrref, o._code, o._description AS client_name
FROM _reference1099 o
WHERE o._fld2267rref = decode('HEX_AGENT_IDRREF', 'hex')  -- replace with the real agent idrref
ORDER BY o._code;
```

To get a client-count summary per agent instead of one agent's list:

```sql
SELECT e._code AS agent_code, e._description AS agent_name, count(*) AS client_count
FROM _reference1099 o
JOIN _reference1109 e ON e._idrref = o._fld2267rref
GROUP BY e._idrref, e._code, e._description
ORDER BY client_count DESC;
```

**Worth knowing before relying on this**: run against live data, this field
resolves to only 14 distinct employees across all 6,760 clients, and the
names/counts it returns (e.g. "Администратор" with 97 clients, "Жамшид офис"
with 392, several people with 500-2,700+ clients each) look like
admin/office staff rather than individual field agents — a single `ТП`
agent typically covers on the order of dozens to ~100 outlets (see the
territory-based agent coverage in `DATA/TABLES.md`'s "Getting an agent's
territories" section), not thousands. So this column may reflect something
like "who entered/manages this record in the system" rather than "which
agent currently serves this client" — worth double-checking against the 1C
configurator's actual field label before treating it as ground truth for
agent assignment.

## Client income/expense: `_accumrg1435`

Same shape as the employee register (`_accumrg1466`, see
`DATA/INCOME_EXPENSE.md`), but keyed on the client instead:

| Column | Meaning |
|---|---|
| `_period` | Timestamp of the transaction |
| `_recordkind` | `0` = income, `1` = expense (same inferred convention as the employee register) |
| `_fld1436rref` | Branch |
| `_fld1437rref` | The client (`_reference1099._idrref`) |
| `_fld1438rref` | Constant across rows — likely currency |
| `_fld1439` | Amount |

Verified: 736,662 of 736,668 rows (99.999%) resolve `_fld1437rref` to a real
client, across 6,240 distinct clients.

### Example: "Шухратжон акаТошлок Дарё" (code 549)

```sql
SELECT _recordkind, sum(_fld1439) AS total, count(*) AS n
FROM _accumrg1435
WHERE _fld1437rref = decode('a739005056070e0911f04cede630efc0', 'hex')
GROUP BY _recordkind;
```

| Type | Total | Count |
|---|---|---|
| Income | 57,469,230.39 | 73 |
| Expense | 62,934,653.24 | 67 |

Most recent transactions run from 2025-06-24 up to 2026-06-11 (this client's
last movement), e.g.:

| Date/time | Type | Amount |
|---|---|---|
| 2026-06-11 09:17:55 | Income | 23,000 |
| 2026-06-11 09:17:35 | Expense | 23,000 |
| 2026-06-10 08:55:32 | Income | 79,000 |
| 2026-06-10 08:55:08 | Expense | 79,000 |
| 2026-06-09 07:03:30 | Income | 24,000 |

## Query: clients not visited on a specific date

"Not logged in" here means not visited (no `_inforg5071` visit event) —
clients don't log in themselves; the agent's visit is what gets recorded.
Uses `NOT EXISTS` against the same visit register used for agent visit
history above:

```sql
SELECT o._idrref, o._code, o._description AS client_name
FROM _reference1099 o
JOIN _reference4540 t ON t._idrref = o._fld4696rref
WHERE o._marked = false AND t._description != 'Тугатилганлар'
  AND NOT EXISTS (
      SELECT 1 FROM _inforg5071 v
      WHERE v._fld5074rref = o._idrref
        AND v._period >= '2026-05-22' AND v._period < '2026-05-23'  -- the date to check
  );
```

Tested against live data for 2026-05-22: **4,696 of 5,731** active clients
(see "Getting clients only" above) had no visit that day — expected, since
agents rotate through their territory over multiple days rather than
visiting every client daily.

### Scoping to a supervisor's agents (not a direct agent/supervisor id filter)

To scope this to "clients not visited by any of a given supervisor's
agents" — **don't filter `_inforg5071` by the supervisor's id directly**
(a supervisor never appears in `_fld5073rref`, only their agents do). Resolve
the supervisor's agents first (same pattern as `DATA/SUPERVISORS.md`'s
"Getting a supervisor's agents"), then filter by that agent set:

```sql
WITH supervisor_agents AS (
    SELECT DISTINCT v._fld5073rref AS agent_id
    FROM _inforg5071 v
    JOIN _reference1109 s ON s._fld1116rref = v._fld5072rref
    WHERE s._idrref = decode('HEX_SUPERVISOR_IDRREF', 'hex')  -- replace with the real supervisor idrref
)
SELECT o._idrref, o._code, o._description AS client_name
FROM _reference1099 o
JOIN _reference4540 t ON t._idrref = o._fld4696rref
WHERE o._marked = false AND t._description != 'Тугатилганлар'
  AND NOT EXISTS (
      SELECT 1 FROM _inforg5071 v
      WHERE v._fld5074rref = o._idrref
        AND v._fld5073rref IN (SELECT agent_id FROM supervisor_agents)
        AND v._period >= '2026-05-22' AND v._period < '2026-05-23'  -- the date to check
  )
  AND EXISTS (
      SELECT 1 FROM _inforg5071 v
      WHERE v._fld5074rref = o._idrref
        AND v._fld5073rref IN (SELECT agent_id FROM supervisor_agents)
  );  -- only consider clients this supervisor's agents actually cover
```

The trailing `EXISTS` limits results to clients within this supervisor's
agents' territories at all (otherwise every unrelated client in the
database — never covered by these agents in the first place — would also
show up as "not visited").

Tested against live data for supervisor "Мадинахон СВ" on 2026-05-22:
**2,123** of her agents' clients weren't visited that day, e.g.:

| Code | Client |
|---|---|
| 730 | Акбарали Хамза 20-21 мактабдан отиб |
| 5120 | Маматкулов Икболжон Хокимят рупараси Ун Маркази |
| 204 | Илхом ака Мухайё Чораха* Рухшона |
| 1187 | Рахматилло Маргилон ЦУМ |
| 1512 | Кобилжон Варзак центр бренд шоп ёни Кола маркет |

## Active clients by recent sales activity

A different notion of "active" than `_marked`: a client counts as **active**
if they have any `_accumrg1435` transaction (income or expense — treated
here as a proxy for "sales activity") within the last 10 days; otherwise
they're **inactive**, but still a client (don't exclude them from the list).

```sql
SELECT o._idrref, o._code, o._description AS client_name,
       CASE WHEN EXISTS (
           SELECT 1 FROM _accumrg1435 a
           WHERE a._fld1437rref = o._idrref
             AND a._period >= current_date - interval '10 days'
       ) THEN 'active' ELSE 'inactive' END AS status
FROM _reference1099 o
JOIN _reference4540 t ON t._idrref = o._fld4696rref
WHERE o._marked = false AND t._description != 'Тугатилганлар';
```

This is the query to use as-is against a real/live database — `current_date`
is correct there since new transactions keep landing every day.

Note: this is a correlated `EXISTS` per client against a 736k-row table and
is noticeably slow (multiple seconds) without an index on
`_accumrg1435._fld1437rref` — consider adding one if this becomes a
recurring query, or precompute it as a materialized view.

**Heads up for this specific snapshot/test copy of `tatriw`:** its data
happens to stop at **2026-06-12**, while this copy's `current_date` reads
**2026-07-07** (~25 days later) — so running the query above against *this*
particular snapshot returns 0 active / 5,731 inactive, since every
transaction is already outside a literal 10-day window from its "today". That's
a property of this stale snapshot, not a problem with the query itself. If
you ever need to sanity-check results against a snapshot like this one,
anchor to the data's own latest date instead:

```sql
WITH anchor AS (SELECT max(_period) AS d FROM _accumrg1435)
SELECT o._idrref, o._code, o._description AS client_name,
       CASE WHEN EXISTS (
           SELECT 1 FROM _accumrg1435 a
           WHERE a._fld1437rref = o._idrref
             AND a._period >= (SELECT d FROM anchor) - interval '10 days'
       ) THEN 'active' ELSE 'inactive' END AS status
FROM _reference1099 o
JOIN _reference4540 t ON t._idrref = o._fld4696rref
WHERE o._marked = false AND t._description != 'Тугатилганлар';
```

Tested against this snapshot with that anchored window: 3,328 active / 2,403
inactive, and "Шухратжон акаТошлок Дарё" (code 549) comes out active — her
last transaction (2026-06-11) falls within 10 days of the data's max date
(2026-06-12).

## Caveats

- `_description` is `USER-DEFINED` (`mvarchar`) with no default collation —
  equality (`=`) works fine, but avoid `ORDER BY`/`LIKE` on it directly (see
  `DATA/TABLES.md`).
- 19 clients (0.3%) have no valid territory link (`_fld4696rref` doesn't
  resolve) — use a `LEFT JOIN` instead of `JOIN` if you need to include them.
- `_folder` is `true` for essentially the whole table (only 1 exception) —
  unlike `_reference1109` (Employees), it does **not** distinguish
  group/category nodes from real client records here, so don't filter on it.
- The income/expense `_recordkind` labels (0=income, 1=expense) are inferred
  from convention, not confirmed against the 1C configurator — same caveat
  as `DATA/INCOME_EXPENSE.md`.
