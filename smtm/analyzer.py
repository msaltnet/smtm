from .log_manager import LogManager

class Analyzer():
    """
    거래 요청, 결과 정보를 저장하고 투자 결과를 분석하는 클래스
    """

    def __init__(self):
        self.request = []
        self.result = []
        self.asset_record_list = []
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

    def make_start_point(self):
        self.request = []
        self.result = []
        self.asset_record_list = []
        self.update_info_func("asset", self.put_asset_info)
