"""
Security regression tests — NumbersCard owner scope + ManualPayment review.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from users.models import User
from business.models import Business
from payments.models import NumbersCard, ManualPayment


class NumbersCardOwnerScopeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner_a = User.objects.create_user(
            phone_number='09111111111', password='pass1234',
            first_name='Owner', last_name='A', is_owner=True
        )
        self.owner_b = User.objects.create_user(
            phone_number='09222222222', password='pass1234',
            first_name='Owner', last_name='B', is_owner=True
        )
        self.customer = User.objects.create_user(
            phone_number='09333333333', password='pass1234',
            first_name='Customer', last_name='C'
        )
        self.business_a = Business.objects.create(
            owner=self.owner_a, name='Salon A', slug='salon-a',
            business_type='male_salon', address='Addr A',
            telephone_number='021111', phone_number='09111111111',
            is_active=True, random_code='111111'
        )
        self.business_b = Business.objects.create(
            owner=self.owner_b, name='Salon B', slug='salon-b',
            business_type='female_salon', address='Addr B',
            telephone_number='021222', phone_number='09222222222',
            is_active=True, random_code='222222'
        )
        self.card_a = NumbersCard.objects.create(
            business=self.business_a, num_code='6037991111111111',
            name_bank='Bank A', card_holder_name='Owner A', status=True
        )
        self.card_b = NumbersCard.objects.create(
            business=self.business_b, num_code='6037992222222222',
            name_bank='Bank B', card_holder_name='Owner B', status=True
        )

    def test_owner_a_sees_only_own_cards(self):
        self.client.force_authenticate(user=self.owner_a)
        response = self.client.get(reverse('numberscard-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data if isinstance(response.data, list) else response.data.get('results', [])
        ids = [c['id'] for c in data]
        self.assertIn(self.card_a.id, ids)
        self.assertNotIn(self.card_b.id, ids)

    def test_owner_a_cannot_edit_card_b(self):
        self.client.force_authenticate(user=self.owner_a)
        response = self.client.patch(
            reverse('numberscard-detail', kwargs={'pk': self.card_b.pk}),
            {'name_bank': 'Hacked'},
            format='json',
        )
        self.assertIn(response.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

    def test_customer_lists_active_cards_by_code(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(
            reverse('numberscard-list-by-code', kwargs={'random_code': '111111'})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data if isinstance(response.data, list) else response.data.get('results', [])
        ids = [c['id'] for c in data]
        self.assertIn(self.card_a.id, ids)
        self.assertNotIn(self.card_b.id, ids)


class ManualPaymentReviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner_a = User.objects.create_user(
            phone_number='09111111111', password='pass1234',
            first_name='Owner', last_name='A', is_owner=True
        )
        self.owner_b = User.objects.create_user(
            phone_number='09222222222', password='pass1234',
            first_name='Owner', last_name='B', is_owner=True
        )
        self.customer = User.objects.create_user(
            phone_number='09333333333', password='pass1234',
            first_name='Customer', last_name='C'
        )
        self.business_a = Business.objects.create(
            owner=self.owner_a, name='Salon A', slug='salon-a',
            business_type='male_salon', address='Addr A',
            telephone_number='021111', phone_number='09111111111',
            is_active=True, random_code='111111'
        )
        self.business_b = Business.objects.create(
            owner=self.owner_b, name='Salon B', slug='salon-b',
            business_type='female_salon', address='Addr B',
            telephone_number='021222', phone_number='09222222222',
            is_active=True, random_code='222222'
        )
        self.payment = ManualPayment.objects.create(
            user=self.customer,
            business=self.business_a,
            tracking_code='TRK001',
            amount=500000,
            status='pending',
        )

    def test_owner_a_can_approve(self):
        self.client.force_authenticate(user=self.owner_a)
        response = self.client.patch(
            reverse('manualpayment-status', kwargs={'pk': self.payment.pk}),
            {'status': 'approved', 'owner_note': 'OK'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'approved')

    def test_owner_b_cannot_approve_payment_of_a(self):
        self.client.force_authenticate(user=self.owner_b)
        response = self.client.patch(
            reverse('manualpayment-status', kwargs={'pk': self.payment.pk}),
            {'status': 'approved'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')

    def test_customer_cannot_approve(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.patch(
            reverse('manualpayment-status', kwargs={'pk': self.payment.pk}),
            {'status': 'approved'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
