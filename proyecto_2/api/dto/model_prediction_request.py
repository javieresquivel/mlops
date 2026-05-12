from pydantic import BaseModel

class ModelPredictionRequest(BaseModel):
    encounter_id: int | None = None
    patient_nbr: int | None = None
    race: str | None
    gender: str | None
    age: str | None
    weight: str | None
    admission_type_id: int
    discharge_disposition_id: int
    admission_source_id: int
    time_in_hospital: int
    payer_code: str | None
    medical_specialty: str | None
    num_lab_procedures: int
    num_procedures: int
    num_medications: int
    number_outpatient: int
    number_emergency: int
    number_inpatient: int
    diag_1: str | None
    diag_2: str | None
    diag_3: str | None
    number_diagnoses: int
    max_glu_serum: str
    A1Cresult: str

    # ---------- medication flags (full list)
    metformin: str
    repaglinide: str
    nateglinide: str
    chlorpropamide: str
    glimepiride: str
    acetohexamide: str
    glipizide: str
    glyburide: str
    tolbutamide: str
    pioglitazone: str
    rosiglitazone: str
    acarbose: str
    miglitol: str
    troglitazone: str
    tolazamide: str
    examide: str
    citoglipton: str
    insulin: str

    # combinations
    glyburide_metformin: float
    glipizide_metformin: float
    glimepiride_pioglitazone: float
    metformin_rosiglitazone: float
    metformin_pioglitazone: float

    # flags
    change_m: float | None = None
    diabetesMed: str


NORMALIZED_COLUMNS = [
    'num__time_in_hospital',
    'num__num_lab_procedures',
    'num__num_procedures',
    'num__num_medications',
    'num__number_outpatient',
    'num__number_emergency',
    'num__number_inpatient',
    'num__number_diagnoses',
    'base_cat__gender_Female',
    'base_cat__gender_Male',
    'base_cat__admission_type_id_1',
    'base_cat__admission_type_id_2',
    'base_cat__admission_type_id_3',
    'base_cat__admission_type_id_4',
    'base_cat__admission_type_id_5',
    'base_cat__admission_type_id_6',
    'base_cat__admission_type_id_8',
    'base_cat__discharge_disposition_id_1',
    'base_cat__discharge_disposition_id_2',
    'base_cat__discharge_disposition_id_3',
    'base_cat__discharge_disposition_id_4',
    'base_cat__discharge_disposition_id_5',
    'base_cat__discharge_disposition_id_6',
    'base_cat__discharge_disposition_id_7',
    'base_cat__discharge_disposition_id_8',
    'base_cat__discharge_disposition_id_10',
    'base_cat__discharge_disposition_id_11',
    'base_cat__discharge_disposition_id_12',
    'base_cat__discharge_disposition_id_13',
    'base_cat__discharge_disposition_id_14',
    'base_cat__discharge_disposition_id_16',
    'base_cat__discharge_disposition_id_18',
    'base_cat__discharge_disposition_id_25',
    'base_cat__admission_source_id_1',
    'base_cat__admission_source_id_2',
    'base_cat__admission_source_id_3',
    'base_cat__admission_source_id_4',
    'base_cat__admission_source_id_5',
    'base_cat__admission_source_id_6',
    'base_cat__admission_source_id_7',
    'base_cat__admission_source_id_8',
    'base_cat__admission_source_id_17',
    'base_cat__admission_source_id_20',
    'base_cat__max_glu_serum_',
    'base_cat__max_glu_serum_>200',
    'base_cat__max_glu_serum_>300',
    'base_cat__max_glu_serum_Norm',
    'base_cat__A1Cresult_',
    'base_cat__A1Cresult_>7',
    'base_cat__A1Cresult_>8',
    'base_cat__A1Cresult_Norm',
    'base_cat__race_?',
    'base_cat__race_AfricanAmerican',
    'base_cat__race_Asian',
    'base_cat__race_Caucasian',
    'base_cat__race_Hispanic',
    'base_cat__race_Other',
    'base_cat__age_[0-10)',
    'base_cat__age_[10-20)',
    'base_cat__age_[20-30)',
    'base_cat__age_[30-40)',
    'base_cat__age_[40-50)',
    'base_cat__age_[50-60)',
    'base_cat__age_[60-70)',
    'base_cat__age_[70-80)',
    'base_cat__age_[80-90)',
    'base_cat__age_[90-100)',
    'meds__metformin',
    'meds__repaglinide',
    'meds__nateglinide',
    'meds__chlorpropamide',
    'meds__glimepiride',
    'meds__acetohexamide',
    'meds__glipizide',
    'meds__glyburide',
    'meds__tolbutamide',
    'meds__pioglitazone',
    'meds__rosiglitazone',
    'meds__acarbose',
    'meds__miglitol',
    'meds__troglitazone',
    'meds__tolazamide',
    'meds__insulin',
    'meds__glyburide_metformin',
    'meds__glipizide_metformin',
    'meds__glimepiride_pioglitazone',
    'meds__metformin_rosiglitazone',
    'meds__metformin_pioglitazone',
    'meds__change_m',
    'meds__diabetesMed',
    'diag__diag_1_Circulatory',
    'diag__diag_1_Diabetes_250',
    'diag__diag_1_Digestive',
    'diag__diag_1_Endocrine_Nutrition',
    'diag__diag_1_Genitourinary',
    'diag__diag_1_Musculoskeletal',
    'diag__diag_1_Other',
    'diag__diag_1_Respiratory',
    'diag__diag_1_Supplementary_V',
    'diag__diag_1_Symptoms_Signs',
    'diag__diag_1_infrequent_sklearn',
    'diag__diag_2_Circulatory',
    'diag__diag_2_Diabetes_250',
    'diag__diag_2_Digestive',
    'diag__diag_2_Endocrine_Nutrition',
    'diag__diag_2_Genitourinary',
    'diag__diag_2_Injury_E',
    'diag__diag_2_Musculoskeletal',
    'diag__diag_2_Other',
    'diag__diag_2_Respiratory',
    'diag__diag_2_Supplementary_V',
    'diag__diag_2_Symptoms_Signs',
    'diag__diag_2_Unknown',
    'diag__diag_3_Circulatory',
    'diag__diag_3_Diabetes_250',
    'diag__diag_3_Digestive',
    'diag__diag_3_Endocrine_Nutrition',
    'diag__diag_3_Genitourinary',
    'diag__diag_3_Injury_E',
    'diag__diag_3_Musculoskeletal',
    'diag__diag_3_Other',
    'diag__diag_3_Respiratory',
    'diag__diag_3_Supplementary_V',
    'diag__diag_3_Symptoms_Signs',
    'diag__diag_3_Unknown'
    ]
