import pandas as pd
from .raw_data_dictionary import get_raw_column_names
from sklearn.preprocessing import LabelEncoder
from .db import create_table, create_table_with_types, insert_data, get_rows_with_columns, delete_table
from .etl import load_raw_data, clear_data, shrink_dtypes
from pandas.api.types import (
    is_bool_dtype, is_integer_dtype, is_float_dtype, is_datetime64_any_dtype
)
# load the data

# print(penguins.head())
endl = "#" * 100


#region Save raw data functions
def store_data(fetchData ,table_name, columns):
    data = pd.DataFrame(fetchData, columns=columns)
    type_map = build_type_map(data)
    create_table_with_types(table_name, data, type_map)
    insert_data(table_name, data)

def store_raw_data(count, batch_size = 15000):
  raw_data = load_raw_data(count, batch_size)
  print("after load_raw_data")
  store_data(raw_data['train'], "raw_data_train", get_raw_column_names())
  store_data(raw_data['validate'], "raw_data_validate", get_raw_column_names())
  store_data(raw_data['test'], "raw_data_test", get_raw_column_names())

#endregion

#region droping and cleaning functions

def clear_all_data():
  clear_raw_data()
  clear_clean_data()

def clear_raw_data():
  delete_table("raw_data_train")
  delete_table("raw_data_validate")
  delete_table("raw_data_test")

def clear_clean_data():
  delete_table("clean_data_train")
  delete_table("clean_data_validate")
  delete_table("clean_data_test")

#endregion

#region get, clean and save data functions
def get_raw_data(table_name):
  rows, columns = get_rows_with_columns(table_name)
  # Exclude 'id' column
  df = pd.DataFrame([row[1:] for row in rows], columns=columns[1:])
  df = df.drop(columns=["row_hash"])
  return df

def save_clean_data(table_sufix, must_balance=False):
    raw_data = get_raw_data("raw_data_" + table_sufix)
    clean_data_df, column_list = clear_data(raw_data, must_balance)
    # clean_data_df = shrink_dtypes(clean_data_df)
    print("clean data number of columns", len(clean_data_df.columns))
    type_map = build_type_map(clean_data_df)
    table_name = "clean_data_" + table_sufix
    create_table_with_types(table_name, clean_data_df, type_map)
    print("After create clean data ", table_sufix)
    for i in range(0,len(clean_data_df), 5000):
      print("Inserting in index", i)
      end_index = i + 5000 if i + 5000 < len(clean_data_df) else len(clean_data_df)
      partial_clean_data_df = clean_data_df.iloc[i:end_index]
      insert_data("clean_data_" + table_sufix, partial_clean_data_df)

def save_all_clean_data():
    save_clean_data("train", True)
    save_clean_data("validate")
    save_clean_data("test")

#endregion

#region get clean data functions
def get_clean_data(table_sufix):
  rows, columns = get_rows_with_columns("clean_data_" + table_sufix)
  columns = columns[1:]  # Exclude 'id' column
  le = LabelEncoder()
  clean_data_df = pd.DataFrame([row[1:] for row in rows], columns=columns)
  clean_data_df = clean_data_df.drop(columns=["row_hash"])
  y = clean_data_df['readmitted']
  X = clean_data_df.drop(columns=["readmitted"])

  show_after_cleaning(X, y)
  return X, y
#endregion



def build_type_map(df: pd.DataFrame) -> dict[str, str]:
    type_map: dict[str, str] = {}
    for col in df.columns:
        s = df[col]
        if is_bool_dtype(s):
            type_map[col] = "TINYINT(1) UNSIGNED"
        elif is_integer_dtype(s):
            mn, mx = (int(s.min()), int(s.max())) if len(s) else (0, 0)
            if mn >= 0:
                if mx <= 255:         type_map[col] = "TINYINT UNSIGNED"
                elif mx <= 65535:     type_map[col] = "SMALLINT UNSIGNED"
                elif mx <= 16777215:  type_map[col] = "MEDIUMINT UNSIGNED"
                else:                  type_map[col] = "INT UNSIGNED"
            else:
                if -128 <= mn <= 127 and mx <= 127:               type_map[col] = "TINYINT"
                elif -32768 <= mn <= 32767 and mx <= 32767:       type_map[col] = "SMALLINT"
                elif -8388608 <= mn <= 8388607 and mx <= 8388607: type_map[col] = "MEDIUMINT"
                else:                                             type_map[col] = "INT"
        elif is_float_dtype(s):
            type_map[col] = "FLOAT"
        elif is_datetime64_any_dtype(s):
            type_map[col] = "DATETIME"
        else:
            # string/object → size by max length (cap at 255), else TEXT
            maxlen = int(s.dropna().astype(str).str.len().max()) if len(s.dropna()) else 0
            type_map[col] = f"VARCHAR({min(maxlen if maxlen > 0 else 1, 255)})" if maxlen <= 255 else "TEXT"
    return type_map

