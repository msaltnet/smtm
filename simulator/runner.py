import enum

class RunnerStatus(enum.Enum):
    NOT_STARTED = 'not_started'
    RUNNING = 'running'
    FINISH = 'finish'

class RunnerOrderType(enum.Enum):
    SELL = 'sell'
    BUY = 'buy'

class RunnerItem():
    def __init__(self, orderType, price, amount):
        self.type = orderType
        self.price = price
        self.amount = amount

class Runner():
# status
    def __init__(self):
        self.status = RunnerStatus.NOT_STARTED

    def start(self, record):
        self.record = record
        self.status = RunnerStatus.RUNNING
        self.currentIndex = 0
        self.stock = {}

    def getStatus(self):
        return self.status

    def getCurrentIndex(self):
        return self.currentIndex

    def order(self, request):
        if self.status != RunnerStatus.RUNNING:
            return -1

        if type(request) is not RunnerItem:
            return -1
        self.evaluate(request)
        return 0

    def evaluate(self, request):
        print('evaluate')
        now = self.record[self.currentIndex]
        price = request.price
        amount = request.amount
        response = RunnerItem(request.orderType, request.price, 0)
        # if price < now.low_price or price > now.high_price:
        #     return response

        # if request.orderType == RunnerOrderType.BUY:
        #     pass
        # else if request.orderType == RunnerOrderType.SELL:
        #     pass

        # response.amount = amount
        # return response

    def next(self):
        if self.status != RunnerStatus.RUNNING:
            return -1
        self.currentIndex += 1

        if len(self.record) <= self.currentIndex:
            self.status = RunnerStatus.FINISH
        return 0

    def getCurrentRecord(self):
        if self.status != RunnerStatus.RUNNING:
            return -1

        return self.record[self.currentIndex]

    def getResult(self):
        if self.status != RunnerStatus.FINISH:
            return -1
        print('Finish Resule')
        return 0
