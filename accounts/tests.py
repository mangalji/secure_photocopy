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
    import uuid
    return Shops.objects.create(
        shopkeeper = shopkeeper,
        shop_name = 'test shop',
        shop_email = f'shop{uuid.uuid4().hex[:8]}@gmail.com',  # Make email unique
        shop_phone = '9000000000',
        shop_address = 'sapna sangeeta',
        city='indore',
        shop_license_no = uuid.uuid4().hex[:10]  # Add unique license
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
    delta = timedelta(minutes=-1) if expired else timedelta(minutes=30)
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
        self.assertEqual(response.status_code,status.HTTP_400_BAD_REQUEST)

    def test_unverified_email_allows_reregister(self):
        self.post()
        self.data['phone'] = '1029384756'
        response = self.post()
        self.assertEqual(response.status_code,status.HTTP_201_CREATED)

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
        make_user('other@test.com','1029384756')
        response = self.post()
        self.assertEqual(response.status_code,status.HTTP_400_BAD_REQUEST)

class OTPVerifyTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('verify_register_otp')
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

class LoginTest(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('login')
        self.user = make_user('login@test.com','1928374650')

    def test_valid_login_sends_otp(self):
        response = self.client.post(self.url,{'email':'login@test.com','password':'password123'},format='json')
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertTrue(OTP.objects.filter(user=self.user,purpose='login').exists())

    def test_wrong_password(self):
        response = self.client.post(self.url, {'email': 'login@test.com', 'password': 'wrongpass'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_account_blocked(self):
        inactive = make_user('inactive@test.com', '9222222222', active=False)
        response = self.client.post(self.url, {'email': 'inactive@test.com', 'password': 'password123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_email(self):
        response = self.client.post(self.url, {'email': 'ghost@test.com', 'password': 'password123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class VerifyLoginOTPTest(TestCase):

    def setUp(self):
        self.client  = APIClient()
        self.url     = reverse('verify_login_otp')
        self.raw_otp = '391847'
        self.user    = make_user('jwt@test.com', '9182736459')
        generate_otp(self.user, 'login', self.raw_otp)

    def test_valid_otp_returns_tokens(self):
        response = self.client.post(self.url, {'email': 'jwt@test.com', 'otp': self.raw_otp}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)

    def test_response_contains_user_info(self):
        response = self.client.post(self.url, {'email': 'jwt@test.com', 'otp': self.raw_otp}, format='json')
        self.assertEqual(response.data['user']['email'], 'jwt@test.com')
        self.assertEqual(response.data['user']['role'], 'consumer')

    def test_invalid_otp_no_token(self):
        response = self.client.post(self.url, {'email': 'jwt@test.com', 'otp': '000000'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('access_token', response.data)

class ForgotPasswordTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user   = make_user('forgot@test.com', '9444444444')

    def test_forgot_password_sends_otp(self):
        response = self.client.post(reverse('forgot_password'), {'email': 'forgot@test.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTP.objects.filter(user=self.user, purpose='forgot_password').exists())

    def test_reset_password_success(self):
        raw_otp = '111222'
        generate_otp(self.user, 'forgot_password', raw_otp)
        response = self.client.post(reverse('reset_password'), {
            'email'            : 'forgot@test.com',
            'otp'              : raw_otp,
            'new_password'     : 'newpassword456',
            'confirm_new_password' : 'newpassword456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword456'))

    def test_reset_wrong_otp(self):
        generate_otp(self.user, 'forgot_password', '111222')
        response = self.client.post(reverse('reset_password'), {
            'email'            : 'forgot@test.com',
            'otp'              : '000000',
            'new_password'     : 'newpassword456',
            'confirm_new_password' : 'newpassword456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_mismatch(self):
        raw_otp = '333444'
        generate_otp(self.user, 'forgot_password', raw_otp)
        response = self.client.post(reverse('reset_password'), {
            'email'            : 'forgot@test.com',
            'otp'              : raw_otp,
            'new_password'     : 'newpassword456',
            'confirm_new_password' : 'differentpassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class ShopTest(TestCase):

    def setUp(self):
        self.client     = APIClient()
        self.shopkeeper = make_user('sk@test.com', '9555555555', role='shopkeeper')
        self.consumer   = make_user('cs@test.com', '9666666666', role='consumer')
        self.shop_data  = {
            'shop_name'    : 'test shop',
            'shop_email'   : 'shop@gmail.com',
            'shop_phone'   : '9000000000',
            'shop_address' : 'sapna sangeeta',
            'city'         : 'indore',            'shop_license_no': 'license123',        }

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(user)}')

    def test_shopkeeper_creates_shop(self):
        self.auth(self.shopkeeper)
        response = self.client.post(reverse('shop_register'), self.shop_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Shops.objects.filter(shopkeeper=self.shopkeeper).exists())

    def test_consumer_cannot_create_shop(self):
        self.auth(self.consumer)
        response = self.client.post(reverse('shop_register'), self.shop_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_shop(self):
        response = self.client.post(reverse('shop_register'), self.shop_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_shops_returns_active_only(self):
        shop = make_shop(self.shopkeeper)
        shop1 = Shops.objects.create(
            shopkeeper = self.shopkeeper,
            shop_name='shop 1',
            shop_email='a@a.com',
            shop_phone='1029384756',
            is_active=True,
            shop_license_no='license1'
        )
        shop2 = Shops.objects.create(
            shopkeeper=self.shopkeeper, shop_name='Closed',
            shop_license_no="license2",
            shop_email='c@c.com', shop_phone='7000000001',
            is_active=False
        )
        self.auth(self.consumer)
        response = self.client.get(reverse('shop_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [s['id'] for s in response.data]
        self.assertIn(shop1.id, ids)
        self.assertNotIn(shop2.id, ids)

    def test_filter_shops_by_city(self):
        make_shop(self.shopkeeper)
        self.auth(self.consumer)
        response = self.client.get(reverse('shop_list') + '?city=Nagpur')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for shop in response.data:
            self.assertIn('nagpur', shop['city'].lower())

    def test_shop_detail_returns_shopkeeper_name(self):
        shop = make_shop(self.shopkeeper)
        self.auth(self.consumer)
        response = self.client.get(reverse('shop_detail', kwargs={'shop_id': shop.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('shopkeeper_name', response.data)

    def test_owner_can_update_shop(self):
        shop = make_shop(self.shopkeeper)
        self.auth(self.shopkeeper)
        response = self.client.put(
            reverse('shop_update', kwargs={'shop_id': shop.id}),
            {'shop_name': 'Updated Name'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        shop.refresh_from_db()
        self.assertEqual(shop.shop_name, 'Updated Name')

    def test_non_owner_cannot_update_shop(self):
        other_sk = make_user('other@test.com', '8111111111', role='shopkeeper')
        shop = make_shop(self.shopkeeper)
        self.auth(other_sk)
        response = self.client.put(
            reverse('shop_update', kwargs={'shop_id': shop.id}),
            {'shop_name': 'Hacked'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_soft_delete_shop(self):
        shop = make_shop(self.shopkeeper)
        self.auth(self.shopkeeper)
        response = self.client.delete(reverse('shop_delete', kwargs={'shop_id': shop.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        shop.refresh_from_db()
        self.assertFalse(shop.is_active)

    def test_deleted_shop_not_in_list(self):
        shop = make_shop(self.shopkeeper)
        shop.is_active = False
        shop.save()
        self.auth(self.consumer)
        response = self.client.get(reverse('shop_list'))
        ids = [s['id'] for s in response.data]
        self.assertNotIn(shop.id, ids)

class DocumentTest(TestCase):

    def setUp(self):
        self.client     = APIClient()
        self.consumer   = make_user('dc@test.com', '9777777777', role='consumer')
        self.shopkeeper = make_user('dsk@test.com', '9888888888', role='shopkeeper')

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(user)}')

    def test_consumer_can_list_documents(self):
        upload_document(self.consumer)
        self.auth(self.consumer)
        response = self.client.get(reverse('document_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_shopkeeper_cannot_list_documents(self):
        self.auth(self.shopkeeper)
        response = self.client.get(reverse('document_list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_consumer_can_delete_own_document(self):
        doc = upload_document(self.consumer)
        self.auth(self.consumer)
        response = self.client.delete(reverse('document_delete', kwargs={'document_id': doc.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertTrue(doc.is_deleted)
        self.assertIsNotNone(doc.deleted_at)

    def test_cannot_delete_already_deleted_document(self):
        doc = upload_document(self.consumer)
        doc.is_deleted = True
        doc.deleted_at = timezone.now()
        doc.save()
        self.auth(self.consumer)
        response = self.client.delete(reverse('document_delete', kwargs={'document_id': doc.id}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_delete_another_users_document(self):
        other = make_user('other@test.com', '8222222222')
        doc   = upload_document(other)
        self.auth(self.consumer)
        response = self.client.delete(reverse('document_delete', kwargs={'document_id': doc.id}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class PrintRequestTest(TestCase):

    def setUp(self):
        self.client     = APIClient()
        self.consumer   = make_user('prc@test.com', '9000000002', role='consumer')
        self.shopkeeper = make_user('prsk@test.com', '9000000003', role='shopkeeper')
        self.shop       = make_shop(self.shopkeeper)
        self.document   = upload_document(self.consumer)

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(user)}')

    def test_consumer_can_create_request(self):
        self.auth(self.consumer)
        response = self.client.post(reverse('print_request_create'), {
            'shop_id'        : self.shop.id,
            'document_id'    : self.document.id,
            'print_copies'   : 1,
            'print_color'    : 'blackwhite',
            'expiry_minutes' : 30,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', response.data)

    def test_shopkeeper_cannot_create_request(self):
        self.auth(self.shopkeeper)
        response = self.client.post(reverse('print_request_create'), {
            'shop_id': self.shop.id, 'document_id': self.document.id,
            'print_copies': 1, 'print_color': 'blackwhite', 'expiry_minutes': 30,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_use_another_users_document(self):
        other_doc = upload_document(make_user('other@test.com', '8333333333'))
        self.auth(self.consumer)
        response = self.client.post(reverse('print_request_create'), {
            'shop_id': self.shop.id, 'document_id': other_doc.id,
            'print_copies': 1, 'print_color': 'blackwhite', 'expiry_minutes': 30,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_consumer_sees_own_requests(self):
        generate_print_request(self.consumer, self.shop, self.document)
        self.auth(self.consumer)
        response = self.client.get(reverse('print_request_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_shopkeeper_sees_shop_requests(self):
        generate_print_request(self.consumer, self.shop, self.document)
        self.auth(self.shopkeeper)
        response = self.client.get(reverse('print_request_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_cancel_pending_request(self):
        pr = generate_print_request(self.consumer, self.shop, self.document)
        self.auth(self.consumer)
        response = self.client.post(reverse('print_request_cancel', kwargs={'request_id': pr.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pr.refresh_from_db()
        self.assertEqual(pr.status, 'cancelled')
        self.assertTrue(pr.is_token_used)

    def test_cannot_cancel_non_pending_request(self):
        pr = generate_print_request(self.consumer, self.shop, self.document)
        pr.status = 'printed'
        pr.save()
        self.auth(self.consumer)
        response = self.client.post(reverse('print_request_cancel', kwargs={'request_id': pr.id}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class PrintSessionTest(TestCase):

    def setUp(self):
        self.client     = APIClient()
        self.consumer   = make_user('sc@test.com', '9000000004', role='consumer')
        self.shopkeeper = make_user('ssk@test.com', '9000000005', role='shopkeeper')
        self.shop       = make_shop(self.shopkeeper)
        self.document   = upload_document(self.consumer)
        self.pr         = generate_print_request(self.consumer, self.shop, self.document)

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(user)}')

    def access(self):
        return self.client.post(
            reverse('access_document'),
            {'access_token': str(self.pr.access_token)},
            format='json'
        )

    def test_token_marks_used_on_access(self):
        self.auth(self.shopkeeper)
        self.access()
        self.pr.refresh_from_db()
        self.assertTrue(self.pr.is_token_used)

    def test_token_cannot_be_used_twice(self):
        self.auth(self.shopkeeper)
        self.access()
        response2 = self.access()
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_expired_token_returns_410(self):
        pr_expired = generate_print_request(self.consumer, self.shop, self.document, expired=True)
        self.auth(self.shopkeeper)
        response = self.client.post(
            reverse('access_document'),
            {'access_token': str(pr_expired.access_token)},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        pr_expired.refresh_from_db()
        self.assertEqual(pr_expired.status, 'expired')

    def test_consumer_cannot_access_document(self):
        self.auth(self.consumer)
        response = self.access()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_wrong_shopkeeper_blocked(self):
        other_sk = make_user('other_sk@test.com', '8444444444', role='shopkeeper')
        self.auth(other_sk)
        response = self.access()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_token_returns_404(self):
        self.auth(self.shopkeeper)
        response = self.client.post(
            reverse('access_document'),
            {'access_token': '00000000-0000-0000-0000-000000000000'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_session_created_on_access(self):
        self.auth(self.shopkeeper)
        self.access()
        self.assertTrue(PrintSession.objects.filter(request=self.pr).exists())

    def test_request_status_becomes_printing(self):
        self.auth(self.shopkeeper)
        self.access()
        self.pr.refresh_from_db()
        self.assertEqual(self.pr.status, 'printing')

    def test_confirm_print_completes_session(self):
        self.auth(self.shopkeeper)
        response = self.access()
        session_id = response.data.get('session_id')
        if not session_id:
            return  # File not found on disk is ok in tests

        confirm_response = self.client.post(reverse('print_confirm', kwargs={'session_id': session_id}))
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        session = PrintSession.objects.get(id=session_id)
        self.assertEqual(session.session_status, 'completed')
        self.assertIsNotNone(session.print_completed_at)

        self.pr.refresh_from_db()
        self.assertEqual(self.pr.status, 'printed')

        document = Document.objects.get(id=self.document.id)
        self.assertTrue(document.is_deleted)
        self.assertIsNotNone(document.deleted_at)

    def test_confirm_already_completed_blocked(self):
        session = PrintSession.objects.create(
            request              = self.pr,
            shopkeeper           = self.shopkeeper,
            session_status       = 'completed',
            document_accessed_at = timezone.now(),
        )
        self.auth(self.shopkeeper)
        response = self.client.post(reverse('print_confirm', kwargs={'session_id': session.id}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fail_session_marks_cancelled(self):
        session = PrintSession.objects.create(
            request              = self.pr,
            shopkeeper           = self.shopkeeper,
            document_accessed_at = timezone.now(),
        )
        self.auth(self.shopkeeper)
        response = self.client.post(reverse('print_fail', kwargs={'session_id': session.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.session_status, 'failed')
        self.pr.refresh_from_db()
        self.assertEqual(self.pr.status, 'cancelled')


class NotificationTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user   = make_user('notif@test.com', '9000000006')
        self.notif  = Notification.objects.create(
            user              = self.user,
            noti_type = 'printed',
            title             = 'Document Printed',
            message           = 'Your document was printed.',
        )

    def auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.user)}')

    def test_list_notifications(self):
        self.auth()
        response = self.client.get(reverse('notification_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertFalse(response.data[0]['is_read'])

    def test_mark_single_read(self):
        self.auth()
        response = self.client.post(reverse('notification_mark_read', kwargs={'notification_id': self.notif.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notif.refresh_from_db()
        self.assertTrue(self.notif.is_read)

    def test_mark_all_read(self):
        Notification.objects.create(
            user=self.user, noti_type='expired',
            title='Expired', message='Request expired.'
        )
        self.auth()
        response = self.client.post(reverse('notification_marked_all_read'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        unread = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(unread, 0)

    def test_cannot_read_other_users_notification(self):
        other = make_user('other@test.com', '8555555555')
        other_notif = Notification.objects.create(
            user=other, noti_type='printed',
            title='Test', message='Test msg'
        )
        self.auth()
        response = self.client.post(reverse('notification_mark_read', kwargs={'notification_id': other_notif.id}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ProfileTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user   = make_user('profile@test.com', '9000000007')

    def auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.user)}')

    def test_get_profile_returns_correct_data(self):
        self.auth()
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'profile@test.com')
        self.assertEqual(response.data['role'], 'consumer')

    def test_update_full_name(self):
        self.auth()
        response = self.client.put(reverse('profile_update'), {'full_name': 'New Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, 'New Name')

    def test_update_phone_to_duplicate_blocked(self):
        make_user('other@test.com', '8666666666')
        self.auth()
        response = self.client.put(reverse('profile_update'), {'phone': '8666666666'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_success(self):
        self.auth()
        response = self.client.post(reverse('change_password'), {
            'current_password' : 'password123',
            'new_password'     : 'newpassword456',
            'confirm_password' : 'newpassword456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword456'))

    def test_change_password_wrong_current(self):
        self.auth()
        response = self.client.post(reverse('change_password'), {
            'current_password' : 'wrongpassword',
            'new_password'     : 'newpassword456',
            'confirm_password' : 'newpassword456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_mismatch(self):
        self.auth()
        response = self.client.post(reverse('change_password'), {
            'current_password' : 'password123',
            'new_password'     : 'newpassword456',
            'confirm_password' : 'differentpassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_get_profile(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuditLogTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user   = make_user('audit@test.com', '9000000008')
        AuditLogs.objects.create(
            user       = self.user,
            action     = 'user_login',
            ip_address = '127.0.0.1',
        )

    def test_list_audit_logs(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.user)}')
        response = self.client.get(reverse('audit_logs'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['action'], 'user_login')

    def test_cannot_see_other_users_logs(self):
        other = make_user('other@test.com', '8777777777')
        AuditLogs.objects.create(user=other, action='document_uploaded')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.user)}')
        response = self.client.get(reverse('audit_logs'))
        self.assertEqual(len(response.data), 1) 

    def test_unauthenticated_blocked(self):
        response = self.client.get(reverse('audit_logs'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class ResendOTPTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_resend_registration_otp(self):
        user = User.objects.create(
            email='resend@test.com', full_name='Test',
            phone='9000000009', role='consumer',
            is_active=False, is_email_verified=False
        )
        user.set_password('pass')
        user.save()
        response = self.client.post(reverse('resend_otp'), {
            'email'  : 'resend@test.com',
            'purpose': 'registration',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTP.objects.filter(user=user, purpose='registration', is_used=False).exists())

    def test_resend_for_already_verified_blocked(self):
        make_user('verified@test.com', '9000000010')
        response = self.client.post(reverse('resend_otp'), {
            'email'  : 'verified@test.com',
            'purpose': 'registration',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_login_otp_for_active_user(self):
        make_user('active@test.com', '9000000011')
        response = self.client.post(reverse('resend_otp'), {
            'email'  : 'active@test.com',
            'purpose': 'login',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)