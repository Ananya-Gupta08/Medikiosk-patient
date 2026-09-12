export type Occurrence={id:string;medication_id:string;medication_name:string;dosage:string;quantity:string;instructions?:string;scheduled_at:string;time_source:string;status:'pending'|'taken';completed_at?:string}
export type Medication={id:string;name:string;dosage:string;quantity:string;frequency:string;times_per_day:number;duration_days?:number|null;start_date:string;instructions?:string;exact_times?:string[]}
export type Consultation={id:string;occurred_at:string;doctor:{id?:string;name:string};location?:string;diagnosis:string;medications:Medication[];prescription_document_url?:string}
export type Dashboard={patient:{id:string;name:string};date:string;medications:Occurrence[];recent_consultation?:Consultation;checkin_due:boolean}
export type Session={id:string;status:'active'|'complete';diagnosis_value:string;started_at:string}
export type ChatMessage={id:string;role:'patient'|'assistant';message:string;created_at:string}
export type HistoryDocument={id:string;document_type:string;document_date:string;confidence_score:number;extracted_history:string;patient_history:string;has_patient_edit:boolean;patient_updated_at?:string}
