from telepathy.answers import extract_answer, same_number


def test_boxed_with_commas():
    assert extract_answer(r"so \boxed{1,260}") == "1260"


def test_decimal_and_last_boxed_wins():
    assert extract_answer(r"\boxed{3} then \boxed{12.5}") == "12.5"


def test_no_boxed_uses_last_number():
    assert extract_answer("it costs 7 then 9 dollars") == "9"


def test_no_number():
    assert extract_answer("no idea") is None
    assert extract_answer(r"\boxed{}") is None


def test_same_number():
    assert same_number("18", "18.0")
    assert not same_number("18", "19")
    assert not same_number(None, "1")
