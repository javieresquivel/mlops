import mysql.connector
import time
import sys
import os
import pandas as pd

def get_db_connection():
    host = os.getenv('DB_HOST', '10.43.100.99')  # service name in docker-compose
    port = int(os.getenv('DB_PORT', '8005'))
    user = os.getenv('DB_USER', 'user')
    password = os.getenv('DB_PASSWORD', 'password')
    database = os.getenv('DB_NAME', 'training')

    return mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )

def create_table(table_name, columns_df, cols_predefined=[]):
  connection = None
  cursor = None
  try:
    # columns_df = columns_df.to_string(index=False)
    columns = columns_df.columns.tolist()
    columns_str = ", ".join([f"{col} VARCHAR(255)" for col in columns])
    connection = get_db_connection()
    cursor = connection.cursor()
    if cols_predefined:
      cols = cols_predefined
    else:
      cols = columns_df.columns.tolist()
    col_defs = ",\n  ".join([f"`{c}` VARCHAR(255) NOT NULL DEFAULT '0' " for c in cols])

    # CONCAT_WS with a delimiter avoids ambiguity; COALESCE to make NULLs deterministic
    concat_expr = "CONCAT_WS('|'," + ", ".join([f"COALESCE(`{c}`,'')" for c in cols]) + ")"

    ddl = f"""
    CREATE TABLE IF NOT EXISTS `{table_name}` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      {col_defs},
      /* SHA2-256 -> 32 bytes binary; safer than MD5 for collision risk */
      `row_hash` BINARY(32)
        GENERATED ALWAYS AS (UNHEX(SHA2({concat_expr}, 256))) STORED,
      UNIQUE KEY `uniq_row_hash` (`row_hash`),
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
    """
    print("create_table ddl", ddl)
    cursor.execute(ddl)
    connection.commit()
  except mysql.connector.Error as err:
    print(f"Database error: {err}")
  finally:
    if connection and connection.is_connected():
      cursor.close()
      connection.close()
      print("MySQL connection closed")

# db.py
def _default_for(mysql_type: str) -> str:
    t = mysql_type.upper()
    if "TEXT" in t:
        return ""  # TEXT cannot have DEFAULT; keep it nullable
    if any(x in t for x in ["INT", "TINYINT", "SMALLINT", "MEDIUMINT", "FLOAT", "DOUBLE", "DECIMAL"]):
        return " DEFAULT 0"
    if "DATETIME" in t:
        return " DEFAULT '1970-01-01 00:00:00'"
    # VARCHAR/CHAR/BINARY
    return " DEFAULT ''"

def create_table_with_types(table_name, columns_df, type_map: dict, cols_predefined=[]):
  connection = None
  cursor = None
  try:
    connection = get_db_connection()
    cursor = connection.cursor()

    if cols_predefined:
        cols = cols_predefined
    else:
        cols = columns_df.columns.tolist()

    # Build typed column definitions
    col_defs_parts = []
    for c in cols:
        mtype = (type_map.get(c) or "VARCHAR(255)").upper()
        if "TEXT" in mtype:
            col_defs_parts.append(f"`{c}` {mtype} NULL")
        else:
            col_defs_parts.append(f"`{c}` {mtype} NOT NULL{_default_for(mtype)}")
    col_defs = ",\n  ".join(col_defs_parts)

    # Keep your existing hash logic as-is to minimize changes
    concat_expr = "CONCAT_WS('|'," + ", ".join([f"COALESCE(`{c}`,'')" for c in cols]) + ")"

    ddl = f"""
    CREATE TABLE IF NOT EXISTS `{table_name}` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      {col_defs},
      `row_hash` BINARY(32)
        GENERATED ALWAYS AS (UNHEX(SHA2({concat_expr}, 256))) STORED,
      UNIQUE KEY `uniq_row_hash` (`row_hash`),
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
    """
    print("create_table_with_types ddl", ddl)
    cursor.execute(ddl)
    connection.commit()

  except mysql.connector.Error as err:
      print(f"❌ Database error: {err}")
  finally:
      if connection and connection.is_connected():
          cursor.close()
          connection.close()
          print("MySQL connection closed")

def get_headers(columns_df):
    return columns_df.columns.tolist()

def insert_data(table_name, data):
  connection = None
  cursor = None
  try:
    connection = get_db_connection()
    cursor = connection.cursor(buffered=True)

    # Columns present in the DataFrame
    df_cols = get_headers(data)

    # Align with actual DB table columns (exclude id and row_hash)
    cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 0")
    _ = cursor.fetchall()
    
    table_cols = [desc[0] for desc in cursor.description]
    # Keep only columns that exist in the table and are present in the df
    insert_cols = [c for c in table_cols if c in df_cols and c not in ("id", "row_hash")]

    # Reindex DataFrame to exact insert order
    df = data.reindex(columns=insert_cols).copy()

    # MySQL connector expects None for NULLs; cast to object first
    df = df.astype(object).where(pd.notna(df), None)

    rows_clean = [tuple(row) for row in df.itertuples(index=False, name=None)]

    placeholders = ", ".join(["%s"] * len(insert_cols))
    # IMPORTANT: quote column names with backticks
    columns_str = ", ".join([f"`{c}`" for c in insert_cols])

    sql = f"INSERT IGNORE INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"
    if rows_clean:
      cursor.executemany(sql, rows_clean)
      connection.commit()
    print(f"Inserted {cursor.rowcount if cursor else 0} rows into {table_name}")

  except mysql.connector.Error as err:
    print(f"Database error: {err}")
  finally:
    if connection and connection.is_connected():
        cursor.close()
        connection.close()
        print("MySQL connection closed")

def get_rows(table_name):
  connection = None
  cursor = None
  try:
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    results = cursor.fetchall()
    return results
  except mysql.connector.Error as err:
    print(f"❌ Database error: {err}")
  finally:
    if connection.is_connected():
      cursor.close()
      connection.close()
      print("MySQL connection closed")

def get_rows_with_columns(table_name):
  connection = None
  cursor = None
  try:
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    return results, columns
  except mysql.connector.Error as err:
    print(f"Database error: {err}")
  finally:
    if connection.is_connected():
      cursor.close()
      connection.close()
      print("MySQL connection closed")

def clear_table(table_name):
  connection = None
  cursor = None
  try:
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(f"DELETE FROM {table_name}")
    connection.commit()
  except mysql.connector.Error as err:
    print(f"Database error: {err}")
  finally:
    if connection.is_connected():
      cursor.close()
      connection.close()
      print("MySQL connection closed")

def test_connection():
  connection = None
  cursor = None
  try:
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT 1")
    results = cursor.fetchall()
  except mysql.connector.Error as err:
    print(f"Database error: {err}")
  finally:
    if connection.is_connected():
      cursor.close()
      connection.close()
      print("MySQL connection closed")
 
def get_table_columns(table_name):
  connection = None
  cursor = None
  try:
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
    cursor.fetchall() 
    columns = [desc[0] for desc in cursor.description]
    return columns
  except mysql.connector.Error as err:
    print(f"Database error: {err}")
    return []
  finally:
    if connection and connection.is_connected():
      cursor.close()
      connection.close()
      print("MySQL connection closed")

def delete_table(table_name):
  connection = None
  cursor = None
  try:
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    connection.commit()
    print(f"Table '{table_name}' deleted.")
  except mysql.connector.Error as err:
    print(f"Database error: {err}")
  finally:
    if connection and connection.is_connected():
      cursor.close()
      connection.close()
      print("MySQL connection closed")