from contextlib import closing
import hashlib
from cStringIO import StringIO

from django.conf import settings
from django.core.files.storage import get_storage_class
from django.core.files.base import ContentFile

from PIL import Image

from rest_framework import permissions, status
from rest_framework.authentication import OAuth2Authentication, SessionAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

# TODO: move these to settings
PROFILE_IMAGE_STORAGE_CLASS = 'django.core.files.storage.FileSystemStorage'
PROFILE_IMAGE_MAX_BYTES = 1024 * 1024
PROFILE_IMAGE_MIN_BYTES = 100


DEV_MSG_FILE_TOO_LARGE = 'Maximum file size exceeded.'
DEV_MSG_FILE_TOO_SMALL = 'Minimum file size not met.'
DEV_MSG_FILE_BAD_TYPE = 'Unsupported file type.'
DEV_MSG_FILE_BAD_EXT = 'File extension does not match data.'
DEV_MSG_FILE_BAD_MIMETYPE = 'Content-Type header does not match data.'


class InvalidProfileImage(Exception):
    """
    Local Exception type that helps us clean up after file validation
    failures, and communicate what went wrong to the user.
    """
    pass


def validate_profile_image(image_file, content_type):
    """
    Raises an InvalidProfileImage if the server should refuse to store this
    uploaded file as a user's profile image.

    Otherwise, returns a cleaned version of the extension as a string, i.e. one
    of: ('gif', 'jpeg', 'png')
    """
    # TODO: better to just use PIL for this?  seems like it

    image_types = {
        'jpeg' : {
            'extension': [".jpeg", ".jpg"],
            'mimetypes': ['image/jpeg', 'image/pjpeg'],
            'magic': ["ffd8"]
            },
        'png': {
            'extension': [".png"],
            'mimetypes': ['image/png'],
            'magic': ["89504e470d0a1a0a"]
            },
        'gif': {
            'extension': [".gif"],
            'mimetypes': ['image/gif'],
            'magic': ["474946383961", "474946383761"]
            }
        }

    # check file size
    if image_file.size > PROFILE_IMAGE_MAX_BYTES:
        raise InvalidProfileImage(DEV_MSG_FILE_TOO_LARGE)
    elif image_file.size < PROFILE_IMAGE_MIN_BYTES:
        raise InvalidProfileImage(DEV_MSG_FILE_TOO_SMALL)

    # check the file extension looks acceptable
    filename = str(image_file.name).lower()
    filetype = [ft for ft in image_types if any(filename.endswith(ext) for ext in image_types[ft]['extension'])]
    if not filetype:
        raise InvalidProfileImage(DEV_MSG_FILE_BAD_TYPE)
    filetype = filetype[0]

    # check mimetype matches expected file type
    if content_type not in image_types[filetype]['mimetypes']:
        raise InvalidProfileImage(DEV_MSG_FILE_BAD_MIMETYPE)

    # check image file headers match expected file type
    headers = image_types[filetype]['magic']
    if image_file.read(len(headers[0])/2).encode('hex') not in headers:
        raise InvalidProfileImage(DEV_MSG_FILE_BAD_EXT)
    # avoid unexpected errors from subsequent modules expecting the fp to be at 0
    image_file.seek(0)
    return filetype


def make_thumbnail(image_file, dimension):
    """
    """
    th = Image.open(image_file)
    th.thumbnail((dimension, dimension), Image.ANTIALIAS)
    string_io = StringIO()
    th.save(string_io, format='JPEG')
    thumbnail_file = ContentFile(string_io.getvalue())
    image_file.seek(0)
    return thumbnail_file


def store_profile_image(image_file, image_name, username, extension):
    """
    Permanently store the contents of the uploaded_file as this user's profile
    image, in whatever storage backend we're configured to use.  Any
    previously-stored profile image will be overwritten.

    Returns the path to the stored file.
    """
    storage = get_storage_class(PROFILE_IMAGE_STORAGE_CLASS)()
    dest_name = storage.get_valid_name('{}_profile_{}.{}'.format(hashlib.md5(username).hexdigest(), image_name, extension))
    if storage.exists(dest_name):
        storage.delete(dest_name)
    path = storage.save(dest_name, image_file)
    return path


class ProfileImageUploadView(APIView):

    parser_classes = (MultiPartParser, FormParser,)

    authentication_classes = (OAuth2Authentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, username):

        # request validation.

        # ensure authenticated user is either same as username, or is staff.
        if request.user.username != username and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # ensure file exists at all!
        if 'file' not in request.FILES:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES['file']
        print 'content_type:', uploaded_file.content_type

        # no matter what happens, delete the temporary file when we're done
        with closing(uploaded_file):

            # image file validation.
            try:
                file_type = validate_profile_image(uploaded_file, uploaded_file.content_type)
            except InvalidProfileImage, e:
                return Response(
                    {
                        "developer_message": e.message,
                        "user_message": None
                    },
                    status = status.HTTP_400_BAD_REQUEST
                )

            stored_paths = []
            for dim in [30, 50, 150]:
                thumbnail_file = make_thumbnail(uploaded_file, dim)
                # Store the file.
                stored_path = store_profile_image(thumbnail_file, str(dim), username, file_type)
                stored_paths.append(stored_path)

            # update the user account to reflect that a profile image is available.
            # TODO

        # send user response.
        return Response({"status": "success"})
