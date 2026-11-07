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
- Q: How does an order's store ID (`SB-10482`) map to the stock data's store ID (`10482`)? → A:
  Strip the `SB-` prefix and match the number exactly; `SB-11937` is its own store, not Capitol
  Hill `11307`; an ID with no store record is refused.
- Q: If a milk or add-in has no stock record at a store, is it available or unavailable? → A:
  Unavailable; every component a store sells needs a stock record.
- Q: Where does the order service get store hours? → A: Weekly opening hours per store in
  Pacific time, plus a temporary-closure flag.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Place a mobile order that can be made (Priority: P1)

A customer sends a mobile order to the gateway with a store ID and one or more drink lines. Each
line names the drink, size, milk, add-ins and quantity. The gateway passes the order to the order
service, which confirms the store is open and every component is in stock, and only then sends the
customer on to payment.

**Why this priority**: Accepting orders that can actually be made is the reason the feature exists.

**Independent Test**: Send an order for an open store whose components are all in stock and confirm
it is accepted and handed to payment.

**Acceptance Scenarios**:

1. **Given** First Hill (10482) is open and has 2% Milk, Vanilla Syrup and Caramel Drizzle in
   stock, **When** a customer orders 1 Grande Iced Caramel Macchiato with 2% Milk, Vanilla Syrup
   and Caramel Drizzle, **Then** the order is accepted and the customer is sent to payment.
2. **Given** a store is open, **When** a customer orders 2 Pike Place Roast with milk `None` and no
   add-ins, **Then** the order is accepted without any milk or add-in check.

---

### User Story 2 - Refuse an order when the store is closed (Priority: P2)

A customer orders from a store that is closed at the time the order is submitted. The order service
refuses it before checking stock and before payment, and tells the customer the store is closed.

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

A customer orders a drink whose milk or add-in has run out at that store. The order service refuses
the order before payment and names the line and the missing component.

**Why this priority**: Prevents customers paying for drinks that will be cancelled at the counter.

**Independent Test**: Send an order needing a component with no available stock and confirm the
refusal names that component.

**Acceptance Scenarios**:

1. **Given** First Hill has 0 Oatmilk available, **When** order MO-250307-0031 (1 Grande Matcha Tea
   Latte, Oatmilk) is submitted, **Then** it is refused with "Line 1, Grande Matcha Tea Latte:
   Oatmilk is unavailable at this store right now." and no payment starts.
2. **Given** First Hill has 0 Caramel Drizzle available, **When** order MO-250306-0019 (1 Grande
   Iced Caramel Macchiato, 2% Milk, Vanilla Syrup; Caramel Drizzle) is submitted, **Then** it is
   refused with "Line 1, Grande Iced Caramel Macchiato: Caramel Drizzle is unavailable at this
   store right now." and no payment starts.
3. **Given** store 11937 has 3 Brown Sugar Syrup available (more than 0 but fewer than 4),
   **When** order MO-250307-0028 (4 Grande Iced Brown Sugar Oatmilk Shaken Espresso, Oatmilk,
   Brown Sugar Syrup) is submitted, **Then** it is refused with "Line 1, Grande Iced Brown Sugar
   Oatmilk Shaken Espresso: Brown Sugar Syrup is unavailable at this store right now.", no stock
   is reserved, and no payment starts.

---

### User Story 4 - Refuse later orders once an earlier order takes the last unit (Priority: P4)

Several customers order the same component within minutes. The first order that passes its checks
reserves the stock before payment, and every later order that needs the now-exhausted component is
refused.

**Why this priority**: Without it, two customers can pay for the same last carton of oat milk.

**Independent Test**: Submit two orders in sequence that both need the last unit of one component
and confirm the first is accepted and the second is refused naming that component.

**Acceptance Scenarios**:

1. **Given** First Hill has 1 Oatmilk available at 06:31 on 2025-03-07, **When** order
   MO-250307-0023 (1 Grande Caffè Latte, Oatmilk) is submitted, **Then** it is accepted and 1
   Oatmilk is reserved before payment starts, leaving 0 available.
2. **Given** scenario 1 has run, **When** order MO-250307-0024 (1 Grande Iced Brown Sugar Oatmilk
   Shaken Espresso, Oatmilk, Brown Sugar Syrup) is submitted at 06:36, **Then** it is refused with
   "Line 1, Grande Iced Brown Sugar Oatmilk Shaken Espresso: Oatmilk is unavailable at this store
   right now." and no payment starts.

---

### Edge Cases

- A store is closed and also out of stock: the closed refusal is returned, not a stock refusal.
- An order has several lines and only one has a missing component: the whole order is refused and
  the message names that line.
- A line's quantity needs more of a component than is left: the whole order is refused naming
  that component, even though some is left (User Story 3, scenario 3).
- Two orders arrive close together for the last unit of a component: the first order to pass
  its checks reserves the unit before payment, so the second sees available 0 and is refused.
- A drink uses a milk or add-in with no stock record at that store (for example Whole Milk,
  Soymilk, Extra Shot): it is treated as unavailable and the order is refused naming it.
- Payment fails or no payment result arrives within 10 minutes: the order's reservation is
  released and the stock becomes available to the next order.
- The store ID has no store record after the `SB-` prefix is removed: the order is refused.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The gateway MUST accept an order containing a store ID and one or more lines, each
  with line number, drink name, size, milk (or `None`), zero or more add-ins, and quantity.
- **FR-002**: The gateway MUST reject an order with no lines, a missing store ID, or a quantity
  below 1, without contacting the order service.
- **FR-003**: The order service MUST check store hours before stock, and stock before payment.
- **FR-004**: The order service MUST refuse an order when the store is closed at the order's
  submission time, with the message "{store name} is closed right now and can't take mobile
  orders."
- **FR-005**: The order service MUST refuse an order when any line's milk or add-in is out of
  stock, with the message "Line {n}, {size} {drink}: {component} is unavailable at this store
  right now."
- **FR-006**: The order service MUST judge stock as on hand minus reserved, and treat a component
  as out of stock when that is 0 or less.
- **FR-007**: The order service MUST NOT start payment for a refused order.
- **FR-008**: The order service MUST reserve stock before payment: once the hours and stock
  checks pass, it MUST add each line's component quantities to that store's reserved quantity,
  and only then start payment.
- **FR-008a**: The order service MUST release an order's reservation at once when payment fails,
  and after 10 minutes when no payment result has arrived.
- **FR-009**: The gateway MUST remove the `SB-` prefix from the store ID and match the remaining
  number exactly to a store record (`SB-10482` → `10482`). `SB-11937` is its own store, not
  Capitol Hill `11307`. An order whose store ID has no store record MUST be refused before any
  hours or stock check with the message "We can't find store {store ID}."
- **FR-010**: The order service MUST treat a milk or add-in that has no stock record at that store
  as unavailable and refuse the order with the stock message naming it.
- **FR-011**: The order service MUST decide whether a store is open from that store's weekly
  opening hours in Pacific time and its temporary-closure flag, using the order's submission
  time.

### Key Entities

- **Order**: one customer submission; has an order ID, store ID, submission time and one or more
  lines.
- **Order line**: one drink in an order; has line number, drink name, size, milk, add-ins and
  quantity.
- **Store**: has a store ID (digits only, no `SB-` prefix), name, weekly opening hours in
  Pacific time, and a temporary-closure flag.
- **Stock record**: one component at one store; has on-hand and reserved quantities. Every
  component a store sells MUST have one.
- **Reservation**: stock held for one order between passing checks and payment; released on
  payment failure or after 10 minutes with no payment result.
- **Refusal**: the outcome of a failed check; has the missing component (or "store_closed") and
  the exact customer message.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every order in the sample week (data/mobile_orders_2025-03-03_to_09.csv) gets the
  outcome in its `expected_outcome` column (19 accepted, 21 refused), and each of the 21 refused
  orders returns exactly the text in its `expected_message` column, character for character.
- **SC-002**: No refused order in the sample week starts a payment (0 of 21).
- **SC-003**: Customers receive an accept or refuse answer within 2 seconds of submitting.
- **SC-004**: Orders sent to a closed store are refused with "Bellevue Square is closed right now
  and can't take mobile orders." (4 of 4 sample orders).

## Assumptions

- Test stock data for the sample week is set per order so each order's expected outcome holds;
  the 7 March 06:45 snapshot alone does not cover the whole week (it shows Vanilla Sweet Cream
  Cold Foam in stock at First Hill, yet MO-250307-0026 at 06:43 expects a refusal for it).
- Bellevue Square (`20516`) is under a temporary closure for the whole sample week.
- One order is checked as a whole: if any line fails, the whole order is refused.
- Payment itself is handled by an existing payment provider and is out of scope here.
- Drink recipes (how much of each component a drink uses) are one unit per drink per component
  unless a recipe says otherwise.
