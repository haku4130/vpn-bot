class XrayError(Exception):
    def __init__(self, detail):
        self.detail = detail


class EmailExistsError(XrayError):
    def __init__(self, detail, email: str):
        super().__init__(detail)
        self.email = email


class InboundTagNotFoundError(XrayError):
    def __init__(self, detail, inbound_tag: str):
        super().__init__(detail)
        self.inbound_tag = inbound_tag
