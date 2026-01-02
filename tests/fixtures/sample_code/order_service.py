"""Order service for testing topology."""

from database import get_connection
from user_service import UserService


class OrderService:
    """Service for managing orders."""
    
    def __init__(self):
        self.conn = get_connection()
        self.user_service = UserService()
    
    def create_order(self, user_id: int, total: float):
        """Create a new order."""
        # Verify user exists
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        cursor = self.conn.execute(
            "INSERT INTO orders (user_id, total, status) VALUES (?, ?, ?)",
            (user_id, total, 'pending')
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_orders_by_user(self, user_id: int):
        """Get all orders for a user."""
        cursor = self.conn.execute(
            "SELECT id, user_id, total, status FROM orders WHERE user_id = ?",
            (user_id,)
        )
        return cursor.fetchall()
    
    def update_order_status(self, order_id: int, status: str):
        """Update order status."""
        self.conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id)
        )
        self.conn.commit()
