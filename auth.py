import base64
import hashlib
import hmac
import os
import secrets


def make_password_hash(password: str, iterations: int = 260_000) -> str:
    salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )

    return (
        f"pbkdf2_sha256${iterations}$"
        f"{base64.urlsafe_b64encode(salt).decode()}$"
        f"{base64.urlsafe_b64encode(digest).decode()}"
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)

        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)

        salt = base64.urlsafe_b64decode(
            salt_text.encode()
        )

        expected = base64.urlsafe_b64decode(
            digest_text.encode()
        )

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(
            actual,
            expected,
        )

    except (ValueError, TypeError):
        return False


def configured_username() -> str:
    return (
        os.getenv(
            "COLLECTETELLER_USERNAME",
            "diaconie",
        ).strip()
        or "diaconie"
    )


def configured_password_hash() -> str:
    return os.getenv(
        "COLLECTETELLER_PASSWORD_HASH",
        "",
    ).strip()