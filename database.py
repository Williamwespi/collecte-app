import sqlite3
from pathlib import Path


# ============================================================
# PADEN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "collectes.db"

DB_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# DATABASEVERBINDING
# ============================================================

def get_db():

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# VEILIGE DATABASE-MIGRATIE
# ============================================================

def _add_column_if_missing(
    conn,
    table,
    column,
    definition
):

    columns = {
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    }

    if column not in columns:

        conn.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN {column} {definition}
            """
        )


# ============================================================
# DATABASE INITIALISEREN
# ============================================================

def init_db():

    with get_db() as conn:

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS collectedoelen (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                datum TEXT NOT NULL UNIQUE,

                doelcode_1 TEXT NOT NULL DEFAULT '',
                doel_1 TEXT NOT NULL DEFAULT '',

                doelcode_2 TEXT NOT NULL DEFAULT '',
                doel_2 TEXT NOT NULL DEFAULT '',

                doelcode_3 TEXT NOT NULL DEFAULT '',
                doel_3 TEXT NOT NULL DEFAULT ''

            );


            CREATE TABLE IF NOT EXISTS tellingen (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                datum TEXT NOT NULL UNIQUE,


                -- COLLECTEDOELEN

                doelcode_1 TEXT NOT NULL DEFAULT '',
                doel_1 TEXT NOT NULL DEFAULT '',

                doelcode_2 TEXT NOT NULL DEFAULT '',
                doel_2 TEXT NOT NULL DEFAULT '',

                doelcode_3 TEXT NOT NULL DEFAULT '',
                doel_3 TEXT NOT NULL DEFAULT '',


                -- COLLECTE 1

                c1_blauw INTEGER NOT NULL DEFAULT 0,
                c1_groen INTEGER NOT NULL DEFAULT 0,

                c1_munt_5 INTEGER NOT NULL DEFAULT 0,
                c1_munt_10 INTEGER NOT NULL DEFAULT 0,
                c1_munt_20 INTEGER NOT NULL DEFAULT 0,
                c1_munt_50 INTEGER NOT NULL DEFAULT 0,

                c1_overig REAL NOT NULL DEFAULT 0,


                -- COLLECTE 2

                c2_blauw INTEGER NOT NULL DEFAULT 0,
                c2_groen INTEGER NOT NULL DEFAULT 0,

                c2_munt_5 INTEGER NOT NULL DEFAULT 0,
                c2_munt_10 INTEGER NOT NULL DEFAULT 0,
                c2_munt_20 INTEGER NOT NULL DEFAULT 0,
                c2_munt_50 INTEGER NOT NULL DEFAULT 0,

                c2_overig REAL NOT NULL DEFAULT 0,


                -- COLLECTE 3

                c3_blauw INTEGER NOT NULL DEFAULT 0,
                c3_groen INTEGER NOT NULL DEFAULT 0,

                c3_munt_5 INTEGER NOT NULL DEFAULT 0,
                c3_munt_10 INTEGER NOT NULL DEFAULT 0,
                c3_munt_20 INTEGER NOT NULL DEFAULT 0,
                c3_munt_50 INTEGER NOT NULL DEFAULT 0,

                c3_overig REAL NOT NULL DEFAULT 0,


                -- AFRONDING

                extra_storting REAL NOT NULL DEFAULT 0,

                opmerkingen TEXT,

                geteld_door TEXT NOT NULL,

                aangemaakt_op TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP

            );
            """
        )


        # ====================================================
        # MIGRATIE COLLECTEDOELEN
        # ====================================================

        for nummer in (1, 2, 3):

            _add_column_if_missing(
                conn,
                "collectedoelen",
                f"doelcode_{nummer}",
                "TEXT NOT NULL DEFAULT ''"
            )

        _add_column_if_missing(
            conn,
            "collectedoelen",
            "doel_3",
            "TEXT NOT NULL DEFAULT ''"
        )


        # ====================================================
        # MIGRATIE TELLINGEN
        # ====================================================

        for nummer in (1, 2, 3):

            _add_column_if_missing(
                conn,
                "tellingen",
                f"doelcode_{nummer}",
                "TEXT NOT NULL DEFAULT ''"
            )

        _add_column_if_missing(
            conn,
            "tellingen",
            "doel_3",
            "TEXT NOT NULL DEFAULT ''"
        )


        # ====================================================
        # MIGRATIE COLLECTE 3
        # ====================================================

        for field in (
            "blauw",
            "groen",
            "munt_5",
            "munt_10",
            "munt_20",
            "munt_50"
        ):

            _add_column_if_missing(
                conn,
                "tellingen",
                f"c3_{field}",
                "INTEGER NOT NULL DEFAULT 0"
            )


        _add_column_if_missing(
            conn,
            "tellingen",
            "c3_overig",
            "REAL NOT NULL DEFAULT 0"
        )


        conn.commit()


# ============================================================
# BEREKENINGEN
# ============================================================

def bereken_collecte(telling, nummer):

    prefix = f"c{nummer}_"

    blauw = telling[f"{prefix}blauw"] or 0
    groen = telling[f"{prefix}groen"] or 0

    totaal_bonnen = (
        blauw * 0.75
        +
        groen * 1.00
    )

    aantal_5 = telling[f"{prefix}munt_5"] or 0
    aantal_10 = telling[f"{prefix}munt_10"] or 0
    aantal_20 = telling[f"{prefix}munt_20"] or 0
    aantal_50 = telling[f"{prefix}munt_50"] or 0

    totaal_briefgeld = (
        aantal_5 * 5
        +
        aantal_10 * 10
        +
        aantal_20 * 20
        +
        aantal_50 * 50
    )

    totaal_muntgeld = (
        telling[f"{prefix}overig"] or 0
    )

    totaal_contant = (
        totaal_briefgeld
        +
        totaal_muntgeld
    )

    totaal_collecte = (
        totaal_bonnen
        +
        totaal_contant
    )

    return {
        "bonnen": round(totaal_bonnen, 2),
        "briefgeld": round(totaal_briefgeld, 2),
        "muntgeld": round(totaal_muntgeld, 2),
        "contant": round(totaal_contant, 2),
        "totaal": round(totaal_collecte, 2),
    }


# ============================================================
# TOTAAL VAN EEN ZONDAG
# ============================================================

def bereken_zondagtotaal(telling):

    collecte_1 = bereken_collecte(telling, 1)
    collecte_2 = bereken_collecte(telling, 2)
    collecte_3 = bereken_collecte(telling, 3)

    extra_storting = (
        telling["extra_storting"] or 0
    )

    totaal = (
        collecte_1["totaal"]
        +
        collecte_2["totaal"]
        +
        collecte_3["totaal"]
        +
        extra_storting
    )

    return round(totaal, 2)