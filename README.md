# Collecteteller Diaconie

Mobielvriendelijke webapp voor de zondagse collectetelling.

## Functies
- Twee vaste en maximaal twee optionele collectedoelen per zondag.
- Bevestiging en vergrendeling per collecte tijdens het tellen.
- Collectedoelen 3 en 4 kunnen tijdens de telling handmatig worden gewijzigd.
- Blauwe bonnen van €0,75 en groene bonnen van €1,00.
- Telling van verpakkingen/bedragen €5, €10, €20, €50 en €100 plus overig contant.
- Directe berekening van de totalen.
- Tellingen bewaren en later corrigeren.
- Excel per zondag en Excel-jaaroverzicht.
- SQLite database in `data/collectes.db`.
- Database wordt bij een update automatisch uitgebreid; bestaande tellingen blijven behouden.
- Stel optioneel `DB_PATH` in om een andere SQLite-database te gebruiken, bijvoorbeeld het mountpad van een Railway Volume. Zonder deze variabele blijft `data/collectes.db` in gebruik.

## Starten in Windows / VS Code

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload
```

Open daarna: http://127.0.0.1:8000

## Mappen
- `app.py` - FastAPI applicatie
- `database.py` - database en migraties
- `routes/` - pagina's, opslag en Excel-export
- `templates/` - HTML
- `static/css/` - vormgeving
- `data/` - lokale SQLite database (wordt automatisch aangemaakt)

## E-mail
De applicatie maakt de Excelbestanden al. Automatisch mailen voegen we toe zodra het afzenderadres/mailplatform is gekozen; daarvoor moeten geen wachtwoorden in de broncode worden gezet.

## Login instellen

De app gebruikt één beveiligde login voor de huidige lokale versie.

1. Installeer de requirements: `pip install -r requirements.txt`
2. Vul lokaal in `.env` de bestaande `COLLECTETELLER_USERNAME` en `COLLECTETELLER_PASSWORD_HASH` van Railway in; genereer geen nieuwe gebruikersnaam of wachtwoordhash.
3. De lokale `.env` wordt automatisch ingelezen. Voor HTTP lokaal staat `COOKIE_HTTPS_ONLY=0`; wijzig deze instelling niet op Railway.
4. `SESSION_SECRET` is lokaal een vaste, willekeurige waarde en hoeft niet gelijk te zijn aan die van Railway.

Aanbevolen gebruikersnaam: `diaconie`.
`COLLECTETELLER_PASSWORD_HASH` bevat alleen een PBKDF2-hash, niet het leesbare wachtwoord.
De `.env` bevat secrets en wordt door Git genegeerd. Deel of commit dit bestand niet.
