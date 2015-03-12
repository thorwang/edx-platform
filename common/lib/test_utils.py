from __future__ import unicode_literals
from urlparse import urlparse
from django.test.client import RequestFactory, Client, FakePayload

BOUNDARY = 'BoUnDaRyStRiNg'
MULTIPART_CONTENT = 'multipart/form-data; boundary=%s' % BOUNDARY


def request_factory_patch(self, path, data={}, content_type=MULTIPART_CONTENT, **extra):
    """
    Construct a PATCH request.
    """
    patch_data = self._encode_data(data, content_type)

    parsed = urlparse(path)
    r = {
        'CONTENT_LENGTH': len(patch_data),
        'CONTENT_TYPE':   content_type,
        'PATH_INFO':      self._get_path(parsed),
        'QUERY_STRING':   parsed[4],
        'REQUEST_METHOD': 'PATCH',
        'wsgi.input':     FakePayload(patch_data),
    }
    r.update(extra)
    return self.request(**r)


def client_patch(self, path, data={}, content_type=MULTIPART_CONTENT, follow=False, **extra):
    """
    Send a resource to the server using PATCH.
    """
    response = super(Client, self).patch(path, data=data, content_type=content_type, **extra)
    if follow:
        response = self._handle_redirects(response, **extra)
    return response

setattr(RequestFactory, 'patch', request_factory_patch)
setattr(Client, 'patch', client_patch)