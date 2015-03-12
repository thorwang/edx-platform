from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
from model_utils.models import TimeStampedModel

from xmodule_django.models import CourseKeyField

# Currently, the "student" app is responsible for
# accounts, profiles, enrollments, and the student dashboard.
# We are trying to move some of this functionality into separate apps,
# but currently the rest of the system assumes that "student" defines
# certain models.  For now we will leave the models in "student" and
# create an alias in "user_api".
from student.models import UserProfile, Registration, PendingEmailChange  # pylint: disable=unused-import

from .errors import PreferenceNotFound


class UserPreference(models.Model):
    """A user's preference, stored as generic text to be processed by client"""
    KEY_REGEX = r"[-_a-zA-Z0-9]+"
    user = models.ForeignKey(User, db_index=True, related_name="preferences")
    key = models.CharField(max_length=255, db_index=True, validators=[RegexValidator(KEY_REGEX)])
    value = models.TextField()

    class Meta:  # pylint: disable=missing-docstring
        unique_together = ("user", "key")

    @classmethod
    def set_preference(cls, user, preference_key, preference_value):
        """Sets the user preference for a given key, creating it if it doesn't exist.

        Arguments:
            user (User): The user whose preference should be set.
            preference_key (string): The key for the user preference.
            preference_value (string): The value to be stored. Non-strings can
                be passed and will be converted to strings.

        Raises:
            IntegrityError: the update causes a database integrity error.
        """
        user_preference, _ = cls.objects.get_or_create(user=user, key=preference_key)
        user_preference.value = preference_value
        user_preference.save()

    @classmethod
    def get_preference(cls, user, preference_key, default=None):
        """Gets the user preference value for a given key

        Arguments:
            user (User): The user whose preference should be set.
            preference_key (string): The key for the user preference.
            default (object): The default value to return if the preference is not set.

        Returns:
            The user preference value, or the specified default if one is not set.
        """
        try:
            user_preference = cls.objects.get(user=user, key=preference_key)
            return user_preference.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def delete_preference(cls, user, preference_key):
        """Deletes the user preference value for a given key

        Arguments:
            user (User): The user whose preference should be set.
            preference_key (string): The key for the user preference.

        Raises:
            PreferenceNotFound: No preference was found with the given key.
        """
        try:
            user_preference = cls.objects.get(user=user, key=preference_key)
        except cls.DoesNotExist:
            raise PreferenceNotFound()
        user_preference.delete()


class UserCourseTag(models.Model):
    """
    Per-course user tags, to be used by various things that want to store tags about
    the user.  Added initially to store assignment to experimental groups.
    """
    user = models.ForeignKey(User, db_index=True, related_name="+")
    key = models.CharField(max_length=255, db_index=True)
    course_id = CourseKeyField(max_length=255, db_index=True)
    value = models.TextField()

    class Meta:  # pylint: disable=missing-docstring
        unique_together = ("user", "course_id", "key")


class UserOrgTag(TimeStampedModel):
    """ Per-Organization user tags.

    Allows settings to be configured at an organization level.

    """
    user = models.ForeignKey(User, db_index=True, related_name="+")
    key = models.CharField(max_length=255, db_index=True)
    org = models.CharField(max_length=255, db_index=True)
    value = models.TextField()

    class Meta:
        """ Meta class for defining unique constraints. """
        unique_together = ("user", "org", "key")
