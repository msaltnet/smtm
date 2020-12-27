from .log_manager import LogManager
from .yield_record import YieldRecord

class Analyzer():
    """
    거래 요청, 결과 정보를 저장하고 투자 결과를 분석하는 클래스

    request: 거래 요청 정보 목록
    result: 거래 결과 정보 목록
    asset_record_list: 특정 시점에 기록된 자산 정보 목록, asset_info 클래스 사용
    yield_record_list: 특정 시점에 기록된 수익률 정보 목록
    update_info_func: 자산 정보 업데이트를 요청하기 위한 콜백 함수
    """

    def __init__(self):
        self.request = []
        self.result = []
        self.asset_record_list = []
        self.yield_record_list = []
        self.update_info_func = None
        self.logger = LogManager.get_logger(__name__)

    def put_request(self, request):
        """거래 요청 정보를 저장한다"""
        self.request.append(request)

    def put_result(self, result):
        """거래 결과 정보를 저장한다"""
        if self.update_info_func is None:
            self.logger.warning("update_info_func is NOT set")
            return

        self.result.append(result)
        self.update_info_func("asset", self.put_asset_info)

    def initialize(self, update_info_func):
        self.update_info_func = update_info_func

    def put_asset_info(self, asset_info):
        self.asset_record_list.append(asset_info)
        self.make_yield_record(asset_info)

    def make_start_point(self):
        self.request = []
        self.result = []
        self.asset_record_list = []
        self.update_info_func("asset", self.put_asset_info)

    def make_yield_record(self, new_info):
        try:
            start_total = self.asset_record_list[0].balance
            start_quote = self.asset_record_list[0].quote
            current_total = new_info.balance
            current_quote = new_info.quote
            cumulative_return = 0
            new_asset_list = []

            for asset in self.asset_record_list[0].asset:
                start_total += asset[2] * start_quote[asset[0]]

            for asset in new_info.asset:
                price = current_quote[asset[0]]
                current_total += asset[2] * price
                item_yield = (price - asset[1]) / asset[1] * 100
                item_yield = round(item_yield, 3)
                self.logger.info(f'yield record {asset[0]}, {asset[1]}, {price}, {asset[2]}, {item_yield}')
                new_asset_list.append((asset[0], asset[1], price, asset[2],
                    item_yield))

            cumulative_return = (current_total - start_total) / start_total * 100
            cumulative_return = round(cumulative_return, 3)
            self.logger.info(f'cumulative_return {start_total} -> {current_total}, {cumulative_return}%')
            self.yield_record_list.append(YieldRecord(new_info.balance, 
                cumulative_return, new_asset_list))
        except IndexError as msg:
            self.logger.warning(msg)
        except AttributeError as msg:
            self.logger.warning(msg)
