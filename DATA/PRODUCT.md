# Products & Categories

Database: `tatriw` (1C:Enterprise on PostgreSQL)
Source table: `_reference1085` ("Nomenclature" catalog), 4,736 rows,
hierarchical (self-referencing via `_parentidrref`)

Order line items link here via `_document4542_vt4599._fld4604rref` (see
`DATA/ORDERS.md`).

## Categories: what they actually are

Categories are **root-level rows that have at least one child** —
`_folder` and naming conventions (quotes, capitalization) are unreliable
signals here:

- `_folder` is `false` for essentially every category in this table (the
  same quirk seen on the Outlets table, see `DATA/CLIENT.md`) — it does
  **not** distinguish group/category nodes from real product records.
- Quoted names (`"APPETITO"`, `"MAKIZ"`, `"SAGBAN"`) are only a subset of
  real categories — most are plain, unquoted brand/line names (`Шерин`,
  `ТИМ`, `KAIJA`, `AK45`, `Golden Max`, `MULTIPAK`, etc).
- `_marked = true` on a category (18 of 119) matches a red "marked for
  deletion" icon in the 1C client, e.g. `Ever Лимонад ва сувлар`,
  `баста энергетик`.

## Query: list all categories

```sql
SELECT r._idrref, r._code, r._description, r._marked,
       (SELECT count(*) FROM _reference1085 c WHERE c._parentidrref = r._idrref) AS product_count
FROM _reference1085 r
WHERE r._parentidrref = decode('00000000000000000000000000000000', 'hex')
  AND EXISTS (SELECT 1 FROM _reference1085 c WHERE c._parentidrref = r._idrref)
ORDER BY r._code;
```

**Verified against a live 1C client screenshot**: returns all 119 real
categories, matching exactly except for one — "NOURA" (code 4744) — which
doesn't exist anywhere in this database snapshot at all (not by that code,
not by that description). This snapshot is likely slightly behind the live
system it was captured from (consistent with other staleness found
elsewhere, e.g. `DATA/CLIENT.md`'s income/expense data cutting off at
2026-06-12).

Real products sit under these via `_parentidrref`, e.g. `"SAGBAN"` → 216
products, `Шерин` → 195, `AK45` → 3.

### Full category list (119, as of this snapshot)

| Code | Category                                                    | Marked deleted? | Products |
| ---- | ----------------------------------------------------------- | --------------- | -------- |
| 1    | Андалус                                              |                 | 45       |
| 2    | Шерин                                                  |                 | 195      |
| 3    | ТИМ                                                      |                 | 166      |
| 4    | Ястро                                                  |                 | 31       |
| 5    | Ал-сафи                                               |                 | 52       |
| 6    | Сыр пикантный                                   |                 | 60       |
| 7    | Пиллер                                                |                 | 17       |
| 8    | Микс товарлар                                   |                 | 108      |
| 9    | Сохраним Традиции                           |                 | 128      |
| 10   | TASTY                                                       |                 | 62       |
| 11   | Микадо                                                |                 | 44       |
| 12   | Софин (СЫР)                                         |                 | 9        |
| 13   | Шерин Макаронлари                           |                 | 57       |
| 14   | Шодлик                                                |                 | 33       |
| 15   | Канотча                                              |                 | 16       |
| 16   | Оливьез Майонезь                             |                 | 21       |
| 17   | СЫР МАХСУЛОТЛАРИ                             |                 | 79       |
| 18   | Бариста Кофе Махсулотлари            |                 | 184      |
| 19   | САРАФРОЗ                                            |                 | 116      |
| 20   | KAIJA                                                       |                 | 70       |
| 21   | Мария Голд Молоко                            |                 | 69       |
| 22   | Эмир                                                    |                 | 3        |
| 23   | Гушт Сарой                                         |                 | 20       |
| 24   | САЛАРИ                                                |                 | 109      |
| 25   | Nuttes шоколадная пасталар                |                 | 84       |
| 26   | "MAKIZ"                                                     |                 | 36       |
| 27   | "SAGBAN мясные деликатесы"                  |                 | 53       |
| 28   | "SIR MOZZARELLO"                                            |                 | 17       |
| 29   | "NOVZA"                                                     |                 | 27       |
| 30   | "SAGBAN"                                                    |                 | 216      |
| 31   | "SALOM"                                                     |                 | 189      |
| 32   | "SIR SAGBAN"                                                |                 | 33       |
| 33   | "ЛЮБИМЫЙ"                                            |                 | 15       |
| 34   | "СЛОНИМСКИЙ"                                      |                 | 7        |
| 35   | "APPETITO"                                                  |                 | 44       |
| 36   | Сгущённое молоко                             |                 | 9        |
| 37   | Ястро Сок Россия                              | ✕              | 22       |
| 38   | САФИ товук махсулотлари                | ✕              | 27       |
| 39   | Пингвин сувлари                               |                 | 13       |
| 40   | Тип топ                                               |                 | 20       |
| 41   | Сафо Сув (без газ)                             |                 | 16       |
| 42   | Месни товук махсулотлари              | ✕              | 21       |
| 43   | Самарканд сув                                   |                 | 17       |
| 44   | Бардзими                                            | ✕              | 32       |
| 45   | Мохито Энергетик                             |                 | 13       |
| 46   | Golden Max                                                  |                 | 47       |
| 47   | Бочкари                                              | ✕              | 14       |
| 48   | Тоза чой                                             | ✕              | 132      |
| 49   | ТАКВО ГУШТ                                         | ✕              | 6        |
| 50   | Чоткол                                                |                 | 15       |
| 51   | Балик махсулотлари                         |                 | 4        |
| 52   | Лимонад ва сувлар                            | ✕              | 16       |
| 53   | Импорт товарлар                               |                 | 12       |
| 54   | Тушонкалар_                                       |                 | 4        |
| 55   | Натурелла горох ва кукурузалари |                 | 5        |
| 56   | Зайчик                                                |                 | 10       |
| 57   | Чипсы DRIVE                                            | ✕              | 7        |
| 58   | Good Day                                                    |                 | 7        |
| 2750 | ЯПРОК                                                  |                 | 110      |
| 2751 | ЛАММ                                                    |                 | 125      |
| 2752 | ПЕРСИЛ                                                |                 | 1        |
| 2753 | СЕН КОМФОРТ                                       |                 | 19       |
| 2754 | ХЙАЛ-СОВИА                                         |                 | 180      |
| 2755 | РАПМ-СФАРЗО                                       |                 | 13       |
| 2756 | ЛАСКА                                                  |                 | 12       |
| 2792 | Доброе                                                |                 | 68       |
| 2793 | Водий                                                  |                 | 8        |
| 2933 | Олео                                                    |                 | 5        |
| 3020 | AMRA-PREMIAL                                                |                 | 148      |
| 3232 | ВОЛИДА                                                |                 | 34       |
| 3299 | Мясные деликатесы                           |                 | 35       |
| 3300 | Приправич приправалари                 | ✕              | 109      |
| 3301 | Ангел махсулотлари                         |                 | 12       |
| 3302 | Приправич Мельница                         | ✕              | 24       |
| 3309 | Paradisee                                                   |                 | 11       |
| 3336 | Кумир 5 секунд                                   |                 | 3        |
| 3383 | Олео Масло Сливочное                      |                 | 17       |
| 3410 | Yangicha                                                    |                 | 32       |
| 3446 | Ever Лимонад ва сувлар                       | ✕              | 15       |
| 3478 | Bai yun fix (BY)                                            |                 | 24       |
| 3486 | Janob Semichka                                              |                 | 8        |
| 3509 | Янгича УН махсулотлари                  |                 | 2        |
| 3529 | Варенья ва Джем                                |                 | 23       |
| 3531 | Маккалдо                                            |                 | 8        |
| 3571 | Wellnax Breeze Refresh WC Block 5 Effect                    |                 | 11       |
| 3590 | TANHO (pikanto)                                             |                 | 2        |
| 3632 | Халапеньо "Hi Food"                                |                 | 29       |
| 3660 | РИЗО Товук Махсулотлари                | ✕              | 4        |
| 3668 | Конфеста Ширинликлари                   |                 | 86       |
| 3757 | BERNI                                                       |                 | 4        |
| 3827 | Силвер Чой                                         |                 | 72       |
| 3880 | Липтон DUBAI                                          | ✕              | 3        |
| 3949 | Сладкий Мир печеньелари                |                 | 72       |
| 3998 | AK45                                                        |                 | 3        |
| 4096 | Рогачев Сут махсулотлари              |                 | 2        |
| 4097 | Ризо Пиканто                                     |                 | 7        |
| 4112 | ''CHik Boom'' ярим таёр махсулотлари    |                 | 8        |
| 4148 | Кароль Тушёнка 338 гр                        |                 | 6        |
| 4185 | FATTY MILK VOLIDA                                           |                 | 4        |
| 4214 | А4                                                         | ✕              | 25       |
| 4215 | Фини                                                    | ✕              | 28       |
| 4278 | "YR" UMKA Пряниклари                              |                 | 5        |
| 4298 | Песочный печенье ва Вафлилар       |                 | 32       |
| 4355 | Чипcы Patrick                                           |                 | 9        |
| 4365 | баста энергетик                               | ✕              | 5        |
| 4385 | Мос Слад                                             |                 | 30       |
| 4440 | Сардор Семичка                                 |                 | 10       |
| 4477 | Титон                                                  |                 | 8        |
| 4482 | MUZUP Сыр                                                |                 | 4        |
| 4487 | Андижон киндер                                 |                 | 25       |
| 4506 | Идеал Ун                                             |                 | 4        |
| 4506 | АК 45 Семечка                                      |                 | 4        |
| 4511 | Асл хан ун                                          |                 | 4        |
| 4533 | СЫР IMPERIYA Tea And Food Product                        |                 | 11       |
| 4566 | Курут ва Сырный палочки                 |                 | 15       |
| 4589 | Лаззат курутлари                             |                 | 4        |
| 4594 | SANIX                                                       |                 | 5        |
| 4690 | MULTIPAK                                                    |                 | 74       |
| 4691 | " MEVITO "                                                  |                 | 4        |

Note: code `4506` appears twice (two distinct categories sharing the same
code, "Идеал Ун" and "АК 45 Семечка") — a data quirk, not a duplicate row.

## Query: list a category's products

```sql
SELECT p._code, p._description
FROM _reference1085 p
WHERE p._parentidrref = decode('HEX_CATEGORY_IDRREF', 'hex')  -- replace with the real category idrref
ORDER BY p._code;
```

## Caveat: brand name in a product ≠ category header of the same name

`NOURA`-branded products (e.g. "Сыр NOURA голланд 0,85") don't sit under a
header literally named "NOURA" in this snapshot — their actual parent
category is `"SIR MOZZARELLO"` (code 28). Don't assume a brand name
mentioned in a product description maps to an identically-named category
header; verify via `_parentidrref` first.

## Query: order line items (product, price, quantity)

See `DATA/ORDERS.md` for the full query joining `_document4542_vt4599` to
this table (`_fld4604rref` = product) to get product name, quantity, and
price per order line.
