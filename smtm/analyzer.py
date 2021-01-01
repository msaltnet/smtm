from .log_manager import LogManager
from .score_record import ScoreRecord

class Analyzer():
    """
    거래 요청, 결과 정보를 저장하고 투자 결과를 분석하는 클래스

    request: 거래 요청 정보 목록
    result: 거래 결과 정보 목록
    asset_record_list: 특정 시점에 기록된 자산 정보 목록, asset_info 클래스 사용
    score_record_list: 특정 시점에 기록된 수익률 정보 목록
    update_info_func: 자산 정보 업데이트를 요청하기 위한 콜백 함수
    """

    def __init__(self):
        self.request = []
        self.result = []
        self.asset_record_list = []
        self.score_record_list = []
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
        self.make_score_record(asset_info)

    def make_start_point(self):
        self.request = []
        self.result = []
        self.asset_record_list = []
        self.update_info_func("asset", self.put_asset_info)

    def make_score_record(self, new_info):
        try:
            start_total = self.__get_start_property_value()
            start_quote = self.asset_record_list[0].quote
            current_total = new_info.balance
            current_quote = new_info.quote
            cumulative_return = 0
            new_asset_list = []
            price_change_ratio = {}

            for asset in new_info.asset:
                item_yield = 0
                price = current_quote[asset[0]]
                current_total += asset[2] * price
                item_price_diff = price - asset[1]
                if item_price_diff != 0:
                    item_yield = (price - asset[1]) / asset[1] * 100
                    item_yield = round(item_yield, 3)
                self.logger.info(f'yield record {asset[0]}, {asset[1]}, {price}, {asset[2]}, {item_yield}')
                new_asset_list.append((asset[0], asset[1], price, asset[2], item_yield))

                start_price = start_quote[asset[0]]
                price_change_ratio[asset[0]] = 0
                price_diff = (price - start_price)
                if price_diff != 0:
                    price_change_ratio[asset[0]] = price_diff / start_price * 100
                    price_change_ratio[asset[0]] = round(price_change_ratio[asset[0]], 3)
                self.logger.info(f'price change ratio {start_price} -> {price}, {price_change_ratio[asset[0]]}%')

            total_diff = current_total - start_total
            if total_diff != 0:
                cumulative_return = (current_total - start_total) / start_total * 100
                cumulative_return = round(cumulative_return, 3)
            self.logger.info(f'cumulative_return {start_total} -> {current_total}, {cumulative_return}%')

            self.score_record_list.append(ScoreRecord(new_info.balance, 
                cumulative_return, new_asset_list, price_change_ratio))
        except IndexError as msg:
            self.logger.warning(msg)
        except AttributeError as msg:
            self.logger.warning(msg)

    def create_report(self):
        start_value = self.__get_start_property_value()
        last_value = self.__get_last_property_value()
        return (start_value, last_value,
            self.score_record_list[-1].cumulative_return,
            self.score_record_list[-1].price_change_ratio)

    def __get_start_property_value(self):
        start_total = self.asset_record_list[0].balance
        start_quote = self.asset_record_list[0].quote
        for asset in self.asset_record_list[0].asset:
            start_total += asset[2] * start_quote[asset[0]]
        return start_total

    def __get_last_property_value(self):
        last_record = self.asset_record_list[-1]
        last_total = last_record.balance
        for asset in last_record.asset:
            last_total += asset[2] * last_record.quote[asset[0]]
        return round(last_total)
