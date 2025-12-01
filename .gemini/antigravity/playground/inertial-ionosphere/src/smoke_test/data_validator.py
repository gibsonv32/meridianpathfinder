def validate_email(email: str) -> bool:
    """
    Validates an email address.
    Returns True if the email contains '@' and '.', False otherwise.
    """
    if not isinstance(email, str):
        return False
    return "@" in email and "." in email


def validate_age(age: int) -> bool:
    """
    Validates an age.
    Returns True if age is between 0 and 120 inclusive, False otherwise.
    """
    if not isinstance(age, int):
        return False
    return 0 <= age <= 120
