"""Domain-specific exceptions"""


class DomainException(Exception):
    """Base exception for domain layer"""

    pass


class BankAPIError(DomainException):
    """Bank API returned an error or is unavailable"""

    pass


class InvalidTransactionDataError(DomainException):
    """Transaction data is malformed or invalid"""

    pass


class InsufficientDataError(DomainException):
    """Not enough transaction history to make decision"""

    pass
