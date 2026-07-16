from app.gstn.gsp_client import GspClient


class IrpClient(GspClient):
    def submit_irn(self, payload: dict):
        self.ensure_configured()
        raise NotImplementedError("IRP submission requires authorized production/sandbox integration")
