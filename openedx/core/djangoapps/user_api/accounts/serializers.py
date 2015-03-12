from rest_framework import serializers
from django.contrib.auth.models import User
from openedx.core.djangoapps.user_api.accounts import NAME_MIN_LENGTH
from openedx.core.djangoapps.user_api.serializers import ReadOnlyFieldsSerializerMixin

from student.models import UserProfile
from .helpers import get_profile_image_url_for_user


class AccountUserSerializer(serializers.HyperlinkedModelSerializer, ReadOnlyFieldsSerializerMixin):
    """
    Class that serializes the portion of User model needed for account information.
    """
    class Meta:
        model = User
        fields = ("username", "email", "date_joined")
        read_only_fields = ("username", "email", "date_joined")
        explicit_read_only_fields = ()

class AccountLegacyProfileSerializer(serializers.HyperlinkedModelSerializer, ReadOnlyFieldsSerializerMixin):
    """
    Class that serializes the portion of UserProfile model needed for account information.
    """
    profile_image = serializers.SerializerMethodField("get_profile_image")

    class Meta:
        model = UserProfile
        fields = (
            "name", "gender", "goals", "year_of_birth", "level_of_education", "language", "country", "mailing_address",
            "profile_image"
        )
        # Currently no read-only field, but keep this so view code doesn't need to know.
        read_only_fields = ()
        explicit_read_only_fields = ("profile_image",)

    def validate_name(self, attrs, source):
        """ Enforce minimum length for name. """
        if source in attrs:
            new_name = attrs[source].strip()
            if len(new_name) < NAME_MIN_LENGTH:
                raise serializers.ValidationError(
                    "The name field must be at least {} characters long.".format(NAME_MIN_LENGTH)
                )
            attrs[source] = new_name

        return attrs

    def transform_gender(self, obj, value):
        """ Converts empty string to None, to indicate not set. Replaced by to_representation in version 3. """
        return AccountLegacyProfileSerializer.convert_empty_to_None(value)

    def transform_country(self, obj, value):
        """ Converts empty string to None, to indicate not set. Replaced by to_representation in version 3. """
        return AccountLegacyProfileSerializer.convert_empty_to_None(value)

    def transform_level_of_education(self, obj, value):
        """ Converts empty string to None, to indicate not set. Replaced by to_representation in version 3. """
        return AccountLegacyProfileSerializer.convert_empty_to_None(value)

    @staticmethod
    def convert_empty_to_None(value):
        """ Helper method to convert empty string to None (other values pass through). """
        return None if value == "" else value

    def get_profile_image(self, obj):
        """ Returns metadata about a user's profile image. """
        return {
            'has_image': obj.has_profile_image,
            'image_url': get_profile_image_url_for_user(obj.user)
        }
