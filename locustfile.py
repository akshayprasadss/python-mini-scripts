from locust import HttpUser, task, between

class MyUser(HttpUser):
    host = "http://127.0.0.1:8000"
    wait_time = between(1, 2)

    def on_start(self):
        self.token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc1MTEzNjY2LCJpYXQiOjE3NzUxMTI3NjYsImp0aSI6IjYwZTExMGRhODFlYjRhMTI5MTFmMjU0ZWI5NWFkOTdjIiwidXNlcl9pZCI6IjQifQ.cnRGwC2exFThvBYLbsO9dxsxRPaVvPCdaBjlOyFO--Y"

    @task
    def job_list(self):
        self.client.get(
            "/api/jobs/",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task
    def my_applications(self):
        self.client.get(
            "/api/applications/my/",
            headers={"Authorization": f"Bearer {self.token}"}
        )