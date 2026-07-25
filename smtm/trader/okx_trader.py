import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from .base_exchange_trader import BaseExchangeTrader
from . import order_spec


class OkxTrader(BaseExchangeTrader):
    """
    OKX 현물(spot) 거래소를 통한 거래 요청 및 계좌 조회를 처리하는 Trader

    OkxTrader processes spot trading requests and account inquiries via OKX.

    id: 요청 정보 id
    type: 거래 유형 buy, sell, cancel
    price: 거래 가격 (USDT)
    amount: 거래 수량 (코인)

    OKX는 access/secret 외에 passphrase를 요구하며, 업무 오류도 HTTP 200에
    {"code": "0|기타", "data": [...]} 봉투로 실어 보낸다. _unwrap이 이를 처리한다.

    https://www.okx.com/docs-v5/en/
    """

    AVAILABLE_CURRENCY = {
        "BTC": ("BTC-USDT", "BTC"),
        "ETH": ("ETH-USDT", "ETH"),
        "DOGE": ("DOGE-USDT", "DOGE"),
        "XRP": ("XRP-USDT", "XRP"),
    }
    NAME = "OKX"
    CODE = "OKX"
    SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})
    USES_PASSPHRASE = True
    #: 더 이상 오더북에 남지 않는 상태. 폴링 대상에서 제거해야 한다.
    TERMINAL_STATES = frozenset({"filled", "canceled", "mmp_canceled"})

    def __init__(
        self, budget=50000, currency="BTC", commission_ratio=0.001, opt_mode=True,
        access_key_env=None, secret_key_env=None, passphrase_env=None,
    ):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        super().__init__(
            budget=budget,
            currency=currency,
            commission_ratio=commission_ratio,
            opt_mode=opt_mode,
            logger_name="OkxTrader",
            worker_name="OkxTrader-Worker",
            env_key_names=(
                access_key_env or "OKX_API_ACCESS_KEY",
                secret_key_env or "OKX_API_SECRET_KEY",
                "OKX_API_SERVER_URL",
            ),
        )
        if not self.SERVER_URL:
            self.SERVER_URL = "https://www.okx.com"
        self.PASSPHRASE = os.environ.get(passphrase_env or "OKX_API_PASSPHRASE", "")
        if not self.PASSPHRASE:
            self.logger.warning("OkxTrader passphrase is not set")
        self.is_demo = os.environ.get("OKX_API_DEMO", "").lower() in ("1", "true", "yes")
        currency_info = self.AVAILABLE_CURRENCY[currency]
        self.market = currency_info[0]
        self.market_currency = currency_info[1]

    @staticmethod
    def _timestamp():
        """OKX 서명용 UTC ISO8601 타임스탬프 (밀리초 3자리). 예: 2026-07-25T09:08:57.715Z"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def _create_signature(self, timestamp, method, request_path, body=""):
        """base64(HMAC-SHA256(timestamp + METHOD + requestPath + body))

        request_path는 쿼리스트링을 포함한 경로여야 하며, 실제 요청 URL과
        정확히 같아야 서명이 통과한다.
        """
        prehash = f"{timestamp}{method.upper()}{request_path}{body}"
        return base64.b64encode(
            hmac.new(self.SECRET_KEY.encode(), prehash.encode(), hashlib.sha256).digest()
        ).decode()

    def _auth_headers(self, method, request_path, body=""):
        timestamp = self._timestamp()
        headers = {
            "OK-ACCESS-KEY": self.ACCESS_KEY,
            "OK-ACCESS-SIGN": self._create_signature(
                timestamp, method, request_path, body),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.PASSPHRASE,
            "Content-Type": "application/json",
        }
        if self.is_demo:
            headers["x-simulated-trading"] = "1"
        return headers

    def _validate_credentials(self):
        """기반 클래스는 access/secret/server_url만 검사하므로 passphrase를 덧붙인다"""
        if not super()._validate_credentials():
            return False
        if not self.PASSPHRASE:
            self.logger.error("OKX passphrase is not configured")
            return False
        return True

    def _unwrap(self, response):
        """OKX 응답 봉투를 해제해 data[0]을 반환. 실패면 None.

        업무 오류가 HTTP 200으로 오고, 실패가 최상위 code와 data[0].sCode 두 층에
        나뉜다. 최상위 code!=0일 때 구체적 사유는 data[0].sMsg에만 담긴다.
        """
        if response is None:
            return None
        data = response.get("data") or []
        first = data[0] if data and isinstance(data[0], dict) else None
        if str(response.get("code")) != "0":
            detail = first.get("sMsg") if first else None
            self.logger.error(
                f"OKX error {response.get('code')}: {detail or response.get('msg')}")
            return None
        if not data:
            self.logger.error("OKX response has empty data")
            return None
        if first is not None and first.get("sCode") not in (None, "", "0"):
            self.logger.error(
                f"OKX order error {first.get('sCode')}: {first.get('sMsg')}")
            return None
        return data[0]

    def _signed_get(self, path, params):
        """서명 GET. 서명 문자열의 requestPath와 실제 URL 쿼리가 반드시 일치해야 하므로
        쿼리를 한 번만 만들어 양쪽에 같이 쓴다 (requests의 params=를 쓰지 않는다)."""
        if not self._validate_credentials():
            return None
        request_path = f"{path}?{urlencode(params)}"
        return self._unwrap(self._request_get(
            self.SERVER_URL + request_path,
            headers=self._auth_headers("GET", request_path),
        ))

    def _signed_post(self, path, payload):
        """서명 POST. 서명한 JSON 문자열과 전송 바디가 반드시 같아야 하므로
        직렬화 결과를 한 번만 만들어 재사용한다."""
        if not self._validate_credentials():
            return None
        body = json.dumps(payload)
        return self._unwrap(self._request_post(
            self.SERVER_URL + path,
            headers=self._auth_headers("POST", path, body),
            data=body,
        ))

    @staticmethod
    def _format_number(value):
        """지수표기 없이 고정소수점 문자열로 포맷 (OKX 파라미터 대비).
        최대 8자리 소수, 불필요한 0/소수점 제거. instId별 lotSz/tickSz
        정밀 라운딩은 /api/v5/public/instruments 조회가 필요하므로 후속 과제."""
        formatted = f"{float(value):.8f}".rstrip("0").rstrip(".")
        return formatted if formatted else "0"

    def get_trade_tick(self):
        """최근 체결가(현재가) 조회 — public 엔드포인트"""
        return self._unwrap(self._request_get(
            self.SERVER_URL + "/api/v5/market/ticker",
            params={"instId": self.market},
        ))

    def get_account_info(self):
        """계좌 정보를 요청한다 (로컬 잔고/자산 + 실시간 시세)

        Returns:
            {
                balance: 계좌 현금 잔고 (USDT)
                asset: {코인: (평균 매입가, 수량)}
                quote: {코인: 현재가}
                date_time: 현재 시간
            }
        """
        result = {
            "balance": self.balance,
            "asset": {self.market_currency: self.asset},
            "quote": {},
            "date_time": datetime.now().strftime(self.ISO_DATEFORMAT),
        }
        trade_info = self.get_trade_tick()
        if trade_info is not None and "last" in trade_info:
            result["quote"][self.market_currency] = float(trade_info["last"])
        else:
            self.logger.error("fail query quote")
        self.logger.debug(f"account info {result}")
        return result

    def _query_order(self, order_id):
        """주문 상태 조회 (signed GET /api/v5/trade/order)"""
        return self._signed_get(
            "/api/v5/trade/order", {"instId": self.market, "ordId": order_id})

    def _cancel_order(self, order_id):
        """주문 취소 (signed POST /api/v5/trade/cancel-order)

        Binance의 DELETE와 달리 응답은 {ordId, clOrdId, sCode, sMsg}뿐이며
        체결 정보를 담지 않는다.
        """
        return self._signed_post(
            "/api/v5/trade/cancel-order", {"instId": self.market, "ordId": order_id})

    @staticmethod
    def _fill_price(response):
        """체결 평단. OKX는 avgPx를 직접 제공하며, 미체결이면 빈 문자열로 온다."""
        return float(response.get("avgPx") or 0)

    @staticmethod
    def _fill_amount(response):
        """누적 체결 수량. 미체결이면 0."""
        return float(response.get("accFillSz") or 0)

    def cancel_request(self, request_id):
        """거래 요청을 취소한다

        OKX cancel-order 응답에는 체결 정보(accFillSz/avgPx)가 없으므로 취소
        성공/실패와 무관하게 주문 조회로 최종 상태를 확정한다. 취소 실패는
        이미 체결됐을 가능성을 포함하므로 같은 경로로 처리된다.
        """
        if request_id not in self.order_map:
            self.logger.debug(f"already canceled or unknown: {request_id}")
            return

        order = self.order_map[request_id]
        del self.order_map[request_id]
        result = order["result"]

        self._cancel_order(order["order_id"])
        response = self._query_order(order["order_id"])
        if response is None:
            self.logger.error(
                f"fail confirm order state after cancel: {order['order_id']}")
            return

        result["date_time"] = datetime.now().strftime(self.ISO_DATEFORMAT)
        result["price"] = self._fill_price(response)
        result["amount"] = self._fill_amount(response)
        result["state"] = "done"
        self._call_callback(order["callback"], result)
