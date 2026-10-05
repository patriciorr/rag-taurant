# app/core/exceptions.py

class MenuItemNotFoundException(Exception):
    """Raised when a menu item does not exist in the database."""
    def __init__(self, dish_id: str):
        self.dish_id = dish_id
        super().__init__(f"Dish '{dish_id}' not found.")

class EmbeddingServiceException(Exception):
    """Raised when communication or embedding generation with Ollama fails."""
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Error in the embedding service: {detail}")

class DatabaseException(Exception):
    """Raised when an unexpected error occurs in MongoDB operations."""
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Database error: {detail}")

class ReservationNotFoundException(Exception):
    """Raised when a reservation does not exist in the database."""
    def __init__(self, reservation_id: str):
        self.reservation_id = reservation_id
        super().__init__(f"Reservation with ID '{reservation_id}' not found.")

class ReservationConflictException(Exception):
    """Raised when a contact already has a reservation for the requested day."""
    pass

class ReservationValidationException(Exception):
    """Raised when a partial update makes the complete reservation schedule invalid."""
    pass