from flask_login import LoginManager, UserMixin
import os

class User(UserMixin):
    def __init__(self, id, email, role, is_active):
        self.id = id
        self.email = email
        self.role = role
        self._active = bool(is_active)

    @property
    def is_active(self):
        return self._active