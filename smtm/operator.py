# 전체 시스템을 운영하는 운영자
class Operator():
    dp = None
    algorithm = None
    trader = None
    interval = 10 # default 10 second
    isTimerRunning = False
    threading = None

    # 초기화 할 때 필수 모듈의 인스턴스를 전달 받는다
    # Data Provider, Algorithm, Trader
    def initialize(self, http, threading, dataProvider, algorithm, trader):
        self.http = http
        self.dp = dataProvider
        self.algorithm = algorithm
        self.trader = trader
        self.threading = threading

        if self.dp is not None:
            self.dp.initialize(self.http)

    # 운영에 필요한 기본 정보를 전달 받는다
    # interval : 거래 간격
    def setup(self, interval):
        self.interval = interval

    # 일정 시간 뒤 자동 거래를 시작한다
    def start(self):
        if self.dp is None or self.threading is None:
            return False

        if self.isTimerRunning:
            return False

        self.timer = self.threading.Timer(self.interval, self.process)
        self.timer.start()
        print("timer is started")

        self.isTimerRunning = True
        return True

    # 자동 거래를 실행 후 일정 시간 뒤 거래를 트리거한다
    def process(self):
        if self.dp is None or self.isTimerRunning == False:
            return False
        self.isTimerRunning = False
        self.dp.get_info()
        print("process is completed")
        self.start()
        return True

    # 거래를 중단한다
    def stop(self):
        self.timer.cancel()
        self.isTimerRunning = False
