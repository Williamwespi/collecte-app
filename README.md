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
