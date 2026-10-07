from datetime import date, datetime
from io import BytesIO
from urllib.parse import quote_plus

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from database import get_db
from auth import (
    configured_password_hash,
    configured_username,
    verify_password,
)


router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ============================================================
# EURO
# ============================================================

def euro(value):

    return (
        f"€ {float(value or 0):,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


templates.env.filters["euro"] = euro


# ============================================================
# TOTALEN
# ============================================================

def totals(row, nummer):

    bonnen = (
        (row[f"c{nummer}_blauw"] or 0) * 0.75
        +
        (row[f"c{nummer}_groen"] or 0) * 1.00
    )

    briefgeld = (
        (row[f"c{nummer}_munt_5"] or 0) * 5
        +
        (row[f"c{nummer}_munt_10"] or 0) * 10
        +
        (row[f"c{nummer}_munt_20"] or 0) * 20
        +
        (row[f"c{nummer}_munt_50"] or 0) * 50
    )

    muntgeld = (
        row[f"c{nummer}_overig"] or 0
    )

    contant = (
        briefgeld
        +
        muntgeld
    )

    totaal = (
        bonnen
        +
        contant
    )

    return (
        bonnen,
        muntgeld,
        briefgeld,
        contant,
        totaal,
    )


def derde_collecte_actief(row):

    return bool(
        str(row["doel_3"] or "").strip()
    )


# ============================================================
# LOGIN
# ============================================================

@router.get(
    "/login",
    response_class=HTMLResponse
)
def login_page(
    request: Request,
    fout: str | None = None,
):

    if request.session.get("logged_in"):

        return RedirectResponse(
            "/",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "fout": fout,
        },
    )


@router.post("/login")
def login(
    request: Request,
    gebruikersnaam: str = Form(...),
    wachtwoord: str = Form(...),
):

    password_hash = (
        configured_password_hash()
    )

    geldig = (
        bool(password_hash)
        and gebruikersnaam.strip()
        == configured_username()
        and verify_password(
            wachtwoord,
            password_hash,
        )
    )

    if not geldig:

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "fout": (
                    "Gebruikersnaam of wachtwoord "
                    "is niet juist."
                ),
            },
            status_code=401,
        )

    request.session.clear()

    request.session["logged_in"] = True
    request.session["username"] = (
        gebruikersnaam.strip()
    )

    return RedirectResponse(
        "/",
        status_code=303,
    )


@router.post("/logout")
def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        "/login",
        status_code=303,
    )


# ============================================================
# HOME
# ============================================================

@router.get(
    "/",
    response_class=HTMLResponse
)
def home(request: Request):

    vandaag = date.today().isoformat()

    with get_db() as db:

        doel = db.execute(
            """
            SELECT *
            FROM collectedoelen
            WHERE datum=?
            """,
            (vandaag,),
        ).fetchone()

        recent = db.execute(
            """
            SELECT *
            FROM tellingen
            ORDER BY datum DESC
            LIMIT 8
            """
        ).fetchall()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "vandaag": vandaag,
            "doel": doel,
            "recent": recent,
        },
    )


# ============================================================
# TELLEN
# ============================================================

@router.get(
    "/tellen",
    response_class=HTMLResponse
)
def tellen(
    request: Request,
    datum: str | None = None,
):

    datum = (
        datum
        or date.today().isoformat()
    )

    with get_db() as db:

        doel = db.execute(
            """
            SELECT *
            FROM collectedoelen
            WHERE datum=?
            """,
            (datum,),
        ).fetchone()

        bestaand = db.execute(
            """
            SELECT *
            FROM tellingen
            WHERE datum=?
            """,
            (datum,),
        ).fetchone()

    return templates.TemplateResponse(
        request=request,
        name="tellen.html",
        context={
            "datum": datum,
            "doel": doel,
            "bestaand": bestaand,
        },
    )


@router.post("/tellen")
def telling_opslaan(

    datum: str = Form(...),

    doelcode_1: str = Form(""),
    doel_1: str = Form(...),

    doelcode_2: str = Form(""),
    doel_2: str = Form(...),

    doelcode_3: str = Form(""),
    doel_3: str = Form(""),

    c1_blauw: int = Form(0),
    c1_groen: int = Form(0),
    c1_munt_5: int = Form(0),
    c1_munt_10: int = Form(0),
    c1_munt_20: int = Form(0),
    c1_munt_50: int = Form(0),
    c1_overig: float = Form(0),

    c2_blauw: int = Form(0),
    c2_groen: int = Form(0),
    c2_munt_5: int = Form(0),
    c2_munt_10: int = Form(0),
    c2_munt_20: int = Form(0),
    c2_munt_50: int = Form(0),
    c2_overig: float = Form(0),

    c3_blauw: int = Form(0),
    c3_groen: int = Form(0),
    c3_munt_5: int = Form(0),
    c3_munt_10: int = Form(0),
    c3_munt_20: int = Form(0),
    c3_munt_50: int = Form(0),
    c3_overig: float = Form(0),

    extra_storting: float = Form(0),
    opmerkingen: str = Form(""),
    geteld_door: str = Form(...),
):

    data = locals().copy()

    columns = list(data.keys())

    placeholders = ",".join(
        "?"
        for _ in columns
    )

    updates = ",".join(
        f"{column}=excluded.{column}"
        for column in columns
        if column != "datum"
    )

    with get_db() as db:

        db.execute(
            f"""
            INSERT INTO tellingen (
                {','.join(columns)}
            )
            VALUES ({placeholders})

            ON CONFLICT(datum)
            DO UPDATE SET
                {updates}
            """,
            tuple(
                data[column]
                for column in columns
            ),
        )

        db.commit()

    return RedirectResponse(
        f"/controle/{datum}",
        status_code=303,
    )


# ============================================================
# CONTROLE
# ============================================================

@router.get(
    "/controle/{datum}",
    response_class=HTMLResponse
)
def controle(
    request: Request,
    datum: str,
):

    with get_db() as db:

        row = db.execute(
            """
            SELECT *
            FROM tellingen
            WHERE datum=?
            """,
            (datum,),
        ).fetchone()

    if not row:

        return RedirectResponse(
            "/",
            status_code=303,
        )

    t1 = totals(row, 1)
    t2 = totals(row, 2)
    t3 = totals(row, 3)

    heeft_derde = (
        derde_collecte_actief(row)
    )

    totaal = (
        t1[4]
        +
        t2[4]
        +
        (
            t3[4]
            if heeft_derde
            else 0
        )
        +
        (row["extra_storting"] or 0)
    )

    return templates.TemplateResponse(
        request=request,
        name="controle.html",
        context={
            "r": row,
            "t1": t1,
            "t2": t2,
            "t3": t3,
            "heeft_derde": heeft_derde,
            "totaal": totaal,
        },
    )


# ============================================================
# COLLECTEDOELEN
# ============================================================

@router.get(
    "/doelen",
    response_class=HTMLResponse
)
def doelen(
    request: Request,
    melding: str | None = None,
    fout: str | None = None,
):

    with get_db() as db:

        rows = db.execute(
            """
            SELECT *
            FROM collectedoelen
            ORDER BY datum DESC
            """
        ).fetchall()

    return templates.TemplateResponse(
        request=request,
        name="doelen.html",
        context={
            "rows": rows,
            "melding": melding,
            "fout": fout,
        },
    )


# ============================================================
# COLLECTEDOEL HANDMATIG OPSLAAN
# ============================================================

@router.post("/doelen")
def doel_opslaan(

    datum: str = Form(...),

    doelcode_1: str = Form(...),
    doel_1: str = Form(...),

    doelcode_2: str = Form(...),
    doel_2: str = Form(...),

    doelcode_3: str = Form(""),
    doel_3: str = Form(""),
):

    with get_db() as db:

        db.execute(
            """
            INSERT INTO collectedoelen(
                datum,
                doelcode_1,
                doel_1,
                doelcode_2,
                doel_2,
                doelcode_3,
                doel_3
            )
            VALUES(?,?,?,?,?,?,?)

            ON CONFLICT(datum)
            DO UPDATE SET
                doelcode_1=excluded.doelcode_1,
                doel_1=excluded.doel_1,
                doelcode_2=excluded.doelcode_2,
                doel_2=excluded.doel_2,
                doelcode_3=excluded.doelcode_3,
                doel_3=excluded.doel_3
            """,
            (
                datum,

                doelcode_1.strip(),
                doel_1.strip(),

                doelcode_2.strip(),
                doel_2.strip(),

                doelcode_3.strip(),
                doel_3.strip(),
            ),
        )

        db.commit()

    return RedirectResponse(
        "/doelen",
        status_code=303,
    )


# ============================================================
# DATUM UIT EXCEL
# ============================================================

def excel_datum_naar_iso(
    raw_datum,
    rij,
):

    if raw_datum is None:

        raise ValueError(
            f"Datum ontbreekt op rij {rij}."
        )

    if isinstance(
        raw_datum,
        datetime
    ):

        return (
            raw_datum
            .date()
            .isoformat()
        )

    if isinstance(
        raw_datum,
        date
    ):

        return raw_datum.isoformat()

    tekst = str(
        raw_datum
    ).strip()

    for fmt in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ):

        try:

            return (
                datetime.strptime(
                    tekst,
                    fmt,
                )
                .date()
                .isoformat()
            )

        except ValueError:

            pass

    raise ValueError(
        f"Ongeldige datum op rij {rij}: {tekst}"
    )


# ============================================================
# EXCELWAARDE NAAR TEKST
# ============================================================

def excel_tekst(value):

    if value is None:

        return ""

    # Voorkomt bijvoorbeeld 101.0
    # wanneer Excel een geheel getal als float aanlevert.

    if (
        isinstance(value, float)
        and value.is_integer()
    ):

        return str(int(value))

    return str(value).strip()


# ============================================================
# COLLECTEDOELEN IMPORTEREN
# ============================================================

@router.post("/doelen/importeren")
async def doelen_importeren(
    bestand: UploadFile = File(...),
):

    if (
        not bestand.filename
        or not bestand.filename
        .lower()
        .endswith(".xlsx")
    ):

        return RedirectResponse(
            (
                "/doelen?"
                "fout=Gebruik+een+"
                "Excelbestand+(.xlsx)"
            ),
            status_code=303,
        )

    try:

        inhoud = await bestand.read()

        wb = load_workbook(
            BytesIO(inhoud),
            data_only=True,
        )

        ws = wb.active

        # ----------------------------------------------------
        # We lezen bewust op kolompositie.
        #
        # A = Datum
        # B = Doel
        # C = Collecte 1
        # D = Doel
        # E = Collecte 2
        # F = Doel
        # G = Collecte 3
        #
        # Dit is nodig omdat "Doel" drie keer voorkomt.
        # ----------------------------------------------------

        verwachte_headers = [
            "datum",
            "doel",
            "collecte 1",
            "doel",
            "collecte 2",
            "doel",
            "collecte 3",
        ]

        werkelijke_headers = []

        for kolom in range(1, 8):

            waarde = ws.cell(
                1,
                kolom,
            ).value

            werkelijke_headers.append(
                str(
                    waarde or ""
                )
                .strip()
                .lower()
            )

        if (
            werkelijke_headers
            != verwachte_headers
        ):

            raise ValueError(
                "De eerste rij moet exact zijn: "
                "Datum | Doel | Collecte 1 | "
                "Doel | Collecte 2 | "
                "Doel | Collecte 3"
            )

        aantal = 0

        with get_db() as db:

            for rij in range(
                2,
                ws.max_row + 1,
            ):

                raw_datum = (
                    ws.cell(rij, 1).value
                )

                doelcode_1 = excel_tekst(
                    ws.cell(rij, 2).value
                )

                doel_1 = excel_tekst(
                    ws.cell(rij, 3).value
                )

                doelcode_2 = excel_tekst(
                    ws.cell(rij, 4).value
                )

                doel_2 = excel_tekst(
                    ws.cell(rij, 5).value
                )

                doelcode_3 = excel_tekst(
                    ws.cell(rij, 6).value
                )

                doel_3 = excel_tekst(
                    ws.cell(rij, 7).value
                )

                # Helemaal lege regel overslaan

                if (
                    raw_datum is None
                    and not doelcode_1
                    and not doel_1
                    and not doelcode_2
                    and not doel_2
                    and not doelcode_3
                    and not doel_3
                ):

                    continue

                datum = excel_datum_naar_iso(
                    raw_datum,
                    rij,
                )

                if not doelcode_1:

                    raise ValueError(
                        f"Doel voor collecte 1 "
                        f"ontbreekt op rij {rij}."
                    )

                if not doel_1:

                    raise ValueError(
                        f"Collecte 1 ontbreekt "
                        f"op rij {rij}."
                    )

                if not doelcode_2:

                    raise ValueError(
                        f"Doel voor collecte 2 "
                        f"ontbreekt op rij {rij}."
                    )

                if not doel_2:

                    raise ValueError(
                        f"Collecte 2 ontbreekt "
                        f"op rij {rij}."
                    )

                # Collecte 3 is optioneel.
                # Als één van beide is ingevuld,
                # moeten beide ingevuld zijn.

                if (
                    bool(doelcode_3)
                    != bool(doel_3)
                ):

                    raise ValueError(
                        f"Vul op rij {rij} voor "
                        f"collecte 3 zowel Doel "
                        f"als Collecte 3 in."
                    )

                db.execute(
                    """
                    INSERT INTO collectedoelen(
                        datum,
                        doelcode_1,
                        doel_1,
                        doelcode_2,
                        doel_2,
                        doelcode_3,
                        doel_3
                    )
                    VALUES(?,?,?,?,?,?,?)

                    ON CONFLICT(datum)
                    DO UPDATE SET
                        doelcode_1=excluded.doelcode_1,
                        doel_1=excluded.doel_1,
                        doelcode_2=excluded.doelcode_2,
                        doel_2=excluded.doel_2,
                        doelcode_3=excluded.doelcode_3,
                        doel_3=excluded.doel_3
                    """,
                    (
                        datum,
                        doelcode_1,
                        doel_1,
                        doelcode_2,
                        doel_2,
                        doelcode_3,
                        doel_3,
                    ),
                )

                aantal += 1

            db.commit()

        return RedirectResponse(
            (
                "/doelen?"
                f"melding={aantal}+"
                "zondagen+geimporteerd"
            ),
            status_code=303,
        )

    except Exception as exc:

        return RedirectResponse(
            (
                "/doelen?fout="
                f"{quote_plus(str(exc))}"
            ),
            status_code=303,
        )


# ============================================================
# VOORBEELD EXCEL COLLECTEDOELEN
# ============================================================

@router.get("/doelen/voorbeeld")
def doelen_voorbeeld():

    wb = Workbook()

    ws = wb.active
    ws.title = "Collectedoelen"

    ws.append(
        [
            "Datum",
            "Doel",
            "Collecte 1",
            "Doel",
            "Collecte 2",
            "Doel",
            "Collecte 3",
        ]
    )

    jaar = date.today().year

    ws.append(
        [
            date(jaar, 1, 4),
            "101",
            "Kerk",
            "201",
            "Diaconie",
            "",
            "",
        ]
    )

    ws.append(
        [
            date(jaar, 1, 11),
            "101",
            "Kerk",
            "201",
            "Diaconie",
            "301",
            "Extra doel",
        ]
    )

    for cell in ws[1]:

        cell.font = Font(
            bold=True,
            color="FFFFFF",
        )

        cell.fill = PatternFill(
            "solid",
            fgColor="166534",
        )

    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 34
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 34
    ws.column_dimensions["F"].width = 14
    ws.column_dimensions["G"].width = 34

    for cell in ws["A"][1:]:

        cell.number_format = (
            "dd-mm-yyyy"
        )

    bio = BytesIO()

    wb.save(bio)
    bio.seek(0)

    return StreamingResponse(
        bio,
        media_type=(
            "application/vnd."
            "openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                'attachment; filename='
                '"Voorbeeld_collectedoelen.xlsx"'
            )
        },
    )


# ============================================================
# EXCEL MAKEN
# ============================================================

def make_excel(rows):

    wb = Workbook()

    ws = wb.active
    ws.title = "Collectes"

    headers = [
        "Datum",
        "Collecte",
        "Doel",
        "Omschrijving",
        "Bonnen blauw (€0,75)",
        "Bonnen groen (€1,00)",
        "Totaal bonnen",
        "Totaal muntgeld",
        "Totaal briefgeld",
        "Totaal contant",
        "Totaal collecte",
        "Extra storting",
        "Geteld door",
        "Opmerkingen",
    ]

    ws.append(headers)

    for cell in ws[1]:

        cell.font = Font(
            bold=True,
            color="FFFFFF",
        )

        cell.fill = PatternFill(
            "solid",
            fgColor="166534",
        )

        cell.alignment = Alignment(
            horizontal="center"
        )

    for row in rows:

        nummers = [1, 2]

        if derde_collecte_actief(row):

            nummers.append(3)

        for nummer in nummers:

            (
                bonnen,
                muntgeld,
                briefgeld,
                contant,
                totaal,
            ) = totals(
                row,
                nummer,
            )

            ws.append(
                [
                    row["datum"],

                    nummer,

                    row[
                        f"doelcode_{nummer}"
                    ],

                    row[
                        f"doel_{nummer}"
                    ],

                    row[
                        f"c{nummer}_blauw"
                    ],

                    row[
                        f"c{nummer}_groen"
                    ],

                    bonnen,
                    muntgeld,
                    briefgeld,
                    contant,
                    totaal,

                    (
                        row["extra_storting"]
                        if nummer == 1
                        else 0
                    ),

                    row["geteld_door"],

                    row["opmerkingen"],
                ]
            )

    # Geldkolommen G t/m L

    for excel_row in ws.iter_rows(
        min_row=2
    ):

        for index in (
            7,
            8,
            9,
            10,
            11,
            12,
        ):

            excel_row[
                index - 1
            ].number_format = (
                "€ #,##0.00"
            )

    widths = [
        14,
        10,
        14,
        32,
        20,
        20,
        17,
        17,
        18,
        18,
        18,
        17,
        24,
        42,
    ]

    for index, width in enumerate(
        widths,
        1,
    ):

        ws.column_dimensions[
            get_column_letter(index)
        ].width = width

    ws.freeze_panes = "A2"

    ws.auto_filter.ref = (
        ws.dimensions
    )

    bio = BytesIO()

    wb.save(bio)
    bio.seek(0)

    return bio


# ============================================================
# EXCEL PER ZONDAG
# ============================================================

@router.get("/excel/{datum}")
def excel_dag(datum: str):

    with get_db() as db:

        rows = db.execute(
            """
            SELECT *
            FROM tellingen
            WHERE datum=?
            """,
            (datum,),
        ).fetchall()

    bio = make_excel(rows)

    return StreamingResponse(
        bio,
        media_type=(
            "application/vnd."
            "openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="Collectetelling_{datum}.xlsx"'
            )
        },
    )


# ============================================================
# EXCEL JAAROVERZICHT
# ============================================================

@router.get("/excel")
def excel_jaar(
    jaar: int | None = None,
):

    jaar = (
        jaar
        or date.today().year
    )

    with get_db() as db:

        rows = db.execute(
            """
            SELECT *
            FROM tellingen
            WHERE datum LIKE ?
            ORDER BY datum
            """,
            (f"{jaar}%",),
        ).fetchall()

    bio = make_excel(rows)

    return StreamingResponse(
        bio,
        media_type=(
            "application/vnd."
            "openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="Collectes_{jaar}.xlsx"'
            )
        },
    )