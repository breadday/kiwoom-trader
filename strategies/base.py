class BaseStrategy:
    def __init__(self, api):
        self.api = api

    def should_enter(self, code, data): 
        raise NotImplementedError

    def should_exit(self, code, position, data):
        raise NotImplementedError
