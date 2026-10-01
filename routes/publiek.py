from datetime import date

from io import BytesIO



from fastapi import APIRouter, File, Form, Request, UploadFile

from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from fastapi.templating import Jinja2Templates

from openpyxl import Workbook, load_workbook

from openpyxl.styles import Alignment, Font, PatternFill

from openpyxl.utils import get_column_letter



from database import get_db



router = APIRouter()

templates = Jinja2Templates(directory="templates")



VALUES = {

    "blauw": 0.75,

    "groen": 1.00,

    "munt_5": 5.00,

    "munt_10": 10.00,

    "munt_20": 20.00,

    "munt_50": 50.00,

}





def euro(value):

    return f"€ {float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")





templates.env.filters["euro"] = euro





def totals(row, nummer):
    bonnen = (
        (row[f"c{nummer}_blauw"] or 0) * 0.75
        + (row[f"c{nummer}_groen"] or 0) * 1.00
    )

    briefgeld = (
        (row[f"c{nummer}_munt_5"] or 0) * 5
        + (row[f"c{nummer}_munt_10"] or 0) * 10
        + (row[f"c{nummer}_munt_20"] or 0) * 20
        + (row[f"c{nummer}_munt_50"] or 0) * 50
    )

    muntgeld = row[f"c{nummer}_overig"] or 0
    contant = briefgeld + muntgeld
    totaal = bonnen + contant

    return bonnen, muntgeld, briefgeld, contant, totaal


def derde_collecte_actief(row):

    if not row["doel_3"].strip():

        return False

    return True





@router.get("/", response_class=HTMLResponse)

def home(request: Request):

    vandaag = date.today().isoformat()

    with get_db() as db:

        doel = db.execute("SELECT * FROM collectedoelen WHERE datum=?", (vandaag,)).fetchone()

        recent = db.execute("SELECT * FROM tellingen ORDER BY datum DESC LIMIT 8").fetchall()

    return templates.TemplateResponse(

        "index.html",

        {"request": request, "vandaag": vandaag, "doel": doel, "recent": recent},

    )





@router.get("/tellen", response_class=HTMLResponse)

def tellen(request: Request, datum: str | None = None):

    datum = datum or date.today().isoformat()

    with get_db() as db:

        doel = db.execute("SELECT * FROM collectedoelen WHERE datum=?", (datum,)).fetchone()

        bestaand = db.execute("SELECT * FROM tellingen WHERE datum=?", (datum,)).fetchone()

    return templates.TemplateResponse(

        "tellen.html",

        {"request": request, "datum": datum, "doel": doel, "bestaand": bestaand},

    )





@router.post("/tellen")

def telling_opslaan(

    datum: str = Form(...),

    doel_1: str = Form(...),

    doel_2: str = Form(...),

    doel_3: str = Form(""),

    c1_blauw: int = Form(0), c1_groen: int = Form(0),

    c1_munt_5: int = Form(0), c1_munt_10: int = Form(0), c1_munt_20: int = Form(0),

    c1_munt_50: int = Form(0), c1_overig: float = Form(0),

    c2_blauw: int = Form(0), c2_groen: int = Form(0),

    c2_munt_5: int = Form(0), c2_munt_10: int = Form(0), c2_munt_20: int = Form(0),

    c2_munt_50: int = Form(0), c2_overig: float = Form(0),

    c3_blauw: int = Form(0), c3_groen: int = Form(0),

    c3_munt_5: int = Form(0), c3_munt_10: int = Form(0), c3_munt_20: int = Form(0),

    c3_munt_50: int = Form(0), c3_overig: float = Form(0),

    extra_storting: float = Form(0),

    opmerkingen: str = Form(""),

    geteld_door: str = Form(...),

):

    data = locals().copy()

    columns = list(data.keys())

    placeholders = ",".join("?" for _ in columns)

    updates = ",".join(f"{column}=excluded.{column}" for column in columns if column != "datum")



    with get_db() as db:

        db.execute(

            f"""

            INSERT INTO tellingen ({','.join(columns)})

            VALUES ({placeholders})

            ON CONFLICT(datum) DO UPDATE SET {updates}

            """,

            tuple(data[column] for column in columns),

        )

        db.commit()

    return RedirectResponse(f"/controle/{datum}", status_code=303)





@router.get("/controle/{datum}", response_class=HTMLResponse)

def controle(request: Request, datum: str):

    with get_db() as db:

        row = db.execute("SELECT * FROM tellingen WHERE datum=?", (datum,)).fetchone()

    if not row:

        return RedirectResponse("/")



    t1 = totals(row, 1)

    t2 = totals(row, 2)

    t3 = totals(row, 3)

    heeft_derde = derde_collecte_actief(row)

    totaal = t1[4] + t2[4] + (t3[4] if heeft_derde else 0) + row["extra_storting"]



    return templates.TemplateResponse(

        "controle.html",

        {

            "request": request,

            "r": row,

            "t1": t1,

            "t2": t2,

            "t3": t3,

            "heeft_derde": heeft_derde,

            "totaal": totaal,

        },

    )





@router.get("/doelen", response_class=HTMLResponse)

def doelen(request: Request, melding: str | None = None, fout: str | None = None):

    with get_db() as db:

        rows = db.execute("SELECT * FROM collectedoelen ORDER BY datum DESC").fetchall()

    return templates.TemplateResponse("doelen.html", {"request": request, "rows": rows, "melding": melding, "fout": fout})





@router.post("/doelen")

def doel_opslaan(

    datum: str = Form(...),

    doel_1: str = Form(...),

    doel_2: str = Form(...),

    doel_3: str = Form(""),

):

    with get_db() as db:

        db.execute(

            """

            INSERT INTO collectedoelen(datum, doel_1, doel_2, doel_3)

            VALUES(?,?,?,?)

            ON CONFLICT(datum) DO UPDATE SET

                doel_1=excluded.doel_1,

                doel_2=excluded.doel_2,

                doel_3=excluded.doel_3

            """,

            (datum, doel_1, doel_2, doel_3),

        )

        db.commit()

    return RedirectResponse("/doelen", status_code=303)







@router.post("/doelen/importeren")

async def doelen_importeren(bestand: UploadFile = File(...)):

    if not bestand.filename or not bestand.filename.lower().endswith(".xlsx"):

        return RedirectResponse("/doelen?fout=Gebruik+een+Excelbestand+(.xlsx)", status_code=303)

    try:

        inhoud = await bestand.read()

        wb = load_workbook(BytesIO(inhoud), data_only=True)

        ws = wb.active

        headers = {}

        for cell in ws[1]:

            if cell.value is not None:

                headers[str(cell.value).strip().lower()] = cell.column

        aliases = {

            "datum": ["datum", "date"],

            "doel_1": ["collecte 1", "doel 1", "collectedoel 1"],

            "doel_2": ["collecte 2", "doel 2", "collectedoel 2"],

            "doel_3": ["collecte 3", "doel 3", "collectedoel 3"],

        }

        cols = {}

        for key, names in aliases.items():

            cols[key] = next((headers[n] for n in names if n in headers), None)

        if not cols["datum"] or not cols["doel_1"] or not cols["doel_2"]:

            raise ValueError("Kolommen Datum, Collecte 1 en Collecte 2 zijn verplicht.")



        aantal = 0

        with get_db() as db:

            for r in range(2, ws.max_row + 1):

                raw_datum = ws.cell(r, cols["datum"]).value

                doel1 = ws.cell(r, cols["doel_1"]).value

                doel2 = ws.cell(r, cols["doel_2"]).value

                doel3 = ws.cell(r, cols["doel_3"]).value if cols["doel_3"] else ""

                if raw_datum is None and doel1 is None and doel2 is None:

                    continue

                if hasattr(raw_datum, "date"):

                    datum = raw_datum.date().isoformat()

                elif hasattr(raw_datum, "isoformat") and not isinstance(raw_datum, str):

                    datum = raw_datum.isoformat()

                else:

                    tekst = str(raw_datum).strip()

                    parsed = None

                    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):

                        try:

                            from datetime import datetime

                            parsed = datetime.strptime(tekst, fmt).date().isoformat()

                            break

                        except ValueError:

                            pass

                    if not parsed:

                        raise ValueError(f"Ongeldige datum op rij {r}: {tekst}")

                    datum = parsed

                if not str(doel1 or "").strip() or not str(doel2 or "").strip():

                    raise ValueError(f"Collecte 1 en 2 zijn verplicht op rij {r}.")

                db.execute("""

                    INSERT INTO collectedoelen(datum, doel_1, doel_2, doel_3)

                    VALUES(?,?,?,?)

                    ON CONFLICT(datum) DO UPDATE SET

                    doel_1=excluded.doel_1, doel_2=excluded.doel_2, doel_3=excluded.doel_3

                """, (datum, str(doel1).strip(), str(doel2).strip(), str(doel3 or "").strip()))

                aantal += 1

            db.commit()

        return RedirectResponse(f"/doelen?melding={aantal}+zondagen+geimporteerd", status_code=303)

    except Exception as exc:

        from urllib.parse import quote_plus

        return RedirectResponse(f"/doelen?fout={quote_plus(str(exc))}", status_code=303)





@router.get("/doelen/voorbeeld")

def doelen_voorbeeld():

    wb = Workbook()

    ws = wb.active

    ws.title = "Collectedoelen"

    ws.append(["Datum", "Collecte 1", "Collecte 2", "Collecte 3"])

    ws.append([date(date.today().year, 1, 4), "Kerk", "Diaconie", ""])

    ws.append([date(date.today().year, 1, 11), "Kerk", "Diaconie", "Extra doel"])

    for cell in ws[1]:

        cell.font = Font(bold=True, color="FFFFFF")

        cell.fill = PatternFill("solid", fgColor="166534")

    ws.column_dimensions["A"].width = 16

    for col in ("B", "C", "D"):

        ws.column_dimensions[col].width = 34

    for cell in ws["A"][1:]:

        cell.number_format = "dd-mm-yyyy"

    bio = BytesIO(); wb.save(bio); bio.seek(0)

    return StreamingResponse(bio, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        headers={"Content-Disposition": 'attachment; filename="Voorbeeld_collectedoelen.xlsx"'})



def make_excel(rows):

    wb = Workbook()

    ws = wb.active

    ws.title = "Collectes"

    headers = [

        "Datum", "Collecte", "Doel", "Bonnen blauw (€0,75)", "Bonnen groen (€1,00)",

        "Totaal bonnen", "Totaal muntgeld", "Totaal briefgeld", "Totaal contant", "Totaal collecte", "Extra storting", "Geteld door", "Opmerkingen"

    ]

    ws.append(headers)



    for cell in ws[1]:

        cell.font = Font(bold=True, color="FFFFFF")

        cell.fill = PatternFill("solid", fgColor="166534")

        cell.alignment = Alignment(horizontal="center")



    for row in rows:

        nummers = [1, 2]

        if derde_collecte_actief(row):

            nummers.append(3)

        for nummer in nummers:

            bonnen, muntgeld, briefgeld, contant, totaal = totals(row, nummer)

            ws.append([

                row["datum"], nummer, row[f"doel_{nummer}"],

                row[f"c{nummer}_blauw"], row[f"c{nummer}_groen"],

                bonnen, muntgeld, briefgeld, contant, totaal,

                row["extra_storting"] if nummer == 1 else 0,

                row["geteld_door"], row["opmerkingen"],

            ])



    for row in ws.iter_rows(min_row=2):

        for index in (6, 7, 8, 9, 10, 11):

            row[index - 1].number_format = '€ #,##0.00'



    widths = [14, 10, 32, 20, 20, 17, 17, 18, 18, 18, 17, 24, 42]

    for index, width in enumerate(widths, 1):

        ws.column_dimensions[get_column_letter(index)].width = width



    ws.freeze_panes = "A2"

    ws.auto_filter.ref = ws.dimensions



    bio = BytesIO()

    wb.save(bio)

    bio.seek(0)

    return bio





@router.get("/excel/{datum}")

def excel_dag(datum: str):

    with get_db() as db:

        rows = db.execute("SELECT * FROM tellingen WHERE datum=?", (datum,)).fetchall()

    bio = make_excel(rows)

    return StreamingResponse(

        bio,

        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        headers={"Content-Disposition": f'attachment; filename="Collectetelling_{datum}.xlsx"'},

    )





@router.get("/excel")

def excel_jaar(jaar: int | None = None):

    jaar = jaar or date.today().year

    with get_db() as db:

        rows = db.execute(

            "SELECT * FROM tellingen WHERE datum LIKE ? ORDER BY datum",

            (f"{jaar}%",),

        ).fetchall()

    bio = make_excel(rows)

    return StreamingResponse(

        bio,

        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        headers={"Content-Disposition": f'attachment; filename="Collectes_{jaar}.xlsx"'},

    )
