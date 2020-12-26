from .log_manager import LogManager

class Analyzer():
    """
    거래 요청, 결과 정보를 저장하고 투자 결과를 분석하는 클래스
    """

    def __init__(self):
        self.request = []
        self.result = []
        self.asset_record_list = []
        self.request_asset_update_func = None
        self.logger = LogManager.get_logger(__name__)

    def put_request(self, request):
        """거래 요청 정보를 저장한다"""
        self.request.append(request)

    def put_result(self, result):
        """거래 결과 정보를 저장한다"""
        if self.request_asset_update_func is None:
            self.logger.warning("request_asset_update_func is NOT set")
            return

        self.result.append(result)
        self.request_asset_update_func()

    def initialize(self, request_asset_update_func):
        self.request_asset_update_func = request_asset_update_func

    def put_asset_info(self, asset_info):
        self.asset_record_list.append(asset_info)