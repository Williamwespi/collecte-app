from getpass import getpass

from auth import make_password_hash


print()
print("Collecteteller - wachtwoord instellen")
print("-------------------------------------")
print()

wachtwoord = getpass(
    "Nieuw wachtwoord: "
)

bevestiging = getpass(
    "Herhaal wachtwoord: "
)


if not wachtwoord:
    raise SystemExit(
        "Het wachtwoord mag niet leeg zijn."
    )


if wachtwoord != bevestiging:
    raise SystemExit(
        "De wachtwoorden zijn niet gelijk."
    )


password_hash = make_password_hash(
    wachtwoord
)


print()
print("Wachtwoord aangemaakt.")
print()
print(
    "Kopieer de VOLLEDIGE hash hieronder:"
)
print()
print(password_hash)
print()