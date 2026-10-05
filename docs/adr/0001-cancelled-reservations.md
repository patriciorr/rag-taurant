# Retain canceled reservations

Canceling a reservation changes it to a canceled state instead of physically deleting it, preserving the booking history while making its day available for another active reservation by the same contact. Only active reservations participate in the per-contact-per-day uniqueness rule. This keeps cancellation safe to retry and allows a customer to book the same day again; a production deployment must define how long canceled records and their contact details are retained.
