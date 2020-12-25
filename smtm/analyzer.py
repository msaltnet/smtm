class Analyzer():
    """
    거래 요청, 결과 정보를 저장하고 투자 결과를 분석하는 클래스
    """

    def __init__(self):
        self.request = []
        self.result = []

    def put_request(self, request):
        """거래 요청 정보를 저장한다"""
        self.request.append(request)

    def put_result(self, result):
        """거래 결과 정보를 저장한다"""
        self.result.append(result)
