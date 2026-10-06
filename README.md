# Collecteteller Diaconie

Mobielvriendelijke webapp voor de zondagse collectetelling.

## Functies
- Twee vaste collectedoelen per zondag.
- Optionele derde collecte.
- Collectedoel 3 kan tijdens de telling handmatig worden gewijzigd/overruled.
- Blauwe bonnen van €0,75 en groene bonnen van €1,00.
- Telling van verpakkingen/bedragen €5, €10, €20, €50 en €100 plus overig contant.
- Directe berekening van de totalen.
- Tellingen bewaren en later corrigeren.
- Excel per zondag en Excel-jaaroverzicht.
- SQLite database in `data/collectes.db`.
- Database wordt bij een update automatisch uitgebreid; bestaande tellingen blijven behouden.

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
2. Maak een wachtwoordhash: `python maak_wachtwoord.py`
3. Zet lokaal de variabelen `APP_USERNAME`, `APP_PASSWORD_HASH` en `SESSION_SECRET`.
4. Zet dezelfde variabelen in Railway bij de service Variables.

Aanbevolen gebruikersnaam: `diaconie`.
`APP_PASSWORD_HASH` bevat alleen een PBKDF2-hash, niet het leesbare wachtwoord.
`SESSION_SECRET` mag een lange willekeurige tekenreeks zijn.
Voor lokaal testen via http kan `COOKIE_HTTPS_ONLY=0` nodig zijn. Op Railway laat je deze weg (standaard veilig op https).
