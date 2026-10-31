import enum


class UserRole(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    STORE_ADMIN = "STORE_ADMIN"


class TransactionType(str, enum.Enum):
    RECEIVED = "RECEIVED"
    ISSUED = "ISSUED"
    ADJUSTED = "ADJUSTED"

