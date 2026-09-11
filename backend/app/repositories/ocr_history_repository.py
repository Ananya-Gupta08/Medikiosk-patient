import json
import psycopg
from psycopg.rows import dict_row


class OcrHistoryRepository:
    """Reads OCR source data and writes only patient-owned correction rows."""
    def __init__(self, database_url: str): self.database_url=database_url

    def list_history(self, patient_id: str) -> list[dict]:
        query="""
        WITH sources AS (
          SELECT id,patient_id,document_type,clinical_document_date,extraction_timestamp,confidence_score,structured_data
          FROM public.medical_documents WHERE patient_id=%s
          UNION ALL
          SELECT id,patient_id,document_type,clinical_document_date,extraction_timestamp,confidence_score,structured_data
          FROM public.patient_pwa_demo_ocr_documents WHERE patient_id=%s
        )
        SELECT d.id,d.document_type,d.clinical_document_date,d.extraction_timestamp,
               d.confidence_score,d.structured_data,e.edited_history,e.updated_at AS patient_updated_at
        FROM sources d LEFT JOIN public.patient_pwa_history_edits e
          ON e.medical_document_id=d.id AND e.patient_id=d.patient_id
        ORDER BY COALESCE(d.clinical_document_date,d.extraction_timestamp::date) DESC,d.id
        """
        with psycopg.connect(self.database_url,connect_timeout=15) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query,(patient_id,patient_id)); rows=cursor.fetchall()
        return [self._map(row) for row in rows]

    def update_history(self, patient_id: str, document_id: str, edited_history: str) -> dict | None:
        with psycopg.connect(self.database_url,connect_timeout=15) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("""SELECT 1 FROM public.medical_documents WHERE id=%s AND patient_id=%s
                    UNION ALL SELECT 1 FROM public.patient_pwa_demo_ocr_documents WHERE id=%s AND patient_id=%s""",(document_id,patient_id,document_id,patient_id))
                if not cursor.fetchone(): return None
                cursor.execute("""INSERT INTO public.patient_pwa_history_edits
                    (patient_id,medical_document_id,edited_history) VALUES (%s,%s,%s)
                    ON CONFLICT(patient_id,medical_document_id) DO UPDATE
                    SET edited_history=excluded.edited_history,updated_at=now()""",(patient_id,document_id,edited_history))
            connection.commit()
        return next((item for item in self.list_history(patient_id) if item["id"]==document_id),None)

    def _map(self,row:dict)->dict:
        data=row["structured_data"] or {}
        if isinstance(data,str): data=json.loads(data)
        fields=("clinical_notes","findings","impression","diagnosis","final_diagnosis","extra_notes","remarks")
        sections=[]
        for field in fields:
            value=data.get(field)
            if value not in (None,"",[],{}):
                text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)
                sections.append(f"{field.replace('_',' ').title()}:\n{text}")
        extracted="\n\n".join(sections) or "No readable history was extracted from this document."
        return {"id":str(row["id"]),"document_type":row["document_type"],
            "document_date":(row["clinical_document_date"] or row["extraction_timestamp"].date()).isoformat(),
            "confidence_score":row["confidence_score"],"extracted_history":extracted,
            "patient_history":row["edited_history"] or extracted,"has_patient_edit":row["edited_history"] is not None,
            "patient_updated_at":row["patient_updated_at"].isoformat() if row["patient_updated_at"] else None}
