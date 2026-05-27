from locust import HttpUser, task, between

class UsuarioDeCarga(HttpUser):
    wait_time = between(1, 3)

    @task
    def hacer_inferencia(self):
        payload = {
            "race": "Caucasian",
            "gender": "Female",
            "age": "[50-60)",
            "weight": "?",
            "admission_type_id": 1,
            "discharge_disposition_id": 1,
            "admission_source_id": 7,
            "time_in_hospital": 3,
            "payer_code": "?",
            "medical_specialty": "InternalMedicine",
            "num_lab_procedures": 40,
            "num_procedures": 1,
            "num_medications": 15,
            "number_outpatient": 0,
            "number_emergency": 0,
            "number_inpatient": 0,
            "diag_1": "250.7",
            "diag_2": "402",
            "diag_3": "401",
            "number_diagnoses": 9,
            "max_glu_serum": "None",
            "A1Cresult": "None",
            "metformin": "No",
            "repaglinide": "No",
            "nateglinide": "No",
            "chlorpropamide": "No",
            "glimepiride": "No",
            "acetohexamide": "No",
            "glipizide": "No",
            "glyburide": "No",
            "tolbutamide": "No",
            "pioglitazone": "No",
            "rosiglitazone": "No",
            "acarbose": "No",
            "miglitol": "No",
            "troglitazone": "No",
            "tolazamide": "No",
            "examide": "No",
            "citoglipton": "No",
            "insulin": "No",
            "glyburide_metformin": 0.0,
            "glipizide_metformin": 0.0,
            "glimepiride_pioglitazone": 0.0,
            "metformin_rosiglitazone": 0.0,
            "metformin_pioglitazone": 0.0,
            "change_m": 0.0,
            "diabetesMed": "No"
        }
        # Enviar una petición POST al endpoint /predict
        with self.client.post("/predict", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Error {response.status_code}: {response.text}")
