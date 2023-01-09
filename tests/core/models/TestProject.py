import pytest

from core.models import Project


class TestProject:
    @pytest.mark.django_db
    def test_save_1(self):
        """Saving should not fail when the attriute in_process is True (default)"""
        try:
            project = Project.objects.create()
        except:
            project = None
        assert project is not None

    @pytest.mark.django_db
    def test_save_2(self):
        """Saving should fail when the attribute in_process is False and the project can't verify
        credentials with the customer server.
        """
        try:
            project = Project.objects.create(in_process=False)
        except:
            project = None
        assert project is None
