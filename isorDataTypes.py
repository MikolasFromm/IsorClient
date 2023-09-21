import uuid

class IsorRequest:
    def __init__(self, url : str, body : dict):
        self.url = url
        self.body = body
        self.guid = uuid.uuid4()

class IsorResponse:
    def __init__(self, status : int, text : str, guid : uuid):
        self.status = status
        self.text = text
        self.guid = guid