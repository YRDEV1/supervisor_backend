# Database Table Reference

Database: `tatriw` (1C:Enterprise on PostgreSQL). Table/column names are
opaque 1C internal identifiers (`_reference1109`, `_fld1117`, ...) — there is
no metadata dictionary available in SQL, so everything below was
reverse-engineered from sampled data. See `DATA/SUPERVISORS.md` for the
detailed queries these entries are based on.

| Table              | What it is                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Confidence                                                                                                                                                                             |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_reference1109` | **Employees** catalog. Flat list of staff; also contains 4 special rows (`ТП`, `СВ`, `ДСТ`, `ОХР`) that act as role-group parents — every real employee's `_parentidrref` points at one of these to indicate their role. `_fld1556` ("Б_Токен") holds each employee's app/bot token (16-byte `bytea`) — treat as a credential, see `DATA/QUERY.md`.                                                                                                                                                                                                                                                                                                                                                  | High                                                                                                                                                                                   |
| `_reference1099` | **Outlets / points of sale** catalog. Hierarchical (folder-based); item descriptions are often a shop/location name, sometimes with the servicing agent's name or role code appended (e.g. `"Шохсанам Мирзаева ТП"`). Not the employees table, despite superficially similar-looking name matches. **Stores GPS coordinates**: `_fld4697` = latitude, `_fld4698` = longitude (both `mvarchar` text, not numeric — parse before use). Only 1,129 of 6,760 outlets have it set; unset rows read `''` or `'0.0'`. Also has its own token field, `_fld6009` (16-byte `bytea`, sparsely set — 14 of 6,760 rows; no overlap with employee tokens) — treat as a credential, see `DATA/QUERY.md`. | Medium (outlet catalog); High (GPS columns — values match the Fergana valley region, e.g.`40.410686, 71.745431`)                                                                    |
| `_inforg5071`    | **Visit log register.** Records agent → outlet visit events over time: `_fld5072rref` = the agent's own branch (`_reference1109._fld1116rref`, i.e. `_reference1054._idrref`), `_fld5073rref` = the visiting agent's `_reference1109._idrref`, `_fld5074rref` = the outlet/client visited (`_reference1099._idrref`), `_period` = event timestamp, `_fld5386rref` = visit outcome (`_reference4541._idrref` — check-in/check-out/other outcomes; all-zero = generic ping). A single visit can span multiple rows (check-in, check-out, generic pings), not one row per visit — see `DATA/CLIENT.md` for the check-in/check-out/duration query. This is the source for "which agents does this supervisor see," "which territories does this agent cover" (join outlet → territory), and per-visit check-in/check-out timing.                                                                                                                                                                                                                          | High (verified: 81.4% / 88.0% match rates against known supervisor/agent ids, see SUPERVISORS.md;`_fld5074rref` matched 100% of a 50k-row sample against `_reference1099._idrref`) |
| `_reference4541` | **Visit outcome catalog.** Small, flat — reasons/outcomes logged for a client visit: `Дуконга кирдим` (entered shop/check-in, code 2), `Дукондан чикдим` (exited shop/check-out, code 8), plus `Товар етарли` ("enough stock"), `Карзи бор` ("has debt"), `Кейинги сафар олади` ("will buy next time"), `Магазин ёпик` ("shop closed"), `Пулга кийнайди` ("cash-strapped"), `Бошка махсулотлар бор` ("other products available"). Referenced by `_inforg5071._fld5386rref`. | High (confirmed via `_inforg5071` join, see `DATA/CLIENT.md`) |
| `_inforg1832`    | **Narrow-population client visit/activity log.** `_fld1833_rrref` = client (`_reference1099._idrref`, composite ref), `_fld2097rref` = the acting user (`_reference1109._idrref`), `_period` = event timestamp. Columns `_fld1834rref`/`_fld1968rref`/`_fld1835rref` not yet identified. **Correction**: only 29 distinct employees ever appear here at all, and only 1 of 250 `ТП` agents — the active users are mostly admin/office staff (e.g. "Администратор" alone has 1,353,551 events, clearly system/bulk activity, not one person's field visits). Matched a real UI visit report exactly for one specific user (see `DATA/CLIENT.md`), but **do not use this as a general per-agent visit log** — for that, use `_inforg5071` instead, which has real coverage across 216 of 250 `ТП` agents. | Medium (client/event columns verified; population scope corrected after broader testing) |
| `_reference1054` | **Branches** ("Филиалы") catalog. Small, flat (13 rows, no hierarchy). Every employee in `_reference1109` links to one via `_fld1116rref` (a `_fld4481rref` duplicate is likely a separate "salary branch" reference). Includes e.g. "Шерин" (code 1), "Салари", "Сагбан".                                                                                                                                                                                                                                                                                                                                                                                                                               | High (confirmed by tracing a real employee's`_fld1116rref` to a matching `_idrref`; see `DATA/BRANCH.md`)                                                                        |
| `_reference4540` | **Territories** catalog. Small, flat (45 rows) — geographic/sales-area names like "Водил", "Ёзёвон", "Кувасой №1", "Кувасой №2", plus a few city names (Andijon, Namangan, Tashkent). Every outlet in `_reference1099` links to one via `_fld4696rref`.                                                                                                                                                                                                                                                                                                                                                                                                                                                | High (verified: 6,741 of 6,760 outlets resolve via`_fld4696rref` to a valid `_reference4540` row)                                                                                  |
| `_accumrg1466`   | **Employee income/expense register** (cash movements). `_fld1467rref` = branch, `_fld1468rref` = employee (`_reference1109._idrref`), `_fld1470` = amount, `_recordkind` = `0`/`1` for income/expense (inferred, not confirmed against 1C configurator). Totals variant: `_accumrgt1471`. See `DATA/INCOME_EXPENSE.md`.                                                                                                                                                                                                                                                                                                                                                                                              | High (26,111 of 26,112 rows resolve`_fld1468rref` to a real employee, across 426 distinct employees)                                                                                 |
| `_accumrg1435`   | **Client income/expense register** (cash movements) — the client-level counterpart to `_accumrg1466`. `_fld1436rref` = branch, `_fld1437rref` = client (`_reference1099._idrref`), `_fld1439` = amount, `_recordkind` = `0`/`1` for income/expense (same inferred convention). Data only goes up to 2026-06-12 even though the server's `current_date` is later — anchor any "recent activity" window to `max(_period)`, not `current_date`. See `DATA/CLIENT.md`.                                                                                                                                                                                                                                     | High (736,662 of 736,668 rows resolve`_fld1437rref` to a real client, across 6,240 distinct clients)                                                                                 |
| `_document4542`  | **Orders** (header; tabular part `_document4542_vt4599` has line items). `_fld4567_rrref` = client (`_reference1099._idrref`, composite ref), `_fld4561rref` = branch, `_fld4564rref` = agent who placed the order, `_fld4570` = order total, `_date_time`/`_number` = order date and number, `_fld4562rref` = order status (enum-backed, see below). Likely the source document behind `_accumrg1435` entries. See `DATA/ORDERS.md`. | High (357,793 of 357,810 rows resolve to a real client; branch/agent/client/total spot-checked against real, coherent output) |
| `_reference1085` | **Products** ("Nomenclature") catalog, 4,736 rows, hierarchical. Line items in orders link here via `_document4542_vt4599._fld4604rref`. Has 119 real category headers (root rows with at least one child — `_folder` and naming conventions are unreliable signals here). See `DATA/PRODUCT.md` for the full category list and queries. | High (verified against a live 1C client screenshot — see `DATA/PRODUCT.md`) |

## Role-group nodes inside `_reference1109`

Not separate tables — four specific rows in `_reference1109` itself, used as
pseudo-groups via `_parentidrref`:

| Role        | `_description` | `_idrref`                          | Employees under it |
| ----------- | ---------------- | ------------------------------------ | ------------------ |
| Sales agent | `ТП`         | `a73a005056070e0911f04f17e018d4c6` | 250                |
| Supervisor  | `СВ`         | `a73a005056070e0911f050e1332c7fcd` | 19                 |
| Logistics   | `ДСТ`       | `a73a005056070e0911f050e1a458d35f` | 97                 |
| Security    | `ОХР`       | `a73a005056070e0911f050e240952b2e` | 5                  |

## Getting an agent's territories

There's no direct FK from an employee to a territory, and outlets have no
reliable "assigned agent" column either (`_reference1099._fld2267rref` looked
promising but turned out to match all 6,760 outlets against only 14 distinct
employees — it's some kind of "created/managed by" admin field, not a
per-agent assignment). The only verified path is through the visit register:

```sql
SELECT t._description AS territory,
       count(DISTINCT o._idrref) AS outlet_count,
       count(*) AS visit_count
FROM "_inforg5071" v
JOIN _reference1099 o ON o._idrref = v._fld5074rref
JOIN _reference4540 t ON t._idrref = o._fld4696rref
WHERE v._fld5073rref = '\xHEX'  -- agent's _reference1109._idrref
GROUP BY t._idrref, t._description;
```

Tested against a real `ТП` agent ("Нилуфархон Халикова К", code 121): returned
"Киргули" (69 outlets, 254 visits) as her territory, plus one stray outlet
filed under "Тугатилганлар" ("discontinued" — a catch-all bucket for
closed/inactive outlets, not a real geographic area). In general expect one
dominant territory per agent, with the "Тугатилганлар" bucket as noise to
filter out if needed.

## Unconfirmed candidates (not yet verified)

Seen during search but not confirmed to be meaningfully linked — worth
checking before relying on them:

- `_inforg1832`, `_inforg5060`, `_inforgsf5082`, `_inforgsl5081` — each had at
  least one `bytea` column with partial hits against both supervisor and
  agent ids, similar to `_inforg5071`. Could be related registers (e.g.
  sales/order documents referencing the visiting agent), but match rates
  were lower/unchecked and column semantics weren't inspected.
- `_document6024` — a large, multi-purpose document (~90 columns; looks like
  orders/deliveries) that also carries `_fld6252`/`_fld6253` (lat/lon text,
  same format as `_reference1099`). Likely captures the GPS location at the
  time the document was created (e.g. an agent's location when placing an
  order), but only sparsely populated (empty in most sampled rows) and not
  otherwise investigated.

## General caveats (apply to all tables above)

- Text columns (e.g. `_description`) are `USER-DEFINED` (`mvarchar`) with no
  default collation — `ORDER BY`/`LIKE` on them can throw
  `IndeterminateCollationError`; sort/filter in application code instead.
- UUID-like columns (`_idrref`, `_parentidrref`, any `*rref` column) are raw
  `bytea` (16 bytes), not native `uuid` — compare as bytea literals
  (`'\xHEX'::bytea`) or bind raw `bytes` from your driver.
- `_marked = true` means "flagged for deletion", not "inactive" in the
  business sense, though it's often a reasonable proxy for that.
- `_enumNNN` tables (33 in this database) hold only `_idrref` and
  `_enumorder` — no caption/label text anywhere in the database. Any
  `*rref` column whose values resolve into one of these tables is an
  enum-typed status/flag field, but its human-readable meaning (e.g.
  "Доставлено") can only be confirmed via the 1C configurator, not SQL. See
  `DATA/ORDERS.md` for a worked example (`_document4542._fld4562rref`).
