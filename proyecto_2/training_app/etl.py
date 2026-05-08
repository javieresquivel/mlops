import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.utils import resample
import scipy as sp
from matplotlib.colors import ListedColormap

from sklearn.pipeline import Pipeline

from .db import *

import os, joblib
from sklearn.preprocessing import StandardScaler, OneHotEncoder, OrdinalEncoder, FunctionTransformer
from sklearn.compose import ColumnTransformer
import cloudpickle
import gzip
import training_app
import sys


pd.set_option('future.no_silent_downcasting', True)

# load the data
endl = "#" * 100

BASE_CAT = [
    "gender","admission_type_id","discharge_disposition_id","admission_source_id",
    "max_glu_serum","A1Cresult","race","age"
]
MED_COLS = [
    "metformin","repaglinide","nateglinide","chlorpropamide","glimepiride","acetohexamide",
    "glipizide","glyburide","tolbutamide","pioglitazone","rosiglitazone","acarbose","miglitol",
    "troglitazone","tolazamide","insulin","glyburide_metformin","glipizide_metformin",
    "glimepiride_pioglitazone","metformin_rosiglitazone","metformin_pioglitazone",
    "change_m","diabetesMed",
]
DIAG_COLS = ["diag_1","diag_2","diag_3"]
ID_COLUMNS = {"encounter_id","patient_nbr"}
TARGET = "readmitted"
READMITTED_MAP = {">30": 0, "<30": 1, "NO": 0}

def to_str_df(X):
    import pandas as pd
    return pd.DataFrame(X).astype(str)


def load_raw_data(batch_number, batch_size):
    df = pd.read_csv("https://docs.google.com/uc?export=download&confirm={{VALUE}}&id=1k5-1caezQ3zWJbKaiMULTGq-3sz6uThC")
    print("df after read_csv in load_raw_data", df.head())
    start_index = (batch_number - 1) * batch_size
    end_index = start_index + batch_size if start_index + batch_size < df.shape[0] else df.shape[0]
    df = df.iloc[start_index:end_index]
    print("df in load_raw_data", df.head())
    return split_data(df, "readmitted")
    

def get_batch_amount(batch_size):
  print("batch_size type", type(batch_size))
  df = pd.read_csv("https://docs.google.com/uc?export=download&confirm={{VALUE}}&id=1k5-1caezQ3zWJbKaiMULTGq-3sz6uThC")
  batch_amount = (df.shape[0] // batch_size) + 1
  return batch_amount
  

def balance_dataset(X, y):
    # Separate majority and minority classes
    df_majority = X[y == 0]
    df_minority = X[y == 1]

    # Upsample minority class
    df_minority_upsampled = resample(
        df_minority, replace=True, n_samples=len(df_majority), random_state=20
    )

    # Combine majority class with upsampled minority class
    X_balanced = pd.concat([df_majority, df_minority_upsampled])
    y_balanced = pd.Series([0] * len(df_majority) + [1] * len(df_minority_upsampled))

    return X_balanced, y_balanced

def train_and_evaluate_model(model, X_train, X_test, y_train, y_test, model_name):
    print(f"\n--- {model_name} ---")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    # Create confusion matrix
    cm = pd.crosstab(
        pd.Series(y_test, name="Actual"),
        pd.Series(y_pred, name="Predict"),
        margins=True,
    )
    print(cm)

    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)

    print(f"Accuracy: {accuracy:.2f}")
    print(f"Precision: {precision:.2f}")
    print(f"Recall: {recall:.2f}")

    return {
        "model": model,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
    }

def plot_model_comparison(results):
    plt.figure(figsize=(14, 7))
    x = np.arange(len(results))
    width = 0.25

    metrics = ["accuracy", "precision", "recall"]
    colors = ["red", "blue", "green"]

    for i, (metric, color) in enumerate(zip(metrics, colors)):
        values = [results[model_name][metric] for model_name in results.keys()]
        plt.bar(
            x + i * width, values, width=width, color=color, alpha=0.7, label=metric
        )

    plt.xlabel("Model")
    plt.ylabel("Score")
    plt.title("Model Comparison")
    plt.xticks(x + width, results.keys())
    plt.legend()
    plt.tight_layout()
    plt.show()

def split_data(df, target_col, test_size=0.10, val_size=0.20, random_state=42):
    # Basic validations
    print("amount of data in split_data ", len(df))
    if not 0 < test_size < 1 or not 0 < val_size < 1:
        raise ValueError("test_size and val_size must be in (0, 1)")
    if test_size + val_size >= 1:
        raise ValueError("test_size + val_size must be < 1")
    if target_col not in df.columns:
        raise KeyError(f"'{target_col}' not found in dataframe columns")

    df_train, df_temp = train_test_split(
        df,
        test_size=test_size + val_size,
        stratify=df[target_col],
        random_state=random_state,
    )

    rel_test_size = test_size / (test_size + val_size)
    df_val, df_test = train_test_split(
        df_temp,
        test_size=rel_test_size,
        stratify=df_temp[target_col],
        random_state=random_state,
    )

    # Optional: reset indices for clean downstream merges/joins
    return {
        "train": df_train.reset_index(drop=True),
        "validate": df_val.reset_index(drop=True),
        "test": df_test.reset_index(drop=True)
    }
def shrink_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    bool_like = []
    for c in df.columns:
        if df[c].dtype == bool:
            bool_like.append(c)
        elif df[c].dtype == object:
            # convert 'True'/'False'/1/0 to 0/1 if applicable
            vals = set(df[c].dropna().unique())
            if vals <= {True, False, 'True', 'False', 1, 0, '1', '0'}:
                df[c] = df[c].map({'True':1,'False':0,True:1,False:0,'1':1,'0':0,1:1,0:0}).astype('int8')

    if bool_like:
        df[bool_like] = df[bool_like].astype('int8')

    for col in df.select_dtypes(include=['int64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')
    return df

def prepare_features(df):
    # Convert data type of nominal features to 'object' type
    nominal_features = [
        "encounter_id",
        "patient_nbr",
        "gender",
        "admission_type_id",
        "discharge_disposition_id",
        "admission_source_id",
        "A1Cresult",
        "age",
        "max_glu_serum",
        "diag_1",
        "diag_2",
        "diag_3",
    ]

    # Add medication columns
    med_columns = [
        col
        for col in df.columns
        if col
        in [
            "metformin",
            "repaglinide",
            "nateglinide",
            "chlorpropamide",
            "glimepiride",
            "acetohexamide",
            "glipizide",
            "glyburide",
            "tolbutamide",
            "pioglitazone",
            "rosiglitazone",
            "acarbose",
            "miglitol",
            "troglitazone",
            "tolazamide",
            "insulin",
            "glyburide_metformin",
            "glipizide_metformin",
            "glimepiride_pioglitazone",
            "metformin_rosiglitazone",
            "metformin_pioglitazone",
            "change_m",
            "diabetesMed",
        ]
    ]


    # Convert only existing columns
    for col in nominal_features:
        if col in df.columns:
            df[col] = df[col].astype("object")

    print("df in prepare_features", df.head())
    # Get list of only numeric features
    numerics = list(set(list(df._get_numeric_data().columns)))
    print("numerics", numerics)
    numerics.remove("readmitted")
    print("numerics after removing readmitted", numerics)

    # Standardize numeric features
    df2 = df.copy()

    # First convert numeric columns to float to avoid warnings
    for col in numerics:
        df2[col] = df2[col].astype(float)
    print("df2 in prepare_features", df2.head())

    # Now standardize
    std =  (np.std(df2[numerics], axis=0)).replace(0, 1)
    # if np.std(df2[numerics], axis=0) == 0:
    # std = std.replace(0, 1)
    mean = np.mean(df2[numerics], axis=0)
    df2.loc[:, numerics] = (df2[numerics] - mean) / std
    # Remove outliers
    # TODO: remove outliers

    # Define categorical columns for dummy variables
    categorical_columns = [
        "gender",
        "admission_type_id",
        "discharge_disposition_id",
        "admission_source_id",
        "max_glu_serum",
        "A1Cresult",
        "race",
    ]

    categorical_columns.extend(med_columns)

    # Create dummy variables
    df_encoded = pd.get_dummies(df2, dtype='int8', columns=categorical_columns, drop_first=True)
    print("df_encoded in prepare_features", df_encoded.head())

    # Define feature sets
    numeric_features = [
        "age",
        "time_in_hospital",
        "num_procedures",
        "num_medications",
        "number_outpatient",
        "number_emergency",
        "number_inpatient",
        "number_diagnoses",
    ]

    # Get all dummy columns for categorical variables
    dummy_columns = [
        col
        for col in df_encoded.columns
        if any(
            col.startswith(prefix)
            for prefix in [
                "gender_",
                "admission_type_id_",
                "discharge_disposition_id_",
                "admission_source_id_",
                "max_glu_serum_",
                "A1Cresult_",
                "race_",
            ]
            + [f"{med}_" for med in med_columns]
        )
    ]

    # Combine numeric and dummy features
    print("numeric_features", numeric_features)
    print("dummy_columns", dummy_columns)
    feature_set = numeric_features + dummy_columns

    return df_encoded, feature_set

def map_readmitted_series(s: pd.Series) -> pd.Series:
    """Map target labels to ints and return a small dtype."""
    out = s.astype(str).str.strip().map(READMITTED_MAP)
    # optional: handle anything unexpected as 0 (or raise)
    out = out.fillna(0).astype("int8")
    return out


def clear_data(raw_data, for_balancing=False):
    print("raw_data -->", raw_data.head())
    y = raw_data[TARGET]
    y = map_readmitted_series(y)
    X = raw_data.drop(columns=[TARGET])
    prep, groups = build_preprocessor(raw_data)
    X_transformed = prep.fit_transform(X)
    out_dir = os.getenv("MODELS_DIR", "./models")
    os.makedirs(out_dir, exist_ok=True)
    cloudpickle.register_pickle_by_value(sys.modules[__name__])
    if (for_balancing):
        print("for_balancing", for_balancing)
        with open(os.path.join(out_dir, "preprocessor.pkl"), "wb") as f:
            cloudpickle.dump({"prep": prep, "groups": groups}, f)
    feature_names = prep.get_feature_names_out()
    # Convert X_transformed to a DataFrame
    X_df = pd.DataFrame(X_transformed, columns=feature_names)

    X_df[TARGET] = y.reset_index(drop=True)
    print("X_df", X_df.head())
    return X_df, feature_names


def show_after_cleaning(X, y):
  print("After cleaning")
  print(X.head())
  print(y.head())
  print(X.shape)
  print(y.shape)
  print(endl)

def store_raw_data():
  data, batch_number = fetch_data()
  rawData = pd.DataFrame(data, columns=get_raw_column_names())
  create_table("raw_data", rawData)
  insert_data("raw_data", rawData)
  return batch_number

def clear_raw_data():
  delete_table("raw_data")


def clean_all_data():
  clear_raw_data()
  clear_clean_data()

def get_raw_data():
  print("Getting raw data from DB")
  rows, columns = get_rows_with_columns("raw_data")
  print("columns raw data", columns)
  df = pd.DataFrame([row[1:] for row in rows], columns=columns[1:])
  df = df.drop(columns=["row_hash"])
  print(df.head())
  return df

def clear_clean_data():
  delete_table("clean_data")

def save_clean_data():
  raw_data = get_raw_data()
  clean_data_df = clear_data(raw_data)
  create_table("clean_data", clean_data_df, column_list)
  columns = get_table_columns("clean_data")
  insert_data("clean_data", clean_data_df)
  print('Clean data saved to DB', clean_data_df.head())

def get_clean_data():
  rows, columns = get_rows_with_columns("clean_data_train")
  columns = columns[1:]  # Exclude 'id' column
  clean_data_df = pd.DataFrame([row[1:] for row in rows], columns=columns)
  clean_data_df = clean_data_df.drop(columns=["row_hash"])
  y = clean_data_df['readmitted']
  X = clean_data_df.drop(columns=["readmitted"])
  print("columns deleted", clean_data_df.columns)
  show_after_cleaning(X, y)
  return X, y

def _simplify_icd_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.upper().str.strip().replace({"?": "UNK"})
    def map_code(code: str) -> str:
        if code == "UNK" or code == "" or code == "NAN": return "Unknown"
        if code.startswith("E"): return "Injury_E"
        if code.startswith("V"): return "Supplementary_V"
        # numeric-ish?
        try:
            v = float(code)
        except ValueError:
            return "Other"
        if str(code).startswith("250"): return "Diabetes_250"
        # ICD-9 big buckets (common in the UCI diabetes papers)
        if 390 <= v <= 459 or v == 785:  return "Circulatory"
        if 460 <= v <= 519 or v == 786:  return "Respiratory"
        if 520 <= v <= 579 or v == 787:  return "Digestive"
        if 580 <= v <= 629 or v == 788:  return "Genitourinary"
        if 240 <= v <= 279:              return "Endocrine_Nutrition"
        if 710 <= v <= 739:              return "Musculoskeletal"
        if 780 <= v <= 799:              return "Symptoms_Signs"
        return "Other"
    return s.map(map_code)

def simplify_icd_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in DIAG_COLS:
        if c in out.columns:
            out[c] = _simplify_icd_series(out[c])
    return out

# ---- 2) Meds as ordinal
MED_ORDER = ["No", "Steady", "Up", "Down"]  # choose any consistent order
def ordinal_categories(df, cols):
    # Build per-column category lists (only values seen in TRAIN need to be ordered)
    cats = []
    for c in cols:
        present = [v for v in MED_ORDER if c in df and v in df[c].astype(str).unique()]
        # ensure full order for consistency; OrdinalEncoder handles unseen with unknown_value
        cats.append(MED_ORDER)
    return cats

def build_preprocessor(df: pd.DataFrame):
    present_base = [c for c in BASE_CAT if c in df.columns]
    present_meds = [c for c in MED_COLS if c in df.columns]
    present_diag = [c for c in DIAG_COLS if c in df.columns]

    # ------------- MUTUALLY EXCLUSIVE ----------------
    # numeric = numeric dtypes minus ids/target and minus any that we force to categorical/meds/diag
    forced_cats = set(present_base) | set(present_meds) | set(present_diag)
    num_cols_all = df.select_dtypes(include=["number"]).columns.tolist()
    num_cols = [c for c in num_cols_all
                if c not in ID_COLUMNS
                and c != TARGET
                and c not in forced_cats]

    # base categoricals (OHE)
    cat_ohe_cols = present_base

    # meds as ordinal single column
    MED_ORDER = ["No", "Steady", "Up", "Down"]
    med_categories = [MED_ORDER for _ in present_meds]
    meds_pipe = Pipeline([
        ("to_str", FunctionTransformer(
            to_str_df,                # << no lambda
            validate=False,
            feature_names_out="one-to-one"
        )),
        ("ord", OrdinalEncoder(
            categories=med_categories,
            handle_unknown="use_encoded_value",
            unknown_value=-1
        ))
    ])


    diag_pipe = Pipeline([
        ("bucket", FunctionTransformer(
            simplify_icd_frame,
            validate=False,
            feature_names_out="one-to-one"
        )),
        ("ohe", OneHotEncoder(
            handle_unknown="infrequent_if_exist",
            min_frequency=50,
            sparse_output=False
        ))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            ("base_cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_ohe_cols),
            ("meds", meds_pipe, present_meds),
            ("diag", diag_pipe, present_diag),
        ],
        remainder="drop",
        # IMPORTANT: add transformer prefixes to avoid name collisions
        verbose_feature_names_out=True,
    )

    groups = {
        "numeric": num_cols,
        "base_cat": cat_ohe_cols,
        "meds": present_meds,
        "diag": present_diag,
    }
    return preprocessor, groups

