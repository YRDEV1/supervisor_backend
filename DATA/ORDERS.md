# Orders

Database: `tatriw` (1C:Enterprise on PostgreSQL)
Source table: `_document4542` (header), tabular part `_document4542_vt4599`
(line items)

This is the main sales/order document — each row is one order placed by an
agent on behalf of a client.

## Header columns (identified)

| Column | Meaning |
|---|---|
| `_idrref` | Order id |
| `_number` | Order number |
| `_date_time` | Order date/time |
| `_posted` | Whether the document is posted/finalized (357,371 of 357,810 are; 439 aren't) |
| `_fld4567_rrref` | The client (`_reference1099._idrref`, composite ref) |
| `_fld4561rref` | Branch (`_reference1054._idrref`) |
| `_fld4564rref` | Agent who placed the order (`_reference1109._idrref`) |
| `_fld4565rref` | A second employee reference (86% match rate) — role not confirmed, possibly a courier/confirmer |
| `_fld4583rref` | A third employee reference (100% match) — role not confirmed, possibly "created by" |
| `_fld4570` | Order total amount (observed values like `2,644,670.05`) |
| `_fld4571` | Observed as `0.0000` in every sampled row — meaning unconfirmed (possibly discount or remaining balance) |

The remaining ~50 header columns (`_fld4572`-`_fld4598`, `_fld5213`-`_fld6250`)
are unidentified — mostly numeric/boolean/timestamp flags typical of a 1C
document's workflow state (approval steps, delivery status, etc.), not
investigated in detail.

## Order status: `_fld4562rref`

This is an **enum-backed field** (`_fld4562rref` → `_enum4544`, a 6-value
1C enumeration), the strongest candidate for order status (e.g.
"Доставлено"/delivered, cancelled, in-progress, etc.):

```sql
SELECT _fld4562rref, count(*) FROM _document4542 GROUP BY _fld4562rref;
```

| Enum value (hex) | Count | Share |
|---|---|---|
| `8f44cc788478ce0d4b526daec28af15e` | 346,849 | 96.9% |
| `846940da2efba8194831883b64104da2` | 9,825 | 2.7% |
| `973121ca98e9ef9f4e1a3ab452d3a640` | 970 | 0.3% |
| `81111539a3f38629445a05ca9ed4f4d6` | 119 | <0.1% |
| `a1a83f16cc3ba6a94656b144475cc684` | 28 | <0.1% |
| `9953a2f7b8bc22984f015192dd1f16fb` | 6 | <0.1% |
| *(null)* | 13 | <0.1% |

**Important limitation**: 1C `_enum*` tables (`_enum4544` here) store only
`_idrref` and `_enumorder` — there is no caption/label column anywhere in
the database. The display text ("Доставлено", "Отменен", etc.) is compiled
into the 1C configurator's metadata, not stored in SQL-accessible form. So
this is as far as pure database inspection can go: the *field* is
identified with high confidence (enum-typed, one dominant "normal" value
plus several rare alternate states — a classic status-field shape), but
**which specific value means "Доставлено" cannot be determined from the
database alone**. If you have access to the 1C configurator, look up
`Перечисления.[name for _enum4544]` and its captions in enum-definition
order (`_enumorder` 0-5 above) to get the exact mapping — the dominant value
(order likely near the middle, ~96.9% share) is the best guess for a
"normal/completed" state, but confirm before relying on it.

A second, unrelated enum-backed field also exists —
`_fld4568rref` → `_enum1261` (only 2 values, 99.7% one value) — but its
near-universal single value looks more like a binary document-type/payment
flag than a multi-stage status, and is a weaker "delivered" candidate than
`_fld4562rref`.

Total: **357,810 orders**, spanning **2025-06-27 to 2026-06-12**. 357,793
(99.996%) resolve to a real client.

## Query: orders joined with client and date

```sql
SELECT d._number AS order_number, d._date_time AS order_time,
       c._code AS client_code, c._description AS client_name
FROM _document4542 d
JOIN _reference1099 c ON c._idrref = d._fld4567_rrref
WHERE d._date_time >= '2026-06-01' AND d._date_time < '2026-06-13'
ORDER BY d._date_time DESC;
```

With branch and agent included (tested against live data — real, coherent
results):

```sql
SELECT d._number, d._date_time,
       c._code AS client_code, c._description AS client_name,
       b._description AS branch,
       e._code AS agent_code, e._description AS agent_name,
       d._fld4570 AS order_total
FROM _document4542 d
JOIN _reference1099 c ON c._idrref = d._fld4567_rrref
JOIN _reference1054 b ON b._idrref = d._fld4561rref
JOIN _reference1109 e ON e._idrref = d._fld4564rref
ORDER BY d._date_time DESC
LIMIT 10;
```

Sample real output:

| Order # | Date/time | Client | Branch | Agent | Total |
|---|---|---|---|---|---|
| 357220 | 2026-06-12 18:19:19 | Хожи Абдулло Олтиарик дехкон бозор Ризк барака файз | Шерин | Эргашева Хилолахон О1 | 2,644,670.05 |
| 357219 | 2026-06-12 18:15:52 | Азизбек ака комбинат Оятиллох | Япрок | Дониёр Собиржонов | 384,000.00 |
| 357218 | 2026-06-12 18:15:05 | Ахроржон Ипотека банк рупараси Ахрор Файз Браво маркет | Волида | Абдухалим ВЛД доставка | 16,000.00 |

## Query: order line items (product, price, quantity)

Tabular part `_document4542_vt4599`, joined on `_document4542_idrref =
_document4542._idrref`. Product catalog is `_reference1085` (seen earlier
while searching for the "Шерин" brand, see `DATA/TABLES.md`).

| Column | Meaning |
|---|---|
| `_fld4604rref` | Product (`_reference1085._idrref`) |
| `_fld4608` | Quantity |
| `_fld4617` (= `_fld4619`) | Line total, sale side (what the client is charged for this line) |
| `_fld4616` (= `_fld4618`) | Line total, cost side (purchase/cost price) — same shape as `_fld4617` but a different amount; likely used for margin reporting, not client-facing price |

Unit price isn't stored directly — divide the sale-side total by quantity:

```sql
SELECT d._number AS order_number, p._description AS product_name,
       vt._fld4608 AS quantity,
       ROUND(vt._fld4617 / NULLIF(vt._fld4608, 0), 2) AS unit_price,
       vt._fld4617 AS line_total
FROM _document4542_vt4599 vt
JOIN _document4542 d ON d._idrref = vt._document4542_idrref
JOIN _reference1085 p ON p._idrref = vt._fld4604rref
WHERE d._idrref = decode('HEX_ORDER_IDRREF', 'hex')  -- replace with a real order idrref, or add your own filter
ORDER BY d._date_time DESC;
```

Tested against live data (order 357220 — its line total, 2,644,670.05,
exactly matches the order header total in the sample table above, confirming
the join and amount field are correct):

| Order # | Product | Quantity | Unit price | Line total |
|---|---|---|---|---|
| 357220 | п/к Таллинская ТИМ | 100 | 26,446.70 | 2,644,670.05 |
| 357219 | Lamm Кондиционер для белья цветочный бриз 2л | 1 | 46,000.00 | 46,000.00 |
| 357219 | Lamm Отбеливатель порошкообразный с пятновыводителем для белого 500мл | 5 | 40,000.00 | 200,000.00 |
| 357217 | Докторская янги (уйча) (кизил) 0,500г | 8 | 26,776.33 | 214,210.66 |

Remaining unmapped tabular-part columns: `_fld4601rref`, `_fld4602rref`,
`_fld4605rref` (likely unit-of-measure/warehouse/batch — not investigated),
`_fld4609`/`_fld5737` (weight-per-unit-shaped values, unconfirmed),
`_fld4610`-`_fld4615`, `_fld4620` (mostly `0.0000` in samples, unconfirmed),
`_fld4621rref`, `_fld4622`/`_fld4623`, `_fld5226`-`_fld5229`, `_fld5481`.

## Query: agent statistics (sales count, revenue, clients)

```sql
SELECT count(*) AS order_count,
       sum(_fld4570) AS total_revenue,
       min(_date_time) AS first_order,
       max(_date_time) AS last_order,
       count(DISTINCT _fld4567_rrref) AS distinct_clients
FROM _document4542
WHERE _fld4564rref = decode('HEX_AGENT_IDRREF', 'hex');  -- replace with the real agent idrref
```

Tested against live data for agent "Нилуфархон Халикова К" (code 121):

| Order count | Total revenue | First order | Last order | Distinct clients |
|---|---|---|---|---|
| 255 | 226,867,541.90 | 2025-06-30 | 2025-07-18 | 69 |

The 69 distinct clients exactly matches her territory-coverage figure from
`DATA/TABLES.md` ("Киргули", 69 outlets) — good cross-check that
`_fld4564rref` really is the right "agent" field.

### Top products sold by an agent

```sql
SELECT p._description AS product, sum(vt._fld4608) AS quantity, sum(vt._fld4617) AS revenue
FROM _document4542_vt4599 vt
JOIN _document4542 d ON d._idrref = vt._document4542_idrref
JOIN _reference1085 p ON p._idrref = vt._fld4604rref
WHERE d._fld4564rref = decode('HEX_AGENT_IDRREF', 'hex')  -- replace with the real agent idrref
GROUP BY p._idrref, p._description
ORDER BY revenue DESC
LIMIT 5;
```

Tested against the same agent — real, coherent results:

| Product | Quantity | Revenue |
|---|---|---|
| п/к Таллинская ТИМ | 1,104.5 | 29,020,898.09 |
| Докторская янги (уйча) (кизил) | 552.17 | 23,250,653.50 |
| Сосиски тигр ТИМ | 279.29 | 15,504,669.16 |
| Докторская янги (уйча) (кизил) 0,500г | 530 | 12,253,656.11 |
| п/к Сервелат 50 (нат) | 178.09 | 11,177,625.36 |

## Relationship to income/expense

This document is almost certainly the source that generates the
corresponding entries in `_accumrg1435` (client income/expense, see
`DATA/CLIENT.md`) — an order creates a debt/payment obligation for the
client. Not yet verified with a direct join (e.g. via `_recorderrref`), but
the field-id proximity and business logic both point that way.

## Caveats

- Client/branch/agent link columns were identified by majority-match
  heuristics (>85% resolve to the expected catalog) against a 2,000-row
  sample, then spot-verified with real joined output above — not confirmed
  against the 1C configurator.
- `_fld4565rref` and `_fld4583rref` clearly hold employees too but their
  exact role (confirmer? creator? courier?) isn't determined — don't assume
  `_fld4564rref` is the only "agent" field without checking your use case.
- Same general caveats as other tables: `_description` collation,
  `bytea` id comparisons — see `DATA/TABLES.md`.
