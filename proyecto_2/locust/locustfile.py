from locust import task, between
from locust.contrib.fasthttp import FastHttpUser

class UsuarioDeCarga(FastHttpUser):
    # Tiempo de espera entre tareas por usuario simulado (en segundos)
    wait_time = between(1, 3)
    connections = 800         # pool grande por worker
    max_reqs_per_conn = 0 
    @task
    def hacer_inferencia(self):
        payload = {
            "encounter_id": 39877476,
            "patient_nbr": 4226301,
            "race": "Caucasian",
            "gender": "Male",
            "age": "[50-60)",
            "weight": "",
            "admission_type_id": 1,
            "discharge_disposition_id": 1,
            "admission_source_id": 7,
            "time_in_hospital": 2,
            "payer_code": "",
            "medical_specialty": "Family/GeneralPractice",
            "num_lab_procedures": 35,
            "num_procedures": 0,
            "num_medications": 7,
            "number_outpatient": 0,
            "number_emergency": 0,
            "number_inpatient": 0,
            "diag_1": "434",
            "diag_2": "250.52",
            "diag_3": "250.42",
            "number_diagnoses": 9,
            "max_glu_serum": "",
            "A1Cresult": "",
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
            "diabetesMed": "YES"
            }
 
        # Enviar una petición POST al endpoint /predict
        # response = self.client.get("/models", json=payload)
        response = self.client.post("/predict", json=payload)
        # Opcional: validación de respuesta
        if response.status_code != 200:
            print("Error en la inferencia:", response.text)
