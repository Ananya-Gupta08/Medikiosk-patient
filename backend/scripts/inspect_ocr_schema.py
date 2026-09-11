"""Read-only discovery of columns that may contain extracted medical history."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from app.config import get_settings
import psycopg


QUERY = """
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND (
    lower(table_name) LIKE '%%ocr%%'
    OR lower(column_name) LIKE '%%ocr%%'
    OR lower(column_name) LIKE '%%history%%'
    OR lower(column_name) LIKE '%%extract%%'
  )
ORDER BY table_schema, table_name, ordinal_position
"""

DOCUMENT_COLUMNS = """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='public' AND table_name='medical_documents'
ORDER BY ordinal_position
"""

JSON_KEYS = """
SELECT DISTINCT jsonb_object_keys(complete_ocr_result) AS key
FROM public.medical_documents
WHERE complete_ocr_result IS NOT NULL
ORDER BY key
"""

NESTED_KEYS = """
SELECT DISTINCT source, key FROM (
  SELECT 'structured_data' source, jsonb_object_keys(structured_data) key
  FROM public.medical_documents WHERE jsonb_typeof(structured_data)='object'
  UNION ALL
  SELECT 'clinical_summary', jsonb_object_keys(complete_ocr_result->'clinical_summary')
  FROM public.medical_documents WHERE jsonb_typeof(complete_ocr_result->'clinical_summary')='object'
  UNION ALL
  SELECT 'data', jsonb_object_keys(complete_ocr_result->'data')
  FROM public.medical_documents WHERE jsonb_typeof(complete_ocr_result->'data')='object'
  UNION ALL
  SELECT 'structured_document', jsonb_object_keys(complete_ocr_result->'structured_document')
  FROM public.medical_documents WHERE jsonb_typeof(complete_ocr_result->'structured_document')='object'
) keys ORDER BY source,key
"""


with psycopg.connect(get_settings().patient_pwa_database_url, connect_timeout=15) as connection:
    with connection.cursor() as cursor:
        cursor.execute(QUERY)
        for row in cursor.fetchall():
            print(" | ".join(str(value) for value in row))
        print("-- medical_documents columns --")
        cursor.execute(DOCUMENT_COLUMNS)
        for row in cursor.fetchall():
            print(" | ".join(str(value) for value in row))
        print("-- complete_ocr_result top-level keys --")
        cursor.execute(JSON_KEYS)
        for row in cursor.fetchall():
            print(row[0])
        print("-- nested OCR key names --")
        cursor.execute(NESTED_KEYS)
        for row in cursor.fetchall():
            print(" | ".join(row))
