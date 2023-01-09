BILLING = "__billing__"
BOT = "__bot__"
CROSS = "__cross__"
EVENT = "__event__"
MANAGER = "__manager__"
OPERATOR = "__operator__"
PUBLIC = "__public__"
SUPERUSER = "__superuser__"

ALL = [BILLING, BOT, CROSS, EVENT, MANAGER, OPERATOR, PUBLIC, SUPERUSER]
ADMIN = [MANAGER, SUPERUSER]
USER = [OPERATOR, *ADMIN]


def has_permissions(user: dict, permissions: list) -> bool:
    """Checks if user has at least one of the permissions.

    Args:
        user (dict): Keycloack user representation.
        permissions (list): List of string, each string should be the name of a keycloak group. If
            permissions is empty is assumed that the user has the credentials.
    """
    if len(permissions) == 0:
        return True

    user_groups = user.get("groups", [])
    for group in user_groups:
        if group in permissions:
            return True

    return False
