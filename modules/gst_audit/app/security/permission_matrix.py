DEFAULT_PERMISSIONS = {
    "SUPER_ADMIN": {"*"},
    "FIRM_ADMIN": {"IMPORT", "RUN_AUDIT", "APPROVE", "EXPORT", "MANAGE_USERS", "VIEW"},
    "MANAGER": {"IMPORT", "RUN_AUDIT", "APPROVE", "EXPORT", "VIEW"},
    "AUDITOR": {"IMPORT", "RUN_AUDIT", "VIEW"},
    "REVIEWER": {"APPROVE", "VIEW"},
    "VIEWER": {"VIEW"},
}


class PermissionMatrix:
    def __init__(self, permissions=None):
        self.permissions = permissions or DEFAULT_PERMISSIONS

    def allowed(self, role: str, action: str) -> bool:
        granted = self.permissions.get(str(role).upper(), set())
        return "*" in granted or str(action).upper() in granted
