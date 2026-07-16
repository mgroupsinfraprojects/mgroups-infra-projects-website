from app.gstn.gsp_client import GspClient


class EWayBillClient(GspClient):
    def generate(self, payload: dict):
        self.ensure_configured()
        raise NotImplementedError("E-way bill generation requires authorized API integration")
