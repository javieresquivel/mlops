"""
db.py – Utilidades MySQL para el pipeline MLOps.

Proporciona:
  - Engine SQLAlchemy compartido (lazy, pool de conexiones)
  - Context manager de conexión transaccional
  - Inferencia de tipos pandas → MySQL
  - DDL (CREATE TABLE con SHA-256 para dedup)
  - DML (INSERT IGNORE por lotes)
  - Consultas (SELECT como DataFrame, row count, DROP)
"""

import os
import logging
from contextlib import contextmanager

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_integer_dtype,
    is_float_dtype,
    is_datetime64_any_dtype,
)
from sqlalchemy import create_engine, text

logger = logging.getLogger("airflow.task")

# ---------------------------------------------------------------------------
# Conexión
# ---------------------------------------------------------------------------

_DB_USER = os.getenv("DB_USER", "user")
_DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
_DB_HOST = os.getenv("DB_HOST", "mysql_db")
_DB_PORT = os.getenv("DB_PORT", "3306")
_DB_NAME = os.getenv("DB_NAME", "training")

DATABASE_URL = (
    f"mysql+pymysql://{_DB_USER}:{_DB_PASSWORD}@{_DB_HOST}:{_DB_PORT}/{_DB_NAME}"
)

_engine = None


def get_engine():
    """Retorna el engine SQLAlchemy compartido (se crea una sola vez por worker)."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
        )
    return _engine


@contextmanager
def get_connection():
    """
    Context manager que entrega una Connection SQLAlchemy dentro de una transacción.

    Al salir exitosamente se hace commit; en caso de excepción se hace rollback.
    """
    engine = get_engine()
    with engine.begin() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Inferencia de tipos (pandas dtype → MySQL)
# ---------------------------------------------------------------------------

def build_type_map(df: pd.DataFrame) -> dict[str, str]:
    """
    Infiere el tipo MySQL más compacto para cada columna del DataFrame.

    bool      → TINYINT(1) UNSIGNED
    integer   → TINYINT / SMALLINT / MEDIUMINT / INT (UNSIGNED si no negativo)
    float     → FLOAT
    datetime  → DATETIME
    string    → VARCHAR(N) o TEXT según el largo máximo
    """
    type_map: dict[str, str] = {}

    for col in df.columns:
        s = df[col]

        if is_bool_dtype(s):
            type_map[col] = "TINYINT(1) UNSIGNED"

        elif is_integer_dtype(s):
            mn = int(s.min()) if len(s) else 0
            mx = int(s.max()) if len(s) else 0

            if mn >= 0:
                if mx <= 255:
                    type_map[col] = "TINYINT UNSIGNED"
                elif mx <= 65_535:
                    type_map[col] = "SMALLINT UNSIGNED"
                elif mx <= 16_777_215:
                    type_map[col] = "MEDIUMINT UNSIGNED"
                else:
                    type_map[col] = "INT UNSIGNED"
            else:
                if mn >= -128 and mx <= 127:
                    type_map[col] = "TINYINT"
                elif mn >= -32_768 and mx <= 32_767:
                    type_map[col] = "SMALLINT"
                else:
                    type_map[col] = "INT"

        elif is_float_dtype(s):
            type_map[col] = "FLOAT"

        elif is_datetime64_any_dtype(s):
            type_map[col] = "DATETIME"

        else:
            # string / object → VARCHAR o TEXT
            non_null = s.dropna()
            maxlen = int(non_null.astype(str).str.len().max()) if len(non_null) else 0

            if 0 < maxlen <= 255:
                type_map[col] = f"VARCHAR({maxlen})"
            elif maxlen == 0:
                type_map[col] = "VARCHAR(255)"
            else:
                type_map[col] = "TEXT"

    return type_map


def _default_clause(mysql_type: str) -> str:
    """Retorna un DEFAULT clause MySQL adecuado para el tipo dado."""
    t = mysql_type.upper()
    if "TEXT" in t:
        return ""  # TEXT no soporta DEFAULT
    if any(kw in t for kw in ("INT", "FLOAT", "DOUBLE", "DECIMAL")):
        return " DEFAULT 0"
    if "DATETIME" in t:
        return " DEFAULT '1970-01-01 00:00:00'"
    return " DEFAULT ''"


# ---------------------------------------------------------------------------
# DDL (CREATE TABLE con deduplicación por SHA-256)
# ---------------------------------------------------------------------------

def create_table_with_types(table_name: str, df: pd.DataFrame, type_map: dict):
    """
    Crea la tabla si no existe, con columnas tipadas y row_hash para dedup.

    Incluye:
      - Una columna por cada columna del DataFrame, con su tipo MySQL.
      - `id` BIGINT UNSIGNED AUTO_INCREMENT como PK.
      - `row_hash BINARY(32)` generado como SHA-256 de la concatenación
        de todas las columnas, con UNIQUE KEY para deduplicación.
    """
    cols = df.columns.tolist()

    col_defs = []
    for c in cols:
        mtype = (type_map.get(c) or "VARCHAR(255)").upper()
        if "TEXT" in mtype:
            col_defs.append(f"  `{c}` {mtype} NULL")
        else:
            col_defs.append(
                f"  `{c}` {mtype} NOT NULL{_default_clause(mtype)}"
            )

    concat = "CONCAT_WS('|', " + ", ".join(f"COALESCE(`{c}`,'')" for c in cols) + ")"

    sql = f"""
    CREATE TABLE IF NOT EXISTS `{table_name}` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      {', '.join(col_defs)},
      `row_hash` BINARY(32)
        GENERATED ALWAYS AS (UNHEX(SHA2({concat}, 256))) STORED,
      UNIQUE KEY `uniq_row_hash` (`row_hash`),
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
    """

    with get_connection() as conn:
        conn.execute(text(sql))

    logger.info("Tabla `%s` lista (%d columnas).", table_name, len(cols))


# ---------------------------------------------------------------------------
# DML (INSERT IGNORE por lotes)
# ---------------------------------------------------------------------------

def insert_data(table_name: str, df: pd.DataFrame, batch_size: int = 5000) -> int:
    """
    Inserta filas del DataFrame en la tabla, ignorando duplicados.

    Los duplicados se detectan por la UNIQUE KEY sobre `row_hash`.
    Retorna la cantidad de filas realmente insertadas.
    """
    if df.empty:
        logger.warning("insert_data: DataFrame vacío.")
        return 0

    # Descubre las columnas reales de la tabla
    with get_connection() as conn:
        result = conn.execute(text(f"SELECT * FROM `{table_name}` LIMIT 0"))
        table_cols = list(result.keys())

    insert_cols = [
        c for c in table_cols
        if c in df.columns and c not in ("id", "row_hash")
    ]
    if not insert_cols:
        logger.warning("insert_data: no hay columnas coincidentes.")
        return 0

    # Prepara datos: alinea columnas, reemplaza NaN por None
    data = df.reindex(columns=insert_cols).copy()
    data = data.astype(object).where(pd.notna(data), None)

    cols_sql = ", ".join(f"`{c}`" for c in insert_cols)
    placeholders = ", ".join(f":{c}" for c in insert_cols)
    stmt = text(
        f"INSERT IGNORE INTO `{table_name}` ({cols_sql}) VALUES ({placeholders})"
    )

    rows = data.to_dict(orient="records")
    total = 0

    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        with get_connection() as conn:
            total += conn.execute(stmt, chunk).rowcount

    logger.info("Insertadas %d / %d filas en `%s`.", total, len(df), table_name)
    return total


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def get_dataframe(table_name: str) -> pd.DataFrame:
    """Lee toda la tabla como DataFrame, excluyendo columnas id y row_hash."""
    with get_connection() as conn:
        result = conn.execute(text(f"SELECT * FROM `{table_name}`"))
        df = pd.DataFrame(result.fetchall(), columns=list(result.keys()))

    for drop_col in ("id", "row_hash"):
        if drop_col in df.columns:
            df.drop(columns=drop_col, inplace=True)

    return df


def get_dataframe_where(table_name: str, column: str, value) -> pd.DataFrame:
    """Lee filas de la tabla filtradas por columna = valor."""
    with get_connection() as conn:
        result = conn.execute(
            text(f"SELECT * FROM `{table_name}` WHERE `{column}` = :val"),
            {"val": value},
        )
        df = pd.DataFrame(result.fetchall(), columns=list(result.keys()))
    for drop_col in ("id", "row_hash"):
        if drop_col in df.columns:
            df.drop(columns=drop_col, inplace=True)
    return df


def delete_table(table_name: str):
    """Elimina la tabla si existe."""
    with get_connection() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
    logger.info("Tabla `%s` eliminada.", table_name)


def row_count(table_name: str) -> int:
    """Retorna la cantidad total de filas en la tabla."""
    with get_connection() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
        return result.scalar()
