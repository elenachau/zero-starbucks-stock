# CLAUDE.md

Rules every agent and contributor MUST follow in this repo. The project constitution is in
`.specify/memory/constitution.md` and applies alongside these rules.

## Service rules

1. **Fixed OpenAPI contracts.** Each service's OpenAPI contract is fixed once it is published.
   A change MUST NOT rename, remove, or retype any path, field, status code, or refusal
   message in a published contract. A breaking change MUST ship as a new versioned path
   (for example `/v2/orders`) while the old one keeps working.
2. **No shared database.** Each service MUST own its data store. A service MUST NOT read from
   or write to another service's database, tables, or files. Services MUST exchange data only
   through each other's published OpenAPI endpoints.
3. **No merge until contract tests pass.** A pull request MUST NOT be merged until every
   contract test passes in CI for every service it touches, including the consumers of any
   contract it changes. A failing or skipped contract test blocks the merge.

## Refusal rules

Source: `data/mobile_orders_2025-03-03_to_09.csv`, rows with `expected_outcome = refused`
(21 rows, 5 scenario tags). This CSV is the only data source for these rules; store IDs are
used exactly as it writes them (for example `SB-10482`). The store stock service is the only
service that holds store hours, closure flags, stock and reservations; the order service MUST
ask it and MUST NOT hold any of them. Stock is judged by the store stock service with this rule:
available = `quantity_on_hand` − `reserved_quantity`, and a component is out when
available ≤ 0. Checks MUST run in this order: store record (R7), then store hours (R1), then
one check-and-reserve request for stock (R2–R5), line by line.
The order service MUST refuse at the first failing check and MUST NOT take payment for a
refused order. Every refusal MUST return the exact message below, with the placeholders
filled from the order line. All 21 refused rows MUST also pass spec.md SC-001. R1–R5 come
from the CSV; R6–R7 are refusals the spec defines that have no CSV row.

Stock message template, used by rules R2–R5:
`Line {line_item_number}, {size} {drink_name}: {component} is unavailable at this store right now.`

- **R1 `store_closed` (hours, not stock).** The store stock service owns store hours and decides
  whether the store is open at `submitted_at`. The order service MUST ask it before asking about
  stock, and when the answer is closed MUST refuse the order before any stock question, whatever
  the drinks are. Message:
  `{store_name} is closed right now and can't take mobile orders.`
  Rows: MO-250303-0001, MO-250305-0013, MO-250308-0034, MO-250309-0040 (all SB-20516,
  Bellevue Square).
  Tested by: spec.md User Story 2 scenario 1, SC-004.
- **R2 `base_out_of_stock`.** When the line's milk (its drink base) has available ≤ 0, the
  order MUST be refused and `{component}` MUST be the milk name. A line with milk `None`
  MUST NOT be checked for milk.
  Rows: MO-250304-0007, MO-250304-0010 (Almondmilk); MO-250307-0029, MO-250307-0031,
  MO-250308-0033, MO-250309-0037 (Oatmilk).
  Tested by: spec.md User Story 3 scenario 1.
- **R3 `add_in_out_of_stock`.** When any add-in on the line has available ≤ 0, the order MUST
  be refused and `{component}` MUST be that add-in's name.
  Rows: MO-250305-0014, MO-250308-0035 (Vanilla Sweet Cream Cold Foam); MO-250306-0019,
  MO-250309-0039 (Caramel Drizzle); MO-250309-0038 (Brown Sugar Syrup).
  Tested by: spec.md User Story 3 scenario 2.
- **R4 `stock_runs_out_mid_order`.** Once an order passes the hours check, the order service
  MUST send the store stock service one check-and-reserve request for the whole order before
  payment starts. The store stock service MUST either add every component quantity to
  `reserved_quantity` or reserve nothing, and MUST handle requests for a store one at a time, so
  the next order is checked against the reduced available stock. The order that takes the last available unit
  MUST be accepted, and every later order needing that component MUST be refused with that
  component named.
  Rows: MO-250307-0023 accepted (last Oatmilk); MO-250307-0024, MO-250307-0025,
  MO-250307-0027 refused (Oatmilk); MO-250307-0026 refused (Vanilla Sweet Cream Cold Foam).
  Tested by: spec.md User Story 4 scenarios 1-4 (scenario 3: available on the menu, gone at
  submission; scenario 4: two check-and-reserve requests race for the last unit).
- **R5 `insufficient_quantity`.** When a line's `quantity` needs more of a component than is
  available, the order MUST be refused even if available > 0, and `{component}` MUST be
  that component. The order service MUST NOT accept part of a line.
  Rows: MO-250307-0028 (quantity 4), MO-250307-0030 (quantity 3), both Brown Sugar Syrup.
  Tested by: spec.md User Story 3 scenario 3.

### Refusals defined by the spec (no CSV row)

- **R6 store stock service unavailable.** When the store stock service returns an error, or does
  not answer within 2 seconds, for the store record, hours, or check-and-reserve request, the
  order MUST be refused, MUST NOT start payment, and MUST NOT be treated as open or in stock.
  This message MUST NOT name a line or component, because nothing was found to be unavailable.
  Message: `We can't reach this store right now. Please try again in a moment.`
  A store record lookup that errors or times out MUST get this message, never R7's.
  Tested by: spec.md User Story 5 scenarios 1-4 (scenario 3: MO-250307-0023's check-and-reserve
  times out; scenario 4: the store record lookup times out before hours are checked).
- **R7 unknown store.** When the store stock service has no store record for the order's store
  ID, the order MUST be refused before any hours or stock question. Message:
  `We can't find store {store_id}.`
  Tested by: spec.md User Story 6 scenario 1.
