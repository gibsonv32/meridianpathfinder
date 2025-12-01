from smoke_test.data_validator import validate_email, validate_age


def test_validate_email_valid():
    assert validate_email("test@example.com") is True
    assert validate_email("user.name@domain.co.uk") is True


def test_validate_email_invalid():
    assert validate_email("invalid-email") is False
    assert validate_email("user@domain") is False  # Missing dot
    assert validate_email("user.domain.com") is False  # Missing at
    assert validate_email("") is False


def test_validate_age_valid():
    assert validate_age(0) is True
    assert validate_age(120) is True
    assert validate_age(25) is True


def test_validate_age_invalid():
    assert validate_age(-1) is False
    assert validate_age(121) is False
