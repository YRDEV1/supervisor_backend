# Ad-hoc Queries

Scratch log for one-off queries run against `tatriw` while exploring the
schema. See `DATA/TABLES.md` for the data-dictionary summary these feed into.

## Employee's token

`_reference1109._fld1556` ("Б_Токен") holds each employee's app/bot token as
a 16-byte `bytea` value. Treat it as a credential — don't log or display the
actual value.

`'\xHEX'` bytea literals depend on client/encoding settings and can fail in
some SQL tools with an "invalid byte sequence for encoding UTF8" error even
for a perfectly valid hex string (seen with pgAdmin/psql clients whose
session isn't treating it as a bytea literal). Use `decode(<hex>, 'hex')`
instead — it takes the hex digits as plain text input, so there's no
literal-encoding ambiguity.

Step 1 — look up the employee's `_idrref` by name:

```sql
SELECT _idrref, _code, _description
FROM _reference1109
WHERE _description = 'Employee Full Name';
```

Step 2 — use that `_idrref` (as a plain hex string, no `\x` prefix, no
quotes-inside-quotes) to fetch the token. `_fld1556` is raw `bytea`, so wrap
it in `encode(..., 'hex')` to get a human-readable hex string instead of a
raw/garbled byte dump:

```sql
SELECT _idrref, _code, encode(_fld1556, 'hex') AS token
FROM _reference1109
WHERE _idrref = decode('b514f0d4155608d411f09f9e87361888', 'hex');  -- replace with the real idrref from step 1
```

## Another token field: outlets

`_reference1099._fld6009` (Outlets catalog) is a second, separate token
field — same shape as the employee token (16-byte `bytea`), but sparsely
populated (only 14 of 6,760 outlets have it set) and doesn't overlap with
any employee token value, so it's its own distinct token space (likely a
POS-device or web-order auth token tied to specific outlets, not confirmed
against the 1C configurator). Same rules apply: treat as a credential, use
`decode(...)`/`encode(...)` rather than raw `\x` literals.

Step 1 — find which outlets actually have a token set (only 14 do), by name
or just to get a real `_idrref` to work with:

```sql
SELECT _idrref, _code, _description
FROM _reference1099
WHERE _fld6009 IS NOT NULL AND _fld6009 != decode('00000000000000000000000000000000', 'hex');
```

Step 2 — use that `_idrref` to fetch the token itself:

```sql
SELECT _idrref, _code, encode(_fld6009, 'hex') AS token
FROM _reference1099
WHERE _idrref = decode('b50ef0d4155608d711f0660301472272', 'hex');  -- example: outlet code 3514, replace with the real idrref from step 1
```
