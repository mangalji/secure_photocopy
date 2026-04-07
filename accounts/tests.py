from django.test import TestCase
import hashlib
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .models import Shops, Document, OTP, PrintRequest, PrintSession, OAuthConnection, MFABackupCode, AuditLogs, Notification

User = get_user_model()


def make_user(email,phone,role='consumer',active=True):
    user = User.objects.create(
        email = email,
        full_name = 'test user',
        phone = phone,
        role = role,
        is_active = active,
        is_email_verified = active,
    )
    user.set_password('password123')
    user.save()
    return user

def get_access_token(user):
    return str(RefreshToken.for_user(user).access_token)


def generate_otp(user,purpose,raw='123456',minutes=5):
    return OTP.objects.create(
        user=user,
        otp_hash=hashlib.sha256(raw.encode()).hexdigest(),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=minutes)
    )

def make_shop(shopkeeper):
    return Shops.objects.create(
        shopkeeper = shopkeeper,
        shop_name = 'test shop',
        shop_email = 'shop@gmail.com',
        shop_phone = '9000000000',
        shop_address = 'sapna sangeeta',
        city='indore'
    )

def upload_document(consumer):
    return Document.objects.create(
        consumer = consumer,
        doc_name='test.pdf',
        encrypted_storage_ref = 'documents/1/test.pdf',
        encryption_key_ref    = 'local',
        file_hash             = 'abc123def456',
        doc_type              = 'application/pdf',
        file_size_mb          = 1,
    )

def generate_print_request(consumer,shop,document,expired=False):
    delta = timedelta(minutes=1) if expired else timedelta(minutes=30)
    return PrintRequest.objects.create(
        consumer = consumer,
        shop = shop,
        document = document,
        token_expires_at = timezone.now() + delta,
        expires_at = timezone.now() + delta
    )

class RegistrationTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('register')
        self.data = {
            'full_name':'raj mangal',
            'email':'raj@gmail.com',
            'phone':'1029384756',
            'address':'sapna sangeeta',
            'password':'password123',
            'confirm_password':'password123',
            'role':'consumer',
        }

    def post(self,data=None):
        return self.client.post(self.url,data or self.data,format='json')
    
    def test_register_consumer_successfully(self):
        response = self.post()
        self.assertEqual(response.status_code,status.HTTP_201_CREATED)
        self.assertIn('message',response.data)
        self.assertFalse(User.objects.get(email='raj@gmail.com').is_active)
        
    def test_register_shopkeeper_successfully(self):
        self.data['role'] = 'shopkeeper'
        response = self.post()
        self.assertEqual(response.status_code,status.HTTP_201_CREATED)

    def test_duplicate_active_email_blocked(self):
        make_user('raj@gmail.com','1029384756')
        response = self.post()
        self.assertDictEqual(response.status_code,status.HTTP_400_BAD_REQUEST)

    def test_unverified_email_allows_reregister(self):
        self.post()
        self.data['phone'] = '1029384756'
        response = self.post()
        self.assertDictEqual(response.status_code,status.HTTP_201_CREATED)

    def test_password_mismatch(self):
        self.data['confirm_password'] = 'wrongpassword'
        response = self.post()
        self.assertEqual(response.status_code,status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        self.data['password'] = self.data['confirm_password'] = 'abc'
        response = self.post()
        self.assertEqual(response.status_code,status.HTTP_400_BAD_REQUEST)

    def test_invalid_role_blocked(self):
        self.data['role'] = 'admin'
        response = self.post()
        self.assertEqual(response.status_code,status.HTTP_400_BAD_REQUEST)

    def test_duplicate_phone_blocked(self):
        make_user('other@test.com','9876543210')
        response = self.post()
        self.assertEqual(response.status_code,status.HTTP_400_BAD_REQUEST)

class OTPVerifyTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('verify-otp')
        self.raw_otp = '123456'
        self.user = User.objects.create(
            email = 'test@test.com',
            full_name = 'test',
            phone = '2020202020',
            role = 'consumer',
            is_active = False,
            is_email_verified = False
        )

        self.user.set_password('password123')
        self.user.save()
        generate_otp(self.user,'registration',self.raw_otp)

    def test_valid_otp_activates_account(self):
        response = self.client.post(self.url,{'email':"test@test.com",'otp':self.raw_otp},format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.is_email_verified)

    
    def test_otp_marked_used_after_verify(self):
        self.client.post(self.url, {'email': 'test@test.com', 'otp': self.raw_otp}, format='json')
        otp = OTP.objects.get(user=self.user)
        self.assertTrue(otp.is_used)
        self.assertIsNotNone(otp.used_at)
 
    def test_wrong_otp_rejected(self):
        res = self.client.post(self.url, {'email': 'test@test.com', 'otp': '000000'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
 
    def test_expired_otp_rejected(self):
        OTP.objects.filter(user=self.user).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        res = self.client.post(self.url, {'email': 'test@test.com', 'otp': self.raw_otp}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
 
    def test_already_active_account_blocked(self):
        self.user.is_active = True
        self.user.save()
        res = self.client.post(self.url, {'email': 'test@test.com', 'otp': self.raw_otp}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
 
    def test_used_otp_cannot_be_reused(self):
        self.client.post(self.url, {'email': 'test@test.com', 'otp': self.raw_otp}, format='json')
        res = self.client.post(self.url, {'email': 'test@test.com', 'otp': self.raw_otp}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
 
    def test_wrong_email(self):
        res = self.client.post(self.url, {'email': 'nobody@test.com', 'otp': self.raw_otp}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
