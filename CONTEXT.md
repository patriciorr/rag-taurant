# Restaurant

Shared language for the restaurant menu and reservation experience.

## Menu

**Menu item**:
A dish or drink offered by the restaurant, with a price, category, allergen information, and dietary attributes.
_Avoid_: Product

## Reservations

**Reservation**:
A customer's booking for a restaurant day and time, including party size and contact details.
_Avoid_: Appointment

**Reservation day**:
The restaurant-local calendar date for which a reservation is held. The booking horizon is 14 dates beginning today and ending 13 days later. A customer may have at most one active reservation for a day.

**Reservation time**:
A local restaurant time slot available on the half-hour, from 12:00 through 23:00.

**Reservation contact**:
The email address and phone number associated with a reservation. Either contact value identifies a reservation for its day; both are required when accessing an existing reservation.

**Cancellation**:
A customer's decision to give up an existing reservation. The canceled reservation remains distinguishable from an active reservation, and its day becomes available for a new active reservation.
_Avoid_: Deletion

## Restaurant information

**Weather forecast**:
The Open-Meteo forecast for the restaurant's location. The chatbot may report only dates available in the 14-date forecast beginning today, including a date from a reservation identified in the current conversation.