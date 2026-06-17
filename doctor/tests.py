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
                'oral_pathologies[]': ['Gingivitis', 'Oral candidiasis'],
                'on_examination': 'Tender molar on percussion',
                'white_patch': 'Yes',
                'red_patch': 'No',
                'investigations': 'IOPA advised',
                'advice': 'Warm saline rinses',
                'further_followup': 'on',
                'specialist_referral': 'on',
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
        self.assertIn('Oral Pathologies', note.content)
        self.assertIn('Gingivitis, Oral candidiasis', note.content)
        self.assertIn('Acute pulpitis', note.content)
        self.assertIn('Ibuprofen 400mg', note.content)
        self.assertIn('<strong>White patch present</strong><br>Yes', note.content)
        self.assertIn('<strong>Red patch present</strong><br>No', note.content)
        self.assertIn('<strong>Specialist Referral Required</strong><br>Yes', note.content)

    def test_response_detail_post_allows_specialist_referral_if_already_diagnosed(self):
        # Create an existing consultation note for the patient
        PatientNote.objects.create(
            patient=self.patient,
            author=self.doctor,
            note_type=PatientNote.NoteType.CONSULTATION,
            title='Previous Consultation',
            content='Some previous diagnosis',
        )

        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse('doctor:response_detail', args=[self.response.pk]),
            {
                'provisional_diagnosis': 'Another pulpitis',
                'further_followup': 'on',
                'specialist_referral': 'on',
            },
        )

        self.assertRedirects(response, reverse('doctor:pending_consultations'))

        # Get the latest consultation note (there should be two notes now)
        notes = PatientNote.objects.filter(patient=self.patient, note_type=PatientNote.NoteType.CONSULTATION).order_by('-created_at')
        self.assertEqual(notes.count(), 2)
        latest_note = notes[0]
        self.assertIn('<strong>Specialist Referral Required</strong><br>Yes', latest_note.content)

    def test_response_detail_shows_oral_pathology_options(self):
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('doctor:response_detail', args=[self.response.pk]))

        self.assertContains(response, 'Observation')
        self.assertContains(response, 'Gingivitis')
        self.assertContains(response, 'Aphthous stomatitis')
        self.assertContains(response, 'Oral candidiasis')
        self.assertContains(response, 'Dental fluorosis')


class ResponseListTimestampTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.doctor = self.user_model.objects.create_user(
            email='doctor-list@example.com',
            password='testpass123',
            role=self.user_model.Role.DOCTOR,
        )
        self.health_assistant = self.user_model.objects.create_user(
            email='assistant-list@example.com',
            password='testpass123',
            role=self.user_model.Role.HEALTH_ASSISTANT,
        )
        self.questionnaire = Questionnaire.objects.create(
            title='Timestamp Survey',
            created_by=self.health_assistant,
        )
        ScreeningType.objects.create(
            name='Default Screening',
            code='default-screening-list',
            is_active=True,
        )
        self.patient = Patient.objects.create(
            first_name='Riya',
            last_name='Shah',
            phone_number='9876543211',
            email='riya@example.com',
            created_by=self.health_assistant,
        )
        self.response = Response.objects.create(
            questionnaire=self.questionnaire,
            respondent=self.health_assistant,
            patient=self.patient,
            is_complete=False,
        )

    def test_doctor_response_list_shows_started_at_when_submitted_at_missing(self):
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('doctor:response_list'))

        self.assertContains(response, self.response.started_at.strftime('%b %d, %Y'))

    def test_health_assistant_response_list_shows_started_at_when_submitted_at_missing(self):
        self.client.force_login(self.health_assistant)

        response = self.client.get(reverse('questionnaires:response_list'))

        self.assertContains(response, self.response.started_at.strftime('%b %d, %Y'))


class CompletedConsultationsExportTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.doctor = self.user_model.objects.create_user(
            email='doctor-export@example.com',
            password='testpass123',
            role=self.user_model.Role.DOCTOR,
        )
        self.health_assistant = self.user_model.objects.create_user(
            email='assistant-export@example.com',
            password='testpass123',
            role=self.user_model.Role.HEALTH_ASSISTANT,
        )
        self.questionnaire = Questionnaire.objects.create(
            title='Survey Form',
            created_by=self.health_assistant,
        )
        ScreeningType.objects.create(
            name='Default Screening',
            code='default-screening-export',
            is_active=True,
        )
        self.patient = Patient.objects.create(
            first_name='Ananya',
            last_name='Sen',
            phone_number='9876543212',
            email='ananya@example.com',
            created_by=self.health_assistant,
        )
        self.response = Response.objects.create(
            questionnaire=self.questionnaire,
            respondent=self.health_assistant,
            patient=self.patient,
            is_complete=True,
        )
        # Create a completed consultation note
        PatientNote.objects.create(
            patient=self.patient,
            author=self.doctor,
            note_type=PatientNote.NoteType.CONSULTATION,
            title='Consultation Note',
            content='<strong>Oral Pathologies</strong><br>Gingivitis<br><br><strong>Provisional Diagnosis</strong><br>Dental caries<br><br><strong>On Examination</strong><br>Mild calculus<br><br><strong>Investigations</strong><br>X-Ray<br><br><strong>White patch present</strong><br>Yes<br><br><strong>Red patch present</strong><br>No<br><br><strong>Prescriptions</strong><br>&bull; Tablet: Paracetamol | 1-0-1 | 5 days | After food | None<br><br><strong>Advice</strong><br>Brush twice daily<br><br><strong>Further Followup Required</strong><br>No<br><br><strong>Specialist Referral Required</strong><br>Yes',
            is_important=False # False makes it appear under Completed consultations according to view filtering
        )

    def test_completed_consultations_export_csv(self):
        self.client.force_login(self.doctor)
        
        # Request patient search API with export=csv and view=completed
        response = self.client.get(
            reverse('health_assistant:api_search_patients'),
            {
                'export': 'csv',
                'view': 'completed'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="patients_export.csv"', response['Content-Disposition'])
        
        csv_content = response.content.decode('utf-8')
        
        # Verify custom CSV headers exist
        self.assertIn('Oral Pathologies', csv_content)
        self.assertIn('Provisional Diagnosis', csv_content)
        self.assertIn('On Examination', csv_content)
        self.assertIn('Investigations', csv_content)
        self.assertIn('White patch present', csv_content)
        self.assertIn('Red patch present', csv_content)
        self.assertIn('Prescriptions', csv_content)
        self.assertIn('Advice', csv_content)
        self.assertIn('Further Followup Required', csv_content)
        self.assertIn('Specialist Referral Required', csv_content)
        
        # Verify row content has parsed values
        self.assertIn('Ananya', csv_content)
        self.assertIn('Gingivitis', csv_content)
        self.assertIn('Dental caries', csv_content)
        self.assertIn('Mild calculus', csv_content)
        self.assertIn('X-Ray', csv_content)
        self.assertIn('Tablet: Paracetamol', csv_content)
        self.assertIn('Brush twice daily', csv_content)
        self.assertIn('No', csv_content)
        self.assertIn('Yes', csv_content)
