# Feature Specification: Order Gateway with Stock and Hours Checks

**Feature Branch**: `001-order-gateway`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "the gateway takes store ID, drinks and add-ins, and the order service checks stock and hours before payment"

## Clarifications

### Session 2026-11-07

- Q: When does the order service reserve stock for an order: before payment, after payment
  succeeds, or never? → A: Before payment. Stock is reserved once hours and stock checks pass,
  and only then does payment start.
- Q: What happens to reserved stock if payment fails or the customer never completes it? → A:
  Released at once on payment failure, or after 10 minutes with no payment result.
- Q: Which store IDs does the order service use? → A: Exactly the IDs in the mobile orders CSV
  (`SB-10482`, `SB-11937`, `SB-20516`), with no mapping to any other store list; an ID with no
  store record is refused.
- Q: If a milk or add-in has no stock record at a store, is it available or unavailable? → A:
  Unavailable; every component a store sells needs a stock record.
- Q: Where does the order service get store hours? → A: Weekly opening hours per store in
  Pacific time, plus a temporary-closure flag.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Place a mobile order that can be made (Priority: P1)

A customer sends a mobile order to the gateway with a store ID and one or more drink lines. Each
line names the drink, size, milk, add-ins and quantity. The gateway passes the order to the order
service, which asks the store stock service whether the store is open, then asks it to check and
reserve every component in one request, and only then sends the customer on to payment.

**Why this priority**: Accepting orders that can actually be made is the reason the feature exists.

**Independent Test**: Send an order for an open store whose components are all in stock and confirm
it is accepted and handed to payment.

**Acceptance Scenarios**:

1. **Given** store SB-10482 is open and has 2% Milk, Vanilla Syrup and Caramel Drizzle in
   stock, **When** a customer orders 1 Grande Iced Caramel Macchiato with 2% Milk, Vanilla Syrup
   and Caramel Drizzle, **Then** the order is accepted and the customer is sent to payment.
2. **Given** a store is open, **When** a customer orders 2 Pike Place Roast with milk `None` and no
   add-ins, **Then** the order is accepted without any milk or add-in check.

---

### User Story 2 - Refuse an order when the store is closed (Priority: P2)

A customer orders from a store that is closed at the time the order is submitted. The order service
asks the store stock service, which owns store hours, whether the store is open at that time. When
the store stock service answers closed, the order service refuses the order before asking about
stock and before payment, and tells the customer the store is closed.

**Why this priority**: Taking money for a drink no one can make damages trust more than any other
failure.

**Independent Test**: Send any order to a closed store and confirm it is refused with the closed
message and that no payment is started.

**Acceptance Scenarios**:

1. **Given** Bellevue Square (SB-20516) is closed at 2025-03-03 05:42, **When** order
   MO-250303-0001 (1 Venti Pike Place Roast) is submitted, **Then** it is refused with
   "Bellevue Square is closed right now and can't take mobile orders." and no payment starts.

---

### User Story 3 - Refuse an order when a component is out of stock (Priority: P3)

A customer orders a drink whose milk or add-in has run out at that store. The store stock service
reports the component as unavailable, and the order service refuses the order before payment and
names the line and the missing component.

**Why this priority**: Prevents customers paying for drinks that will be cancelled at the counter.

**Independent Test**: Send an order needing a component with no available stock and confirm the
refusal names that component.

**Acceptance Scenarios**:

1. **Given** store SB-10482 has 0 Oatmilk available, **When** order MO-250307-0031 (1 Grande
   Matcha Tea Latte, Oatmilk) is submitted, **Then** it is refused with "Line 1, Grande Matcha
   Tea Latte: Oatmilk is unavailable at this store right now." and no payment starts.
2. **Given** store SB-10482 has 0 Caramel Drizzle available, **When** order MO-250306-0019 (1 Grande
   Iced Caramel Macchiato, 2% Milk, Vanilla Syrup; Caramel Drizzle) is submitted, **Then** it is
   refused with "Line 1, Grande Iced Caramel Macchiato: Caramel Drizzle is unavailable at this
   store right now." and no payment starts.
3. **Given** store SB-11937 has 3 Brown Sugar Syrup available (more than 0 but fewer than 4),
   **When** order MO-250307-0028 (4 Grande Iced Brown Sugar Oatmilk Shaken Espresso, Oatmilk,
   Brown Sugar Syrup) is submitted, **Then** it is refused with "Line 1, Grande Iced Brown Sugar
   Oatmilk Shaken Espresso: Brown Sugar Syrup is unavailable at this store right now.", no stock
   is reserved, and no payment starts.

---

### User Story 4 - Refuse later orders once an earlier order takes the last unit (Priority: P4)

Several customers order the same component within minutes. The first order that passes its checks
has its stock reserved by the store stock service before payment, and every later order that needs
the now-exhausted component is refused.

**Why this priority**: Without it, two customers can pay for the same last carton of oat milk.

**Independent Test**: Submit two orders in sequence that both need the last unit of one component
and confirm the first is accepted and the second is refused naming that component.

**Acceptance Scenarios**:

1. **Given** store SB-10482 has 1 Oatmilk available at 06:31 on 2025-03-07, **When** order
   MO-250307-0023 (1 Grande Caffè Latte, Oatmilk) is submitted, **Then** it is accepted and 1
   Oatmilk is reserved before payment starts, leaving 0 available.
2. **Given** scenario 1 has run, **When** order MO-250307-0024 (1 Grande Iced Brown Sugar Oatmilk
   Shaken Espresso, Oatmilk, Brown Sugar Syrup) is submitted at 06:36, **Then** it is refused with
   "Line 1, Grande Iced Brown Sugar Oatmilk Shaken Espresso: Oatmilk is unavailable at this store
   right now." and no payment starts.
3. **Given** the store stock service reported 1 Oatmilk available at store SB-10482 when the
   customer opened the menu before 2025-03-07T06:31:07-08:00, and order MO-250307-0023 submitted
   at 2025-03-07T06:31:07-08:00 was then accepted and reserved that 1 Oatmilk, **When** the same
   customer submits order MO-250307-0024 (1 Grande Iced Brown Sugar Oatmilk Shaken Espresso,
   Oatmilk, Brown Sugar Syrup) at 2025-03-07T06:36:42-08:00, **Then** it is refused with "Line 1,
   Grande Iced Brown Sugar Oatmilk Shaken Espresso: Oatmilk is unavailable at this store right
   now.", no stock is reserved for it, and no payment starts.
4. **Given** store SB-10482 has 1 Oatmilk available, orders MO-250307-0023 and MO-250307-0024 have
   both passed the hours check, and the store stock service handles MO-250307-0023's
   check-and-reserve request first and reserves the 1 Oatmilk, **When** it then handles
   MO-250307-0024's check-and-reserve request, **Then** it reserves nothing for MO-250307-0024
   and reports Oatmilk as unavailable, and MO-250307-0024 is refused with "Line 1, Grande Iced
   Brown Sugar Oatmilk Shaken Espresso: Oatmilk is unavailable at this store right now." and no
   payment starts.

---

### User Story 5 - Refuse an order when the store stock service cannot answer (Priority: P5)

A customer submits an order while the store stock service is down or slow. The order service does
not guess: it refuses the order without payment and asks the customer to try again.

**Why this priority**: Assuming stock is there when it cannot be confirmed would take payment for
drinks that may not exist.

**Independent Test**: Make the store stock service fail to answer and confirm the order is refused
with the try-again message and no payment starts.

**Acceptance Scenarios**:

1. **Given** the store stock service does not answer the check-and-reserve request within 2 seconds,
   **When** order MO-250303-0005 (store SB-11937, 1 Grande Iced Brown Sugar Oatmilk Shaken Espresso,
   Oatmilk, Brown Sugar Syrup) is submitted at 2025-03-03T07:22:40-08:00, **Then** it is refused
   with "We can't reach this store right now. Please try again in a moment." and no
   payment starts.
2. **Given** the store stock service returns an error for the hours question, **When** order
   MO-250303-0005 is submitted, **Then** it is refused with "We can't reach this store right now.
   Please try again in a moment.", no check-and-reserve request is sent, and no payment starts.
3. **Given** store SB-10482 has 1 Oatmilk available and the store stock service does not answer
   MO-250307-0023's check-and-reserve request within 2 seconds, **When** order MO-250307-0023 (1
   Grande Caffè Latte, Oatmilk) is submitted at 2025-03-07T06:31:07-08:00, **Then** it is refused
   with "We can't reach this store right now. Please try again in a moment." and no
   payment starts.
4. **Given** the store stock service does not answer the store record lookup for SB-10482 within 2
   seconds, **When** order MO-250307-0023 (1 Grande Caffè Latte, Oatmilk) is submitted at
   2025-03-07T06:31:07-08:00, **Then** it is refused with "We can't reach this store right now.
   Please try again in a moment." (not "We can't find store SB-10482."), no hours question or
   check-and-reserve request is sent, and no payment starts.
5. **Given** store SB-10482 has a store record and the store stock service does not answer the
   hours question for SB-10482 within 2 seconds, **When** order MO-250307-0023 (1 Grande Caffè
   Latte, Oatmilk) is submitted at 2025-03-07T06:31:07-08:00, **Then** it is refused with "We
   can't reach this store right now. Please try again in a moment." (not the R1 closed-store
   message), no check-and-reserve request is sent, and no payment starts.

---

### User Story 6 - Refuse an order for a store that does not exist (Priority: P6)

A customer's order carries a store ID the store stock service has no record of. The order service
refuses it before asking about hours or stock, and tells the customer the store can't be found.

**Why this priority**: Without it, an unknown store could be treated as open with no stock limits.

**Independent Test**: Send an order with a store ID that has no store record and confirm the
not-found refusal comes back without any hours or stock question.

**Acceptance Scenarios**:

1. **Given** the store stock service has no store record for `SB-99999` (an ID that does not appear
   in the mobile orders CSV), **When** an order with store ID `SB-99999` for 1 Grande Pike Place
   Roast, milk `None`, is submitted, **Then** it is refused with "We can't find store SB-99999.",
   no hours question or check-and-reserve request is sent, and no payment starts.

---

### Edge Cases

- A store is closed and also out of stock: the closed refusal is returned, not a stock refusal.
- An order has several lines and only one has a missing component: the whole order is refused and
  the message names that line.
- A line's quantity needs more of a component than is left: the whole order is refused naming
  that component, even though some is left (User Story 3, scenario 3).
- Two orders arrive close together for the last unit of a component: the store stock service
  handles their check-and-reserve requests one at a time, reserves the unit for the first, and
  reserves nothing for the second, which is refused naming that component (User Story 4,
  scenario 4).
- A drink uses a milk or add-in with no stock record at that store (for example Whole Milk,
  Soymilk, Extra Shot): it is treated as unavailable and the order is refused naming it.
- A component shows as available on the menu but is gone by the time the order is submitted:
  the order is checked again at submission and refused with the stock message naming that
  component (User Story 4, scenario 3).
- Payment fails or no payment result arrives within 10 minutes: the order's reservation is
  released and the stock becomes available to the next order.
- The store ID has no store record: the order is refused with "We can't find store {store ID}."
  (User Story 6).
- The store stock service errors or does not answer within 2 seconds: the order is refused with "We
  can't reach this store right now. Please try again in a moment." and no payment starts (User Story
  5).
- A check-and-reserve request times out but the store stock service did reserve the stock: the
  order is still refused, payment is never confirmed, and the reservation is released after 10
  minutes (FR-008a).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The gateway MUST accept an order containing a store ID and one or more lines, each
  with line number, drink name, size, milk (or `None`), zero or more add-ins, and quantity.
- **FR-002**: The gateway MUST reject an order with no lines, a missing store ID, or a quantity
  below 1, without contacting the order service.
- **FR-003**: The order service MUST ask the store stock service about store hours first, then send
  one check-and-reserve request for the whole order, and MUST get both answers before payment.
- **FR-004**: The order service MUST refuse an order when the store stock service answers that the
  store is closed at the order's submission time, with the message "{store name} is closed right
  now and can't take mobile orders."
- **FR-005**: The order service MUST refuse an order when the store stock service's
  check-and-reserve answer reports a line's milk or add-in as unavailable, with the message "Line
  {n}, {size} {drink}: {component} is unavailable at this store right now."
- **FR-006**: The store stock service MUST judge stock as on hand minus reserved, and report a
  component as unavailable when that is 0 or less, or less than the quantity the line needs. The
  order service MUST NOT compute availability itself.
- **FR-007**: The order service MUST NOT start payment for a refused order.
- **FR-008**: Stock MUST be checked and reserved in one request, before payment. Once the hours
  check passes, the order service MUST send the store stock service one check-and-reserve request
  covering every line, and MUST NOT ask about stock in a separate call first. The store stock
  service MUST either add every line's component quantities to that store's reserved quantity, or
  reserve nothing and report the first unavailable component (lines in line-number order; within
  a line, milk first, then add-ins in the order listed). It MUST handle requests for the same
  store one at a time, so two orders cannot both reserve the same last unit. The order service
  MUST start payment only after every line is reserved.
- **FR-008a**: The order service MUST ask the store stock service to release an order's
  reservation at once when payment fails. The store stock service MUST release a reservation
  itself after 10 minutes when the order service has not confirmed payment.
- **FR-008b**: When the store stock service returns an error, or does not answer within 2 seconds,
  for the store record lookup, the hours question, or the check-and-reserve request, the order
  service MUST refuse the order with the message "We can't reach this store right now. Please try
  again in a moment.", MUST NOT start payment, and MUST NOT treat the store as open or the stock as
  available. This message MUST NOT name a line or component.
- **FR-009**: The gateway MUST pass the store ID on exactly as sent, in the mobile orders CSV
  format (for example `SB-10482`). When the store stock service has no store record for that ID,
  the order service MUST refuse the order before any hours or stock question with the message
  "We can't find store {store ID}." An error or timeout on the store record lookup MUST NOT be
  treated as "no store record"; it is refused under FR-008b instead.
- **FR-010**: The store stock service MUST report a milk or add-in that has no stock record at
  that store as unavailable, and the order service MUST refuse the order with the stock message
  naming it.
- **FR-011**: The store stock service MUST decide whether a store is open from that store's weekly
  opening hours in Pacific time and its temporary-closure flag, at the submission time the order
  service sends. The order service MUST NOT hold or compute store hours.
- **FR-012**: The store stock service MUST be the only service that holds store records, weekly
  opening hours, temporary-closure flags, stock records and reservations. The gateway and the
  order service MUST get them only through the store stock service's published endpoints
  (CLAUDE.md rule 2, no shared database).
- **FR-013**: Any availability shown on the menu MUST come from the store stock service at the
  time it is shown, is display only, and MUST NOT reserve or hold stock. The order service MUST
  check hours and send the check-and-reserve request when the order is submitted, and MUST use
  those answers, not the menu's.

### Key Entities

- **Order**: one customer submission; has an order ID, store ID, submission time and one or more
  lines.
- **Order line**: one drink in an order; has line number, drink name, size, milk, add-ins and
  quantity.
- **Store**: has a store ID (as in the mobile orders CSV, for example `SB-10482`), name, weekly
  opening hours in Pacific time, and a temporary-closure flag. Owned by the store stock service.
- **Stock record**: one component at one store; has on-hand and reserved quantities. Every
  component a store sells MUST have one. Owned by the store stock service.
- **Reservation**: stock held for one order between passing checks and payment; released on
  payment failure or after 10 minutes with no payment confirmation. Owned by the store stock
  service.
- **Refusal**: the outcome of a failed check; has the missing component (or "store_closed") and
  the exact customer message.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the store stock service answering normally, every order in the sample week
  (data/mobile_orders_2025-03-03_to_09.csv) gets the outcome in its `expected_outcome` column (19
  accepted, 21 refused), and each of the 21 refused orders returns exactly the text in its
  `expected_message` column, character for character.
- **SC-002**: No refused order in the sample week starts a payment (0 of 21).
- **SC-003**: Customers receive an accept or refuse answer within 2 seconds of submitting.
- **SC-004**: Orders sent to a closed store are refused with "Bellevue Square is closed right now
  and can't take mobile orders." (4 of 4 sample orders).

## Assumptions

- The mobile orders CSV (data/mobile_orders_2025-03-03_to_09.csv) is the only data source for
  this feature. Each test sets store hours and stock so that the order's `expected_outcome` and
  `expected_message` hold; no other stock file is used.
- Bellevue Square (`SB-20516`) is under a temporary closure for the whole sample week.
- One order is checked as a whole: if any line fails, the whole order is refused.
- Payment itself is handled by an existing payment provider and is out of scope here.
- Drink recipes (how much of each component a drink uses) are one unit per drink per component
  unless a recipe says otherwise.
