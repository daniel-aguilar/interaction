from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings

from .forms import CaptchaField


@override_settings(
    EMAIL_ADDRESS='daniel@example.com',
    THANKS_URL='http://test-server.com/thanks/',
    ERROR_URL='http://test-server.com/oops/'
)
class ContactTestCase(SimpleTestCase):
    def setUp(self):
        self.form_data = {
            'name': 'Daniel',
            'email': 'daniel@example.com',
            'message': 'message',
            'g-recaptcha-response': 'I am not a robot',
        }

    @patch('contact.forms.CaptchaField.validate')
    def test_send_email(self, validate):
        self.client.post('/contact/', self.form_data)

        self.assertEqual(len(mail.outbox), 1)
        self.assertCountEqual(mail.outbox[0].recipients(), ['daniel@example.com'])

    @patch('contact.forms.CaptchaField.validate')
    def test_form_redirect(self, validate):
        response = self.client.post('/contact/', self.form_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.get('Location'), settings.THANKS_URL)

        validate.side_effect = ValidationError('Invalid CAPTCHA', code='captcha')
        response = self.client.post('/contact/', self.form_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.get('Location'), settings.ERROR_URL)


@patch('requests.post')
@patch('requests.Response')
class ContactFormTestCase(SimpleTestCase):

    def test_valid_captcha(self, post, Response):
        res = Response()
        res.json = MagicMock(return_value={'success': True})
        post.return_value = res

        field = CaptchaField()
        self.assertEqual(field.clean('I am not a robot'), 'I am not a robot')

    def test_invalid_captcha(self, post, Response):
        res = Response()
        res.json = MagicMock(return_value={'success': False})
        post.return_value = res

        field = CaptchaField()
        with self.assertRaises(ValidationError) as cm:
            field.clean('I am a robot')

        self.assertEqual(cm.exception.code, 'captcha')
