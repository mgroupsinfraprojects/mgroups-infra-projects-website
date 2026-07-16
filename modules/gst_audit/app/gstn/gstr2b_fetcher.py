from .gsp_client import GspClient


def fetch_gstr2b(client: GspClient, gstin: str, period: str):
    client.ensure_configured()
    raise NotImplementedError("Connect this boundary to an authorized GSP/GSTN API client before production use")
