from locust import HttpUser, task, between

class UsuarioDeCarga(HttpUser):
    wait_time = between(1, 3)

    @task
    def hacer_inferencia(self):
        payload = {
            'brokered_by': 101640.0, 
            'status': 'for_sale', 
            'price': 289900.0, 
            'bed': 4.0, 
            'bath': 2.0, 
            'acre_lot': 0.38, 
            'street': 1758218.0, 
            'city': 'East Windsor', 
            'state': 'Connecticut', 
            'zip_code': 6016.0, 
            'house_size': 1617.0, 
            'prev_sold_date': '1999-09-30'
        } 
        # Enviar una petición POST al endpoint /predict
        with self.client.post("/predict", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Error {response.status_code}: {response.text}")
