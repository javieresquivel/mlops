"""
data_pipeline.py – Tareas del pipeline de ingesta para el DAG de Airflow.

Cada función pública es un PythonOperator que recibe **context de Airflow.
"""

import os
import math
import logging

import numpy as np
import pandas as pd
import requests
from sqlalchemy import text

from training_app.db import (
    build_type_map,
    create_table_with_types,
    get_connection,
    get_dataframe,
    insert_data,
)

logger = logging.getLogger("airflow.task")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

DATA_API_URL = os.getenv("DATA_API_URL", "http://data-api:80")
RAW_TABLE_NAME = "raw_data"

COLUMNS = [
    "brokered_by", "status", "price", "bed", "bath",
    "acre_lot", "street", "city", "state",
    "zip_code", "house_size", "prev_sold_date",
]

TYPE_MAP = {
    "brokered_by":    "FLOAT",
    "status":         "VARCHAR(50)",
    "price":          "FLOAT",
    "bed":            "FLOAT",
    "bath":           "FLOAT",
    "acre_lot":       "FLOAT",
    "street":         "FLOAT",
    "city":           "VARCHAR(100)",
    "state":          "VARCHAR(100)",
    "zip_code":       "FLOAT",
    "house_size":     "FLOAT",
    "prev_sold_date": "VARCHAR(20)",
}

DEFAULT_TYPES = {
    "brokered_by": "float", "status": "object", "price": "float",
    "bed": "float", "bath": "float", "acre_lot": "float",
    "street": "float", "city": "object", "state": "object",
    "zip_code": "float", "house_size": "float", "prev_sold_date": "object",
}

CATEGORICAL_COLUMNS = ["status", "city", "state", "prev_sold_date"]
NUMERICAL_COLUMNS = ["brokered_by", "price", "bed", "bath", "acre_lot", "street", "zip_code", "house_size"]

CATEGORIES_TABLE = "known_categories"
PSI_THRESHOLD = 0.1


# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------

def _pull_batch(context):
    """Obtiene el batch desde XCom y lo normaliza a lista de dicts."""
    batch = context["ti"].xcom_pull(key="raw_batch", task_ids="fetch_batch_from_api")
    if batch is None:
        raise RuntimeError("No hay batch en XCom.")
    return batch if isinstance(batch, list) else [batch]


# ---------------------------------------------------------------------------
# Task 1: Obtener batch desde data-api
# ---------------------------------------------------------------------------

def fetch_batch(**context):
    """Obtiene un lote de registros desde la API externa."""
    group = (context.get("dag_run").conf or {}).get("group_number", 1)

    logger.info("Obteniendo batch group_number=%s", group)
    resp = requests.get(f"{DATA_API_URL}/data", params={"group_number": group}, timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(f"data-api respondió HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    records = data if isinstance(data, list) else data.get("data", data)

    logger.info("Batch recibido: %d registros (group=%s).", len(records) if isinstance(records, list) else 1, group)

    context["ti"].xcom_push(key="raw_batch", value=records)
    context["ti"].xcom_push(key="group_number", value=group)


# ---------------------------------------------------------------------------
# Task 2: Almacenar batch en MySQL
# ---------------------------------------------------------------------------

def store_raw_batch(**context):
    """Persiste el batch en la tabla raw_data con deduplicación por SHA-256."""
    df = pd.DataFrame(_pull_batch(context))
    logger.info("DataFrame shape: %s", df.shape)

    cols = [c for c in COLUMNS if c in df.columns]
    df = df[cols]
    type_map = {k: v for k, v in TYPE_MAP.items() if k in cols}

    create_table_with_types(RAW_TABLE_NAME, df, type_map)
    insertadas = insert_data(RAW_TABLE_NAME, df)

    logger.info("Almacenadas %d filas nuevas en `%s`.", insertadas, RAW_TABLE_NAME)


# ---------------------------------------------------------------------------
# Task 3: Validar esquema
# ---------------------------------------------------------------------------

def validate_schema(**context):
    """Valida columnas requeridas y tipos de datos del batch."""
    df = pd.DataFrame(_pull_batch(context))

    if df.empty:
        raise RuntimeError("Batch vacío.")

    faltantes = [c for c in COLUMNS if c not in df.columns]
    if faltantes:
        raise RuntimeError(f"Columnas faltantes: {faltantes}")

    unexpected = [c for c in df.columns if c not in COLUMNS]
    tipos_invalidos = {}

    for col, tipo_esperado in DEFAULT_TYPES.items():
        if col in df.columns and tipo_esperado not in str(df[col].dtype):
            tipos_invalidos[col] = {"esperado": tipo_esperado, "recibido": str(df[col].dtype)}

    if tipos_invalidos:
        raise RuntimeError(f"Tipos inválidos: {tipos_invalidos}")

    report = {
        "status": "success",
        "records": len(df),
        "missing_columns": faltantes,
        "unexpected_columns": unexpected,
        "invalid_types": tipos_invalidos,
    }

    logger.info("Esquema válido: %s", report)
    context["ti"].xcom_push(key="schema_validation_report", value=report)


# ---------------------------------------------------------------------------
# Task 4: Validar calidad de datos
# ---------------------------------------------------------------------------

def validate_data_quality(**context):
    """Valida nulos, duplicados, rangos, consistencia y valores categóricos."""
    df = pd.DataFrame(_pull_batch(context))
    logger.info("Validando calidad, shape=%s", df.shape)

    # Nulos en columnas críticas
    null_pct = (df.isnull().sum() / len(df) * 100).round(2).to_dict()
    criticas = ["price", "bed", "bath", "city", "state"]
    nulls_criticos = {c: p for c, p in null_pct.items() if c in criticas and p > 20}

    # Duplicados
    duplicados = int(df.duplicated().sum())

    # Rangos numéricos
    rangos = {
        "price": (0, 100_000_000), "bed": (0, 50), "bath": (0, 50),
        "acre_lot": (0, 100_000), "house_size": (0, 1_000_000),
    }
    fuera_rango = {}
    for col, (min_v, max_v) in rangos.items():
        if col in df.columns:
            malas = df[(df[col] < min_v) | (df[col] > max_v)]
            if not malas.empty:
                fuera_rango[col] = len(malas)

    # Consistencia baños vs cuartos
    consistencia = {}
    if "bed" in df.columns and "bath" in df.columns:
        malos = df[df["bath"] > (df["bed"] * 3)]
        if not malos.empty:
            consistencia["bath_vs_bed"] = len(malos)

    # Categóricas inválidas
    status_invalidos = []
    if "status" in df.columns:
        validos = {"for_sale", "sold", "pending"}
        status_invalidos = df[~df["status"].isin(validos)]["status"].dropna().unique().tolist()

    report = {
        "status": "success",
        "records": len(df),
        "duplicate_rows": duplicados,
        "critical_nulls": nulls_criticos,
        "invalid_ranges": fuera_rango,
        "consistency_issues": consistencia,
        "invalid_status_values": status_invalidos,
    }

    if nulls_criticos or fuera_rango:
        logger.warning("Problemas de calidad: %s", report)
    else:
        logger.info("Calidad válida: %s", report)

    context["ti"].xcom_push(key="data_quality_report", value=report)


# ---------------------------------------------------------------------------
# Task 5: Detectar categorías nuevas
# ---------------------------------------------------------------------------

def detect_new_categories(**context):
    """Identifica y registra categorías no vistas antes en columnas categóricas."""
    df = pd.DataFrame(_pull_batch(context))
    _crear_tabla_categorias()

    nuevas = {}

    for col in CATEGORICAL_COLUMNS:
        if col not in df.columns:
            continue

        batch_vals = set(df[col].dropna().unique())
        conocidas = _categorias_conocidas(col)
        nuevas_vals = batch_vals - conocidas

        if nuevas_vals:
            nuevas[col] = sorted(str(v) for v in nuevas_vals)
            _insertar_categorias(col, nuevas_vals)

    report = {
        "status": "success" if not nuevas else "new_categories_found",
        "new_categories": nuevas,
        "categorical_columns_checked": [c for c in CATEGORICAL_COLUMNS if c in df.columns],
    }

    if nuevas:
        logger.warning("Categorías nuevas detectadas: %s", nuevas)
    else:
        logger.info("Sin categorías nuevas.")

    context["ti"].xcom_push(key="new_categories_report", value=report)


def _crear_tabla_categorias():
    """Crea la tabla known_categories si no existe."""
    sql = f"""
    CREATE TABLE IF NOT EXISTS `{CATEGORIES_TABLE}` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `column_name` VARCHAR(100) NOT NULL,
      `category_value` VARCHAR(255) NOT NULL,
      `first_seen_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uniq_col_val` (`column_name`, `category_value`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with get_connection() as conn:
        conn.execute(text(sql))


def _categorias_conocidas(col: str) -> set:
    """Retorna los valores conocidos para una columna categórica."""
    sql = text(f"SELECT DISTINCT `category_value` FROM `{CATEGORIES_TABLE}` WHERE `column_name` = :col")
    with get_connection() as conn:
        return {row[0] for row in conn.execute(sql, {"col": col})}


def _insertar_categorias(col: str, valores: set):
    """Inserta nuevas categorías en la tabla known_categories."""
    sql = text(f"INSERT IGNORE INTO `{CATEGORIES_TABLE}` (`column_name`, `category_value`) VALUES (:col, :val)")
    with get_connection() as conn:
        for v in valores:
            conn.execute(sql, {"col": col, "val": str(v)})


# ---------------------------------------------------------------------------
# Task 6: Detectar data drift (PSI)
# ---------------------------------------------------------------------------

def detect_data_drift(**context):
    """Compara distribución del batch vs histórico usando Population Stability Index."""
    df_batch = pd.DataFrame(_pull_batch(context))
    df_ref = get_dataframe(RAW_TABLE_NAME)

    if df_ref.empty:
        logger.warning("Sin datos históricos para drift.")
        context["ti"].xcom_push(key="data_drift_report", value={
            "status": "no_reference_data", "drift_detected": False,
        })
        return

    drift = {}

    for col in NUMERICAL_COLUMNS:
        if col not in df_batch.columns or col not in df_ref.columns:
            continue
        ref = df_ref[col].dropna()
        act = df_batch[col].dropna()
        if len(ref) < 10 or len(act) < 5:
            continue
        psi = _psi_numerico(ref, act)
        if psi > PSI_THRESHOLD:
            drift[col] = {
                "type": "numerical", "psi": round(psi, 4), "drift_detected": True,
                "ref_mean": round(float(ref.mean()), 4), "batch_mean": round(float(act.mean()), 4),
            }

    for col in CATEGORICAL_COLUMNS:
        if col not in df_batch.columns or col not in df_ref.columns:
            continue
        ref = df_ref[col].dropna()
        act = df_batch[col].dropna()
        if len(ref) < 10 or len(act) < 5:
            continue
        psi = _psi_categorico(ref, act)
        if psi > PSI_THRESHOLD:
            drift[col] = {"type": "categorical", "psi": round(psi, 4), "drift_detected": True}

    report = {
        "status": "drift_detected" if drift else "no_drift",
        "drift_detected": bool(drift),
        "drift_details": drift,
        "batch_size": len(df_batch),
        "reference_size": len(df_ref),
    }

    if drift:
        logger.warning("Drift detectado en: %s", list(drift.keys()))
    else:
        logger.info("Sin drift significativo.")
    context["ti"].xcom_push(key="data_drift_report", value=report)


def _psi_numerico(ref: pd.Series, act: pd.Series, bins: int = 10) -> float:
    """PSI para variable numérica usando bins por percentiles de referencia."""
    if ref.nunique() < 2:
        return 0.0

    if ref.nunique() < bins:
        edges = sorted(ref.unique())
    else:
        pct = np.linspace(0, 100, bins + 1)[1:-1]
        edges = sorted(np.percentile(ref, pct))
    edges = [float("-inf")] + list(edges) + [float("inf")]

    n_ref, n_act = len(ref), len(act)
    psi = 0.0

    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i == len(edges) - 2:
            mask_ref = (ref >= lo) & (ref <= hi)
            mask_act = (act >= lo) & (act <= hi)
        else:
            mask_ref = (ref >= lo) & (ref < hi)
            mask_act = (act >= lo) & (act < hi)

        p_ref = max(mask_ref.sum() / n_ref, 1e-6)
        p_act = max(mask_act.sum() / n_act, 1e-6)
        psi += (p_ref - p_act) * math.log(p_ref / p_act)

    return psi


def _psi_categorico(ref: pd.Series, act: pd.Series) -> float:
    """PSI para variable categórica comparando proporciones por categoría."""
    cats = set(ref.unique()) | set(act.unique())
    n_ref, n_act = len(ref), len(act)
    psi = 0.0

    for c in cats:
        p_ref = max((ref == c).sum() / n_ref, 1e-6)
        p_act = max((act == c).sum() / n_act, 1e-6)
        psi += (p_ref - p_act) * math.log(p_ref / p_act)

    return psi
