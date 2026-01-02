"""Sample application code for testing topology analysis."""

from database import get_connection
from utils import validate_email


class UserService:
    """Service for managing users."""
    
    def __init__(self):
        self.conn = get_connection()
    
    def get_user_by_id(self, user_id: int):
        """Fetch user by ID."""
        cursor = self.conn.execute(
            "SELECT id, email, name FROM users WHERE id = ?",
            (user_id,)
        )
        return cursor.fetchone()
    
    def get_user_by_email(self, email: str):
        """Fetch user by email."""
        if not validate_email(email):
            raise ValueError("Invalid email")
        
        cursor = self.conn.execute(
            "SELECT id, email, name FROM users WHERE email = ?",
            (email,)
        )
        return cursor.fetchone()
    
    def create_user(self, email: str, name: str):
        """Create a new user."""
        self.conn.execute(
            "INSERT INTO users (email, name) VALUES (?, ?)",
            (email, name)
        )
        self.conn.commit()
        return self.conn.lastrowid
    
    def update_user(self, user_id: int, name: str):
        """Update user name."""
        self.conn.execute(
            "UPDATE users SET name = ? WHERE id = ?",
            (name, user_id)
        )
        self.conn.commit()
    
    def delete_user(self, user_id: int):
        """Delete a user."""
        # Delete related orders first
        self.conn.execute(
            "DELETE FROM orders WHERE user_id = ?",
            (user_id,)
        )
        # Then delete user
        self.conn.execute(
            "DELETE FROM users WHERE id = ?",
            (user_id,)
        )
        self.conn.commit()
