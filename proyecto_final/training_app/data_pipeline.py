"""
data_pipeline.py – Tareas del pipeline de ingesta para el DAG de Airflow.

Cada función pública es un PythonOperator que recibe **context de Airflow.
"""

import os
import math
import logging
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import requests
import mlflow
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from airflow.exceptions import AirflowSkipException
from sqlalchemy import text

from training_app.db import (
    build_type_map,
    create_table_with_types,
    get_connection,
    get_dataframe,
    get_dataframe_where,
    insert_data,
)

logger = logging.getLogger("airflow.task")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

DATA_API_URL = os.getenv("DATA_API_URL", "http://data-api:80")
RAW_TABLE_NAME = "raw_data"
BATCH_LOG_TABLE = "batch_log"
HISTORY_TABLE = "training_history"
DEBUG_LIMIT = int(os.getenv("DEBUG_LIMIT", "2000"))

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
    "batch_group":    "INT UNSIGNED",
    "ingested_at":    "DATETIME",
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
CLEAN_TABLE_NAME = "clean_data"

CLEAN_TYPE_MAP = {
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
    "price_per_sqft": "FLOAT",
    "room_total":     "FLOAT",
    "has_prev_sold":  "TINYINT(1) UNSIGNED",
}


# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------

def _pull_batch(context):
    """Lee el batch desde raw_data filtrado por group_number."""
    group = context["ti"].xcom_pull(key="group_number", task_ids="fetch_batch_from_api")
    if group is None:
        raise RuntimeError("No se encontró group_number en XCom.")
    df = get_dataframe_where(RAW_TABLE_NAME, "batch_group", group)
    if df.empty:
        raise RuntimeError(f"No hay datos en raw_data para batch_group={group}.")
    return df


def _registrar_batch_log(run_id: str, group: int, batch_size: int, inserted: int):
    """Registra metadatos del batch en la tabla batch_log."""
    ddl = f"""
    CREATE TABLE IF NOT EXISTS `{BATCH_LOG_TABLE}` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `run_id` VARCHAR(255) NOT NULL,
      `group_number` INT UNSIGNED NOT NULL,
      `batch_size` INT UNSIGNED NOT NULL,
      `inserted_rows` INT UNSIGNED NOT NULL,
      `ingested_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with get_connection() as conn:
        conn.execute(text(ddl))
        conn.execute(
            text(
                f"INSERT INTO `{BATCH_LOG_TABLE}` "
                f"(`run_id`, `group_number`, `batch_size`, `inserted_rows`) "
                f"VALUES (:r, :g, :b, :i)"
            ),
            {"r": run_id, "g": group, "b": batch_size, "i": inserted},
        )


# ---------------------------------------------------------------------------
# Task 1: Obtener batch desde data-api
# ---------------------------------------------------------------------------

def _next_group_number() -> int:
    """Lee el último group_number de batch_log y devuelve el siguiente (1 si no hay/tabla no existe)."""
    try:
        with get_connection() as conn:
            result = conn.execute(text(f"SELECT MAX(`group_number`) FROM `{BATCH_LOG_TABLE}`"))
            max_group = result.scalar()
        return (max_group or 0) + 1
    except Exception:
        return 1


def fetch_batch(**context):
    """Obtiene un lote de la API y lo escribe directamente en raw_data + batch_log."""
    group = _next_group_number()
    run_id = context["dag_run"].run_id

    logger.info("Obteniendo batch group_number=%s", group)
    resp = requests.get(f"{DATA_API_URL}/data", params={"group_number": group}, timeout=120)
    if resp.status_code == 400:
        logger.info("API: %s", resp.json().get("detail", "sin datos"))
        with get_connection() as conn:
            conn.execute(text("DROP TABLE IF EXISTS raw_data"))
            conn.execute(text("DROP TABLE IF EXISTS clean_data"))
            conn.execute(text(f"DROP TABLE IF EXISTS `{BATCH_LOG_TABLE}`"))
        logger.info("Tablas raw_data, clean_data y batch_log reiniciadas.")
        restart = requests.get(f"{DATA_API_URL}/restart_data_generation", params={"group_number": 1}, timeout=30)
        logger.info("Reinicio de data-api: HTTP %s", restart.status_code)
        raise AirflowSkipException("Datos completos — tablas y API reiniciadas para próximo ciclo.")
    if resp.status_code != 200:
        raise RuntimeError(f"data-api respondió HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    records = data if isinstance(data, list) else data.get("data", data)
    if DEBUG_LIMIT > 0 and isinstance(records, list):
        records = records[:DEBUG_LIMIT]
    batch_size = len(records) if isinstance(records, list) else 1
    logger.info("Batch recibido: %d registros (group=%s).", batch_size, group)

    df = pd.DataFrame(records)
    cols = [c for c in COLUMNS if c in df.columns]
    df = df[cols]
    df["batch_group"] = group
    df["ingested_at"] = datetime.utcnow()

    type_map = {k: v for k, v in TYPE_MAP.items() if k in df.columns}
    create_table_with_types(RAW_TABLE_NAME, df, type_map)
    insertadas = insert_data(RAW_TABLE_NAME, df)
    logger.info("Almacenadas %d filas nuevas en `%s`.", insertadas, RAW_TABLE_NAME)

    _registrar_batch_log(run_id, group, batch_size, insertadas)

    context["ti"].xcom_push(key="group_number", value=group)
    context["ti"].xcom_push(key="batch_size", value=batch_size)


# ---------------------------------------------------------------------------
# Task 2: Validar esquema
# ---------------------------------------------------------------------------

def validate_schema(**context):
    """Valida columnas requeridas y tipos de datos del batch."""
    df = _pull_batch(context)

    if df.empty:
        raise RuntimeError("Batch vacío.")

    faltantes = [c for c in COLUMNS if c not in df.columns]
    if faltantes:
        raise RuntimeError(f"Columnas faltantes: {faltantes}")

    _AUDIT = {"batch_group", "ingested_at"}
    unexpected = [c for c in df.columns if c not in COLUMNS and c not in _AUDIT]
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
# Task 3: Validar calidad de datos
# ---------------------------------------------------------------------------

def validate_data_quality(**context):
    """Valida nulos, duplicados, rangos, consistencia y valores categóricos."""
    df = _pull_batch(context)
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
# Task 4: Detectar categorías nuevas
# ---------------------------------------------------------------------------

def detect_new_categories(**context):
    """Identifica y registra categorías no vistas antes en columnas categóricas."""
    df = _pull_batch(context)
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
# Task 5: Detectar data drift (PSI)
# ---------------------------------------------------------------------------

def detect_data_drift(**context):
    """Compara distribución del batch vs histórico usando Population Stability Index."""
    df_batch = _pull_batch(context)
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


# ---------------------------------------------------------------------------
# Task 6: Preprocesar batch y actualizar clean_data
# ---------------------------------------------------------------------------

def preprocess_data(**context):
    """Limpia, transforma y persiste el batch en la tabla clean_data."""
    df = _pull_batch(context)
    logger.info("Preprocesando %d registros.", len(df))

    # Copia para no mutar el original
    clean = df[COLUMNS].copy()

    # Imputación de nulos
    clean["brokered_by"].fillna(0, inplace=True)
    clean["price"].fillna(clean["price"].median(), inplace=True)
    clean["bed"].fillna(clean["bed"].median(), inplace=True)
    clean["bath"].fillna(clean["bath"].median(), inplace=True)
    clean["acre_lot"].fillna(clean["acre_lot"].median(), inplace=True)
    clean["street"].fillna(0, inplace=True)
    clean["house_size"].fillna(clean["house_size"].median(), inplace=True)
    clean["zip_code"].fillna(0, inplace=True)
    clean["status"].fillna("unknown", inplace=True)
    clean["city"].fillna("unknown", inplace=True)
    clean["state"].fillna("unknown", inplace=True)
    clean["prev_sold_date"].fillna("", inplace=True)

    # Feature engineering
    mask = clean["house_size"] > 0
    clean["price_per_sqft"] = 0.0
    clean.loc[mask, "price_per_sqft"] = clean.loc[mask, "price"] / clean.loc[mask, "house_size"]

    clean["room_total"] = clean["bed"] + clean["bath"]
    clean["has_prev_sold"] = (clean["prev_sold_date"] != "").astype(int)

    # Crear tabla e insertar
    type_map = CLEAN_TYPE_MAP
    create_table_with_types(CLEAN_TABLE_NAME, clean, type_map)
    insertadas = insert_data(CLEAN_TABLE_NAME, clean)

    report = {
        "status": "success",
        "records_input": len(df),
        "records_inserted": insertadas,
        "columns": list(clean.columns),
        "derived_features": ["price_per_sqft", "room_total", "has_prev_sold"],
    }

    logger.info("Preprocesamiento completo: %s", report)
    context["ti"].xcom_push(key="preprocess_report", value=report)


# ---------------------------------------------------------------------------
# Task 7: Decidir si entrenar (BranchPythonOperator)
# ---------------------------------------------------------------------------

VOLUMEN_MINIMO = 100


def decide_training(**context):
    """Evalúa reglas técnicas y retorna la siguiente tarea: train_model o skip_training."""
    reports = {
        "quality":  context["ti"].xcom_pull(task_ids="validate_data_quality",    key="data_quality_report"),
        "cats":     context["ti"].xcom_pull(task_ids="detect_new_categories",     key="new_categories_report"),
        "drift":    context["ti"].xcom_pull(task_ids="detect_data_drift",         key="data_drift_report"),
        "prep":     context["ti"].xcom_pull(task_ids="preprocess_data",           key="preprocess_report"),
    }

    batch_size = (reports["prep"] or {}).get("records_input", 0)

    # Regla 1 — volumen mínimo
    if batch_size < VOLUMEN_MINIMO:
        reason = f"Volumen insuficiente: {batch_size} registros (mínimo {VOLUMEN_MINIMO})"
        logger.warning(reason)
        context["ti"].xcom_push(key="training_decision", value={"train": False, "reason": reason})
        return "skip_training"

    # Regla 2 — sin modelo productivo registrado (primera vez)
    try:
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:8003"))
        client = MlflowClient()
        prod_mv = client.get_model_version_by_alias("real-estate-model", "prod")
    except Exception:
        prod_mv = None
    if prod_mv is None:
        reason = "No hay modelo productivo — entrenamiento inicial"
        logger.info(reason)
        context["ti"].xcom_push(key="training_decision", value={"train": True, "reason": reason})
        return "train_model"

    # Regla 3 — drift distribucional
    if reports["drift"] and reports["drift"].get("drift_detected"):
        cols = list(reports["drift"].get("drift_details", {}).keys())
        reason = f"Data drift detectado en: {cols}"
        logger.info(reason)
        context["ti"].xcom_push(key="training_decision", value={"train": True, "reason": reason})
        return "train_model"

    # Regla 4 — categorías nuevas
    if reports["cats"] and reports["cats"].get("new_categories"):
        cats = reports["cats"]["new_categories"]
        reason = f"Nuevas categorías detectadas: {cats}"
        logger.info(reason)
        context["ti"].xcom_push(key="training_decision", value={"train": True, "reason": reason})
        return "train_model"

    # Regla 5 — calidad deficiente (no entrenar si hay problemas graves)
    quality = reports["quality"] or {}
    nulls = quality.get("critical_nulls", {})
    rangos = quality.get("invalid_ranges", {})
    if nulls or rangos:
        reason = f"Problemas de calidad — nulos: {nulls}, rangos: {rangos}"
        logger.warning(reason)
        context["ti"].xcom_push(key="training_decision", value={"train": False, "reason": reason})
        return "skip_training"

    # Por defecto — sin cambios significativos
    reason = "Sin cambios significativos que justifiquen entrenamiento"
    logger.info(reason)
    context["ti"].xcom_push(key="training_decision", value={"train": False, "reason": reason})
    return "skip_training"


# ---------------------------------------------------------------------------
# Task 8: Omitir entrenamiento
# ---------------------------------------------------------------------------

def skip_training(**context):
    """Registra la razón por la cual se omitió el entrenamiento."""
    decision = context["ti"].xcom_pull(task_ids="decide_training", key="training_decision") or {}
    reason = decision.get("reason", "No especificada")
    logger.info("Entrenamiento omitido — razón: %s", reason)
    context["ti"].xcom_push(key="skip_reason", value=reason)


# ---------------------------------------------------------------------------
# Task 9: Entrenar modelo candidato (RF5)
# ---------------------------------------------------------------------------

def train_model(**context):
    """Entrena el pipeline (preprocesador + RandomForest) y lo guarda a disco."""
    group = context["ti"].xcom_pull(task_ids="fetch_batch_from_api", key="group_number")
    run_id = context["dag_run"].run_id
    model_path = os.path.join("/tmp", f"pipeline_{run_id}_{group}.pkl")

    df = get_dataframe(CLEAN_TABLE_NAME)
    if df.empty:
        raise RuntimeError("No hay datos en clean_data para entrenar.")

    X = df.drop(columns=["price"])
    y = df["price"]
    cat_cols = [c for c in CATEGORICAL_COLUMNS if c in X.columns]
    num_cols = [c for c in X.columns if c not in cat_cols]

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
    ])
    X_train, _, y_train, _ = train_test_split(X, y, test_size=0.2, random_state=42)

    rf = RandomForestRegressor(random_state=42, n_jobs=-1)
    gs = GridSearchCV(
        rf,
        {"n_estimators": [50, 100], "max_depth": [10, 20, None], "min_samples_split": [2, 5]},
        cv=3, scoring="neg_mean_absolute_error", n_jobs=-1,
    )
    pipeline = Pipeline([("prep", preprocessor), ("model", gs)])
    pipeline.fit(X_train, y_train)

    joblib.dump(pipeline, model_path)
    logger.info("Pipeline guardado en %s", model_path)

    context["ti"].xcom_push(key="model_path", value=model_path)
    context["ti"].xcom_push(key="data_size", value=len(df))


# ---------------------------------------------------------------------------
# Task 10: Evaluar modelo candidato (RF5)
# ---------------------------------------------------------------------------

def evaluate_model(**context):
    """Evalua el pipeline, calcula métricas y genera artefactos (gráficos, reporte)."""
    model_path = context["ti"].xcom_pull(task_ids="train_model", key="model_path")
    run_id = context["dag_run"].run_id
    group = context["ti"].xcom_pull(task_ids="fetch_batch_from_api", key="group_number")
    artifacts_dir = os.path.join("/tmp", f"artifacts_{run_id}_{group}")
    os.makedirs(artifacts_dir, exist_ok=True)

    pipeline = joblib.load(model_path)

    df = get_dataframe(CLEAN_TABLE_NAME)
    X = df.drop(columns=["price"])
    y = df["price"]
    cat_cols = [c for c in CATEGORICAL_COLUMNS if c in X.columns]
    num_cols = [c for c in X.columns if c not in cat_cols]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    y_pred = pipeline.predict(X_test)
    y_train_pred = pipeline.predict(X_train)

    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    train_mse = mean_squared_error(y_train, y_train_pred)
    train_rmse = np.sqrt(train_mse)
    train_r2 = r2_score(y_train, y_train_pred)

    # Reporte de métricas
    with open(os.path.join(artifacts_dir, "metrics.txt"), "w") as f:
        f.write(f"Test  MAE: {mae:.4f}  MSE: {mse:.4f}  RMSE: {rmse:.4f}  R²: {r2:.4f}\n")
        f.write(f"Train MAE: {train_mae:.4f}  MSE: {train_mse:.4f}  RMSE: {train_rmse:.4f}  R²: {train_r2:.4f}\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Feature importance
    best = pipeline.named_steps["model"].best_estimator_
    if hasattr(best, "feature_importances_"):
        try:
            preprocessor = pipeline.named_steps["prep"]
            cat_names = preprocessor.named_transformers_["cat"].get_feature_names_out(cat_cols)
            feat_names = list(num_cols) + list(cat_names)
        except Exception:
            feat_names = [f"f{i}" for i in range(len(best.feature_importances_))]
        imp = best.feature_importances_
        idx = np.argsort(imp)[-15:]
        plt.figure(figsize=(8, 5))
        plt.title("Feature Importances")
        plt.barh(range(len(idx)), imp[idx])
        plt.yticks(range(len(idx)), [feat_names[i] for i in idx])
        plt.tight_layout()
        plt.savefig(os.path.join(artifacts_dir, "feature_importance.png"))
        plt.close()

    # Residual plot
    residuals = y_test - y_pred
    plt.figure(figsize=(8, 5))
    plt.scatter(y_pred, residuals, alpha=0.3)
    plt.axhline(y=0, color="r", linestyle="--")
    plt.xlabel("Predicho")
    plt.ylabel("Residual")
    plt.title("Residual Plot")
    plt.savefig(os.path.join(artifacts_dir, "residuals.png"))
    plt.close()

    logger.info("Evaluación: MAE=%.2f, RMSE=%.2f, R²=%.4f", mae, rmse, r2)

    context["ti"].xcom_push(key="evaluation_report", value={
        "mae": mae, "mse": mse, "rmse": rmse, "r2": r2,
        "train_mae": train_mae, "train_mse": train_mse, "train_rmse": train_rmse, "train_r2": train_r2,
        "artifacts_dir": artifacts_dir,
    })


# ---------------------------------------------------------------------------
# Task 11: Registrar modelo candidato en MLflow (RF5)
# ---------------------------------------------------------------------------

def register_model(**context):
    """Registra el pipeline, métricas y artefactos en MLflow."""
    model_path = context["ti"].xcom_pull(task_ids="train_model", key="model_path")
    eval_report = context["ti"].xcom_pull(task_ids="evaluate_model", key="evaluation_report")
    decision = context["ti"].xcom_pull(task_ids="decide_training", key="training_decision") or {}

    pipeline = joblib.load(model_path)

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:8003"))
    mlflow.set_experiment("price_experiment")

    df = get_dataframe(CLEAN_TABLE_NAME)
    X = df.drop(columns=["price"])
    y = df["price"]
    X_train, _ = train_test_split(X, test_size=0.2, random_state=42)

    with mlflow.start_run() as run:
        mlflow.set_tag("reason", decision.get("reason", ""))
        mlflow.set_tag("model_type", "RandomForestRegressor")

        best = pipeline.named_steps["model"].best_estimator_
        mlflow.log_params(best.get_params())

        mlflow.log_metric("test_mae", eval_report["mae"])
        mlflow.log_metric("test_mse", eval_report["mse"])
        mlflow.log_metric("test_rmse", eval_report["rmse"])
        mlflow.log_metric("test_r2", eval_report["r2"])
        mlflow.log_metric("train_mae", eval_report["train_mae"])
        mlflow.log_metric("train_mse", eval_report["train_mse"])
        mlflow.log_metric("train_rmse", eval_report["train_rmse"])
        mlflow.log_metric("train_r2", eval_report["train_r2"])

        # Artefactos (gráficos, reportes)
        artifacts_dir = eval_report.get("artifacts_dir")
        if artifacts_dir and os.path.exists(artifacts_dir):
            for fname in os.listdir(artifacts_dir):
                mlflow.log_artifact(os.path.join(artifacts_dir, fname))

        signature = infer_signature(X_train, pipeline.predict(X_train))
        result = mlflow.sklearn.log_model(
            sk_model=pipeline,
            artifact_path="model",
            registered_model_name="real-estate-model",
            signature=signature,
            input_example=X_train.iloc[:5],
        )

        logger.info("Registrado: versión %s | MAE=%.2f | RMSE=%.2f | R²=%.4f",
                     result.registered_model_version,
                     eval_report["mae"], eval_report["rmse"], eval_report["r2"])

    context["ti"].xcom_push(key="register_report", value={
        "version": result.registered_model_version,
        "run_id": run.info.run_id,
    })


# ---------------------------------------------------------------------------
# Task 12: Comparar candidato vs productivo (RF6)
# ---------------------------------------------------------------------------

def compare_with_production(**context):
    """Compara métricas del candidato contra el modelo productivo en MLflow."""
    eval_report = context["ti"].xcom_pull(task_ids="evaluate_model", key="evaluation_report")
    reg_report = context["ti"].xcom_pull(task_ids="register_model", key="register_report")

    candidate_mae = eval_report["mae"]
    candidate_rmse = eval_report["rmse"]
    candidate_version = reg_report["version"]
    candidate_run_id = reg_report["run_id"]

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:8003"))
    client = MlflowClient()
    MODEL_NAME = "real-estate-model"
    ALIAS = "prod"

    try:
        prod_mv = client.get_model_version_by_alias(MODEL_NAME, ALIAS)
        prod_version = int(prod_mv.version)
        prod_run = client.get_run(prod_mv.run_id)
        prod_mae = prod_run.data.metrics.get("test_mae")
        prod_rmse = prod_run.data.metrics.get("test_rmse")
    except Exception:
        prod_version = None
        prod_mae = None
        prod_rmse = None

    if prod_version is None:
        should_promote = True
        reason = "Primer modelo — no hay productivo con quien comparar"
        mae_improvement = None
        rmse_regression = None
    else:
        mae_improvement = ((prod_mae - candidate_mae) / prod_mae) * 100
        rmse_regression = ((candidate_rmse - prod_rmse) / prod_rmse) * 100
        # RF6: MAE >= 3% mejor, RMSE no empeora > 1%
        if mae_improvement >= 3 and rmse_regression <= 1:
            should_promote = True
            reason = (
                f"MAE mejora {mae_improvement:.2f}% (≥3%) y "
                f"RMSE empeora {rmse_regression:.2f}% (≤1%)"
            )
        else:
            should_promote = False
            reason = (
                f"No cumple: MAE mejora {mae_improvement:.2f}% (req ≥3%), "
                f"RMSE empeora {rmse_regression:.2f}% (req ≤1%)"
            )

    report = {
        "candidate_version": candidate_version,
        "candidate_mae": candidate_mae,
        "candidate_rmse": candidate_rmse,
        "candidate_run_id": candidate_run_id,
        "production_version": prod_version,
        "production_mae": prod_mae,
        "production_rmse": prod_rmse,
        "mae_improvement_pct": mae_improvement,
        "rmse_regression_pct": rmse_regression,
        "should_promote": should_promote,
        "reason": reason,
    }

    logger.info("Comparación: %s", reason)
    context["ti"].xcom_push(key="comparison_report", value=report)


# ---------------------------------------------------------------------------
# Task 13: Decidir promoción (BranchPythonOperator)
# ---------------------------------------------------------------------------

def decide_promotion(**context):
    """Bifurca según el resultado de la comparación."""
    report = context["ti"].xcom_pull(task_ids="compare_with_production", key="comparison_report")
    if report and report.get("should_promote"):
        logger.info("Decisión: promover modelo")
        return "promote_model"
    logger.info("Decisión: rechazar modelo")
    return "reject_model"


# ---------------------------------------------------------------------------
# Task 14: Promover modelo a producción
# ---------------------------------------------------------------------------

def promote_model(**context):
    """Actualiza alias prod en MLflow y notifica a la API."""
    report = context["ti"].xcom_pull(task_ids="compare_with_production", key="comparison_report")
    candidate_version = report["candidate_version"]

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:8003"))
    client = MlflowClient()
    client.set_registered_model_alias("real-estate-model", "prod", str(candidate_version))
    logger.info("Alias 'prod' actualizado a versión %s", candidate_version)

    api_url = os.getenv("PREDICT_API_URL", "http://api:8000")
    try:
        resp = requests.post(f"{api_url}/model", timeout=30)
        logger.info("API recargada: HTTP %s", resp.status_code)
    except Exception as e:
        logger.warning("No se pudo notificar a la API: %s", e)

    context["ti"].xcom_push(key="promotion_result", value={
        "version": candidate_version,
        "status": "promoted",
    })


# ---------------------------------------------------------------------------
# Task 15: Rechazar modelo
# ---------------------------------------------------------------------------

def reject_model(**context):
    """Registra la razón del rechazo."""
    report = context["ti"].xcom_pull(task_ids="compare_with_production", key="comparison_report")
    reason = report.get("reason", "No cumple criterios de promoción")
    logger.warning("Modelo rechazado: %s", reason)
    context["ti"].xcom_push(key="rejection_reason", value=reason)


# ---------------------------------------------------------------------------
# Task 16: Notificar / registrar historial (RF9)
# ---------------------------------------------------------------------------

def notify_or_log_result(**context):
    """Inserta un registro en training_history con el resultado del pipeline."""
    batch_number = context["ti"].xcom_pull(task_ids="fetch_batch_from_api", key="group_number")
    execution_date = datetime.utcnow()

    skip_reason = context["ti"].xcom_pull(task_ids="skip_training", key="skip_reason")
    promotion = context["ti"].xcom_pull(task_ids="promote_model", key="promotion_result")

    if skip_reason:
        decision = "skip"
        reason = skip_reason
        model_version = None
        mae = rmse = r2 = None
        prod_version = prod_mae = mae_imp = rmse_reg = None
        run_id_val = None
    elif promotion:
        decision = "promoted"
        report = context["ti"].xcom_pull(task_ids="compare_with_production", key="comparison_report")
        eval_rep = context["ti"].xcom_pull(task_ids="evaluate_model", key="evaluation_report")
        reason = report["reason"]
        model_version = report["candidate_version"]
        mae = report["candidate_mae"]
        rmse = report["candidate_rmse"]
        r2 = eval_rep["r2"]
        prod_version = report["production_version"]
        prod_mae = report["production_mae"]
        mae_imp = report["mae_improvement_pct"]
        rmse_reg = report["rmse_regression_pct"]
        run_id_val = report["candidate_run_id"]
    else:
        decision = "rejected"
        report = context["ti"].xcom_pull(task_ids="compare_with_production", key="comparison_report")
        eval_rep = context["ti"].xcom_pull(task_ids="evaluate_model", key="evaluation_report",)
        reason = report.get("reason", "Rechazado")
        model_version = report["candidate_version"]
        mae = report["candidate_mae"]
        rmse = report["candidate_rmse"]
        r2 = eval_rep["r2"]
        prod_version = report["production_version"]
        prod_mae = report["production_mae"]
        mae_imp = report["mae_improvement_pct"]
        rmse_reg = report["rmse_regression_pct"]
        run_id_val = report["candidate_run_id"]

    ddl = f"""
    CREATE TABLE IF NOT EXISTS `{HISTORY_TABLE}` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `batch_number` INT,
      `execution_date` DATETIME,
      `decision` VARCHAR(20),
      `model_version` INT,
      `reason` TEXT,
      `candidate_mae` FLOAT, `candidate_rmse` FLOAT, `candidate_r2` FLOAT,
      `production_version` INT, `production_mae` FLOAT,
      `mae_improvement_pct` FLOAT, `rmse_regression_pct` FLOAT,
      `mlflow_run_id` VARCHAR(100),
      `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    with get_connection() as conn:
        conn.execute(text(ddl))
        conn.execute(
            text(f"""
            INSERT INTO `{HISTORY_TABLE}`
            (`batch_number`, `execution_date`, `decision`, `model_version`, `reason`,
             `candidate_mae`, `candidate_rmse`, `candidate_r2`,
             `production_version`, `production_mae`,
             `mae_improvement_pct`, `rmse_regression_pct`, `mlflow_run_id`)
            VALUES (:bn, :ed, :dec, :mv, :rea,
                    :cmae, :crmse, :cr2,
                    :pv, :pmae,
                    :maeimp, :rmseimp, :rid)
            """),
            {
                "bn": batch_number, "ed": execution_date, "dec": decision,
                "mv": model_version, "rea": reason,
                "cmae": mae, "crmse": rmse, "cr2": r2,
                "pv": prod_version, "pmae": prod_mae,
                "maeimp": mae_imp, "rmseimp": rmse_reg, "rid": run_id_val,
            },
        )

    logger.info("Historial registrado: batch=%s, decisión=%s", batch_number, decision)


# ---------------------------------------------------------------------------
# Task 17: Fin de la ejecución
# ---------------------------------------------------------------------------

def end(**context):
    """Marca el fin exitoso del pipeline."""
    logger.info("=" * 50)
    logger.info("Pipeline completado exitosamente.")
    logger.info("=" * 50)
