from abc import ABC, abstractmethod

class BaseLogger(ABC):
    @abstractmethod
    def log_query(self, message: str):
        pass