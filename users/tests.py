from django.test import TestCase, Client
from .models import CustomUser

class UserAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = '/users/register/'
        self.login_url = '/users/login/'
        self.user_data = {'email': 'test@example.com', 'password': 'password123'}

    def test_register_user(self):
        response = self.client.post(self.register_url, self.user_data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(CustomUser.objects.count(), 1)

    def test_register_user_existing_email(self):
        CustomUser.objects.create_user(**self.user_data)
        response = self.client.post(self.register_url, self.user_data, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_login_user(self):
        CustomUser.objects.create_user(**self.user_data)
        response = self.client.post(self.login_url, self.user_data, content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_login_user_invalid_credentials(self):
        response = self.client.post(self.login_url, self.user_data, content_type='application/json')
        self.assertEqual(response.status_code, 401)
