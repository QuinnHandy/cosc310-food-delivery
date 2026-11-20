from app.core.security import hash_password, verify_password

PASSWORD = "Password123!"


# The stored value is a salted hash in the documented format, never the plain password.
def test_hash_is_not_the_plain_password():
    stored = hash_password(PASSWORD)

    assert PASSWORD not in stored
    algorithm, iterations, salt_hex, hash_hex = stored.split("$")
    assert algorithm == "pbkdf2_sha256"
    assert iterations == "600000"
    assert len(bytes.fromhex(salt_hex)) == 16
    assert len(bytes.fromhex(hash_hex)) == 32


def test_verify_accepts_the_right_password():
    assert verify_password(PASSWORD, hash_password(PASSWORD)) is True


def test_verify_rejects_a_wrong_password():
    assert verify_password("not-the-password", hash_password(PASSWORD)) is False


# Each hash gets its own random salt, so the same password never produces the same string.
def test_same_password_gives_different_hashes():
    first = hash_password(PASSWORD)
    second = hash_password(PASSWORD)

    assert first != second
    assert verify_password(PASSWORD, first) is True
    assert verify_password(PASSWORD, second) is True


# Failure case: a malformed stored value returns False instead of raising.
def test_verify_returns_false_for_malformed_stored_value():
    for stored in ["", "plain-text", "a$b$c", "pbkdf2_sha256$abc$00$00",
                   "pbkdf2_sha256$1$zz$zz", "md5$1$00$00", "pbkdf2_sha256$0$00$00"]:
        assert verify_password(PASSWORD, stored) is False
