"""

POST /uploads

* 'file' must be set
* 'file' must have acceptable mime type
* 'file' must have acceptable extension
* 'file' must be within acceptable size range

* authentication
* authorization

* response content...
* response structure...

"""
import os
from tempfile import NamedTemporaryFile

from django.core.urlresolvers import reverse
import mock
from PIL import Image
from rest_framework.test import APITestCase, APIClient

from student.tests.factories import UserFactory

from ..views import DEV_MSG_FILE_TOO_LARGE, DEV_MSG_FILE_TOO_SMALL, DEV_MSG_FILE_BAD_TYPE, DEV_MSG_FILE_BAD_EXT, DEV_MSG_FILE_BAD_MIMETYPE

TEST_PASSWORD = "test"


class ProfileImageUploadTestCase(APITestCase):

    def setUp(self):
        super(ProfileImageUploadTestCase, self).setUp()

        self.anonymous_client = APIClient()
        self.different_user = UserFactory.create(password=TEST_PASSWORD)
        self.different_client = APIClient()
        self.staff_user = UserFactory(is_staff=True, password=TEST_PASSWORD)
        self.staff_client = APIClient()
        self.user = UserFactory.create(password=TEST_PASSWORD)
        self.url = reverse("profile_image_upload", kwargs={'username': self.user.username})

    def test_anonymous_access(self):
        """
        Test that an anonymous client (not logged in) cannot call GET or POST.
        """
        for request in (self.anonymous_client.get, self.anonymous_client.post):
            response = request(self.url)
            self.assertEqual(401, response.status_code)

    def _make_image_file(self, dimensions=(100, 100), extension=".jpeg", force_size=None):
        """
        Returns a named temporary file created with the specified image type and options
        """
        image = Image.new('RGB', dimensions, "green")
        image_file = NamedTemporaryFile(suffix=extension)
        image.save(image_file)
        if force_size is not None:
            image_file.seek(0, os.SEEK_END)
            bytes_to_pad = force_size - image_file.tell()
            # write in hunks of 256 bytes
            hunk, byte_ = bytearray([0] * 256), bytearray([0])
            num_hunks, remainder = divmod(bytes_to_pad, 256)
            for _ in xrange(num_hunks):
                image_file.write(hunk)
            for _ in xrange(remainder):
                image_file.write(byte_)
            image_file.flush()
        image_file.seek(0)
        return image_file

    def test_upload_self(self):
        """
        Test that an authenticated user can POST to their own upload endpoint.
        """
        self.client.login(username=self.user.username, password=TEST_PASSWORD)
        response = self.client.post(self.url, {'file': self._make_image_file()}, format='multipart')
        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "success"}, response.data)

    def test_upload_other(self):
        """
        Test that an authenticated user cannot POST to another user's upload endpoint.
        """
        self.different_client.login(username=self.different_user.username, password=TEST_PASSWORD)
        response = self.different_client.post(self.url, {'file': self._make_image_file()}, format='multipart')
        self.assertEqual(403, response.status_code)

    def test_upload_staff(self):
        """
        Test that an authenticated staff user can POST to another user's upload endpoint.
        """
        self.staff_client.login(username=self.staff_user.username, password=TEST_PASSWORD)
        response = self.staff_client.post(self.url, {'file': self._make_image_file()}, format='multipart')
        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "success"}, response.data)

    def test_upload_missing_file(self):
        """
        Test that omitting the file entirely from the POST results in HTTP 400.
        """
        self.client.login(username=self.user.username, password=TEST_PASSWORD)
        response = self.client.post(self.url, {}, format='multipart')
        self.assertEqual(400, response.status_code)

    def test_upload_not_a_file(self):
        """
        Test that sending unexpected data that isn't a file results in HTTP 400.
        """
        self.client.login(username=self.user.username, password=TEST_PASSWORD)
        response = self.client.post(self.url, {'file': 'not a file'}, format='multipart')
        self.assertEqual(400, response.status_code)

    def test_upload_file_too_large(self):
        """
        """
        image_file = self._make_image_file(force_size=(1024 * 1024) + 1)  # TODO settings / override settings
        self.client.login(username=self.user.username, password=TEST_PASSWORD)
        response = self.client.post(self.url, {'file': image_file}, format='multipart')
        self.assertEqual(400, response.status_code)
        self.assertEqual(response.data.get('developer_message'), DEV_MSG_FILE_TOO_LARGE)

    def test_upload_file_too_small(self):
        """
        """
        image_file = self._make_image_file(dimensions=(1, 1), extension=".png", force_size=99)  # TODO settings / override settings
        self.client.login(username=self.user.username, password=TEST_PASSWORD)
        response = self.client.post(self.url, {'file': image_file}, format='multipart')
        self.assertEqual(400, response.status_code)
        self.assertEqual(response.data.get('developer_message'), DEV_MSG_FILE_TOO_SMALL)

    def test_upload_bad_extension(self):
        """
        """
        self.client.login(username=self.user.username, password=TEST_PASSWORD)
        response = self.client.post(self.url, {'file': self._make_image_file(extension=".bmp")}, format='multipart')
        self.assertEqual(400, response.status_code)
        self.assertEqual(response.data.get('developer_message'), DEV_MSG_FILE_BAD_TYPE)

    # ext / header mismatch
    def test_upload_wrong_extension(self):
        """
        """
        self.client.login(username=self.user.username, password=TEST_PASSWORD)
        # make a bmp, rename it to jpeg
        bmp_file = self._make_image_file(extension=".bmp")
        fake_jpeg_file = NamedTemporaryFile(suffix=".jpeg")
        fake_jpeg_file.write(bmp_file.read())
        fake_jpeg_file.seek(0)
        response = self.client.post(self.url, {'file': fake_jpeg_file}, format='multipart')
        self.assertEqual(400, response.status_code)
        self.assertEqual(response.data.get('developer_message'), DEV_MSG_FILE_BAD_EXT)

    # content-type / header mismatch
    @mock.patch('django.test.client.mimetypes')
    def test_upload_bad_content_type(self, mock_mimetypes):
        """
        """
        mock_mimetypes.guess_type.return_value = ['image/gif']
        self.client.login(username=self.user.username, password=TEST_PASSWORD)
        response = self.client.post(self.url, {'file': self._make_image_file(extension=".jpeg")}, format='multipart')
        self.assertEqual(400, response.status_code)
        self.assertEqual(response.data.get('developer_message'), DEV_MSG_FILE_BAD_MIMETYPE)

