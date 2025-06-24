import re

def validate_password_complexity(password: str) -> bool:
    """
    Enforces the following password rules:
    - Minimum 8 characters
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one special character (non-alphanumeric)
    """
    if len(password) < 8:
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[^a-zA-Z0-9]', password):
        return False
    return True
