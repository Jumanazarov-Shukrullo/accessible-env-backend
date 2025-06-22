from enum import Enum


class RoleID(Enum):
    SUPERADMIN = 1
    ADMIN = 2
    USER = 3  # Note: USER is at ID 3 in the existing database
    MANAGER = 4
    INSPECTOR = 5
