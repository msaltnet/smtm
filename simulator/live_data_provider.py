from . import DataProvider

# 거래소로부터 실시간 데이터를 수집해서 정보를 제공
class LiveDataProvider(DataProvider):
    url = None
    http = None
    state = None
    # 현재 거래 정보 전달
    def get_info(self):
        if self.http is None or self.state is None:
            return False

        response = self.http.get(self.url)
        # print()
        # print(response.text)
        return response

    def initialize(self, http, url):
        self.url = url
        self.http = http
        self.state = "initialized"
