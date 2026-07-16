class IntegrationNotConfigured(RuntimeError):
    pass


class GspClient:
    """Safe GSTN/GSP client contract.

    This module intentionally refuses live calls unless explicit credentials and
    base URL are configured. It prevents fake compliance screens.
    """
    def __init__(self, base_url: str = "", client_id: str = "", client_secret: str = "") -> None:
        self.base_url = base_url.strip()
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.client_id and self.client_secret)

    def ensure_configured(self) -> None:
        if not self.configured:
            raise IntegrationNotConfigured("GSTN/GSP credentials are not configured; live statutory action is blocked.")
