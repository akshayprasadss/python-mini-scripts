from rest_framework.test import APITestCase
from rest_framework import status
from core.models import CustomUser, Job, EmployerProfile


class TestAuth(APITestCase):

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="test@test.com",
            username="testuser",
            password="test123",
            role="CANDIDATE"
        )
        self.user.is_verified = True
        self.user.save()

    def test_login(self):
        response = self.client.post("/api/login/", {
            "email": "test@test.com",
            "password": "test123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestJob(APITestCase):

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="employer@test.com",
            username="employer1",
            password="candidate123",
            role="EMPLOYER"
        )

        self.employer_profile = EmployerProfile.objects.get(user=self.user)


        self.client.force_authenticate(user=self.user)

        Job.objects.create(
            title="Python Dev",
            skills="python",
            experience=1,
            employer=self.employer_profile
        )

    def test_job_list(self):
        response = self.client.get("/api/jobs/")
        self.assertEqual(response.status_code, 200)