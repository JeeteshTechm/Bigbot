import pytest

from core.models import KeycloakRealm, Project, Stack


# --------------------------------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------------------------------


class TestGitlabPipeline:
    @pytest.mark.django_db
    def test_cehck(self):
        pass

    @pytest.mark.django_db
    def test_create(self):
        pass


class TestKeycloakRealm:
    @pytest.mark.django_db
    def test_check_offline(self, mocker):
        def check_mock(self):
            return False

        mocker.patch.object(KeycloakRealm, "check_status", new=check_mock)

        realm = KeycloakRealm.objects.create(realm="test")
        project = Project.objects.create(name="test")
        project.keycloak_realm = realm
        project.save()

        stack = Stack.objects.create(
            project=project, status=Stack.Status.RUNNING, step=Stack.Step.KEYCLOAK
        )
        stack.next(False)

        assert stack.status == Stack.Status.RUNNING
        assert stack.step == Stack.Step.KEYCLOAK

    @pytest.mark.django_db
    def test_check_online(self, mocker):
        def check_mock(self):
            return True

        mocker.patch.object(KeycloakRealm, "check_status", new=check_mock)

        realm = KeycloakRealm.objects.create(realm="test")
        project = Project.objects.create(name="test")
        project.keycloak_realm = realm
        project.save()

        stack = Stack.objects.create(
            project=project, status=Stack.Status.RUNNING, step=Stack.Step.KEYCLOAK
        )
        stack.next(False)

        assert stack.status == Stack.Status.FINISHED
        assert stack.step == Stack.Step.KEYCLOAK

    @pytest.mark.django_db
    def test_create(self, mocker):
        def create_mock(realm):
            instance = KeycloakRealm.objects.create(realm=realm)
            return instance

        mocker.patch.object(KeycloakRealm, "create", new=create_mock)

        project = Project.objects.create(name="test")

        stack = Stack.objects.create(
            project=project, status=Stack.Status.PENDING, step=Stack.Step.KEYCLOAK
        )
        stack.next(False)

        assert stack.status == Stack.Status.RUNNING
        assert stack.step == Stack.Step.KEYCLOAK
        assert stack.project.keycloak_realm is not None


class TestServerSetup:
    @pytest.mark.django_db
    def test_check(self):
        pass

    @pytest.mark.django_db
    def test_create(self):
        pass
