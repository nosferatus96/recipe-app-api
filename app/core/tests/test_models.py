from django.test import TestCase
from django.contrib.auth import get_user_model


class ModelTests(TestCase):

    def test_create_user_with_email_successful(self):
        """Test creating new user with good email"""
        email = 'jonathannb123@hotmail.com'
        password = 'totop900'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test the email for a new user is normalized"""
        email = 'jonathannb123@hotmail.com'
        user = get_user_model().objects.create_user(email, 'totop900')

        self.assertEqual(user.email, email.lower())
