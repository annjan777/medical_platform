from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from patients.models import Patient, PatientNote
from questionnaires.models import Questionnaire, Response
from screening.models import ScreeningType


class ResponseDetailViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.doctor = self.user_model.objects.create_user(
            email='doctor@example.com',
            password='testpass123',
            role=self.user_model.Role.DOCTOR,
        )
        self.health_assistant = self.user_model.objects.create_user(
            email='assistant@example.com',
            password='testpass123',
            role=self.user_model.Role.HEALTH_ASSISTANT,
        )
        self.questionnaire = Questionnaire.objects.create(
            title='Dental Consultation Form',
            created_by=self.health_assistant,
        )
        ScreeningType.objects.create(
            name='Default Screening',
            code='default-screening',
            is_active=True,
        )
        self.patient = Patient.objects.create(
            first_name='Asha',
            last_name='Patel',
            phone_number='9876543210',
            email='asha@example.com',
            created_by=self.health_assistant,
        )
        self.response = Response.objects.create(
            questionnaire=self.questionnaire,
            respondent=self.health_assistant,
            patient=self.patient,
            is_complete=True,
        )

    def test_response_detail_post_creates_consultation_note(self):
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse('doctor:response_detail', args=[self.response.pk]),
            {
                'provisional_diagnosis': 'Acute pulpitis',
                'on_examination': 'Tender molar on percussion',
                'investigations': 'IOPA advised',
                'advice': 'Warm saline rinses',
                'further_followup': 'on',
                'pres_type[]': ['Tablet'],
                'pres_medicine[]': ['Ibuprofen 400mg'],
                'pres_dosage[]': ['1-0-1'],
                'pres_instructions[]': ['After food'],
                'pres_duration[]': ['5'],
                'pres_others[]': ['SOS if pain persists'],
            },
        )

        self.assertRedirects(response, reverse('doctor:pending_consultations'))

        note = PatientNote.objects.get(patient=self.patient, note_type=PatientNote.NoteType.CONSULTATION)
        self.assertEqual(note.author, self.doctor)
        self.assertEqual(note.title, f'Consultation Note - {self.questionnaire.title}')
        self.assertTrue(note.is_important)
        self.assertIn('Acute pulpitis', note.content)
        self.assertIn('Ibuprofen 400mg', note.content)
