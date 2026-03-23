from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from .models import IncidentReport


@override_settings(ROOT_URLCONF='main.tests_urls')
class IncidentNotificationTests(TestCase):
	def setUp(self):
		self.user_model = get_user_model()

		self.reporter = self.user_model.objects.create_user(
			username='student_reporter',
			password='test-pass-123',
			first_name='Stu',
			middle_name='D',
			last_name='Ent',
			email='student_reporter@example.com',
			id_number='S-1001',
			contact_number='09123456780',
			gender='M',
			department='CCS',
			privilege='student',
			status='allowed',
		)

		self.admin_user = self.user_model.objects.create_user(
			username='admin_user',
			password='test-pass-123',
			first_name='Ad',
			middle_name='M',
			last_name='In',
			email='admin_user@example.com',
			id_number='A-2001',
			contact_number='09123456781',
			gender='F',
			department='Admin Office',
			privilege='admin',
			status='allowed',
		)

		self.faculty_user = self.user_model.objects.create_user(
			username='faculty_user',
			password='test-pass-123',
			first_name='Fac',
			middle_name='U',
			last_name='Lty',
			email='faculty_user@example.com',
			id_number='F-3001',
			contact_number='09123456782',
			gender='M',
			department='CCS',
			privilege='faculty',
			status='allowed',
		)

		self.student_user = self.user_model.objects.create_user(
			username='another_student',
			password='test-pass-123',
			first_name='Other',
			middle_name='S',
			last_name='Tudent',
			email='another_student@example.com',
			id_number='S-1002',
			contact_number='09123456783',
			gender='F',
			department='CAS',
			privilege='student',
			status='allowed',
		)

	@patch('main.views.incident_view.send_mail')
	def test_new_incident_sends_email_to_all_admin_and_faculty(self, mock_send_mail):
		login_ok = self.client.login(username='student_reporter', password='test-pass-123')
		self.assertTrue(login_ok)

		with patch('main.views.incident_view.reverse', return_value='/incidents/1/'), \
			 patch('main.views.incident_view.loader.get_template') as mock_get_template:
			mock_get_template.return_value.render.return_value = 'ok'
			response = self.client.post(
				reverse('incident_forms'),
				data={
					'first_name': 'Stu',
					'middle_name': 'D',
					'last_name': 'Ent',
					'contact_number': '09123456780',
					'id_number': 'S-1001',
					'subject': 'Unauthorized Entry',
					'location': 'Main Gate',
					'incident': 'Observed unauthorized person attempting entry.',
					'people_involved': 'Unknown person',
					'request_for_action': 'Investigate and review CCTV footage.',
					'position': 'Student',
					'department': 'CCS',
				},
			)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(IncidentReport.objects.count(), 1)

		self.assertTrue(mock_send_mail.called)
		self.assertEqual(mock_send_mail.call_count, 1)

		_, _, _, recipients = mock_send_mail.call_args[0][:4]
		self.assertCountEqual(
			recipients,
			['admin_user@example.com', 'faculty_user@example.com'],
		)
		self.assertNotIn('another_student@example.com', recipients)
