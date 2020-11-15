from abc import *
 
class RecordBase(metaclass=ABCMeta):
    @abstractmethod
    def get_item(self):
        pass
 
    @abstractmethod
    def get_total_count(self):
        pass

    @abstractmethod
    def intialize(self):
        pass