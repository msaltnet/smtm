import json

class Record():
    def __init__(self, interval, period):
        self.list = []
        self.interval = interval
        self.period = period

    def importRecord(self, data):
        self.list = data

    def importFromFile(self, filepath):
        with open(filepath) as json_file:
            json_data = json.load(json_file)
        self.list = json_data

    def getList(self):
        return self.list

    def getInterval(self):
        return self.interval

    def getPeriod(self):
        return self.period

    # get from external server
    def fetchFromServer(self, period, interval):
        pass

    def printRecord(self):
        for i, v in enumerate(self.list):
            print("index : {}, value: {}".format(i,str(v)))
