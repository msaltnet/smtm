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

    def _execute_order(self, task):
        request = task["request"]
        if request["type"] == "cancel":
            self.cancel_request(request["id"])
            return

        ord_type = order_spec.get_ord_type(request)
        if ord_type not in self.SUPPORTED_ORD_TYPES:
            task["callback"](order_spec.make_rejected_result(
                request, f"unsupported ord_type: {ord_type}"))
            return

        is_buy = request["type"] == "buy"
        is_market = ord_type == order_spec.MARKET

        if not is_market and request["price"] == 0:
            # price==0 은 기존 no-op(hold) 신호 — 지정가에서는 무시
            self.logger.warning("[REJECT] limit order requires price")
            return

        if is_buy and float(request["price"]) * float(request["amount"]) > self.balance:
            self.logger.warning(
                f"[REJECT] balance is too small! "
                f"{float(request['price']) * float(request['amount'])} > {self.balance}"
            )
            task["callback"]("error!")
            return

        if is_buy is False and float(request["amount"]) > self.asset[1]:
            self.logger.warning(
                f"[REJECT] invalid amount {float(request['amount'])} > {self.asset[1]}"
            )
            task["callback"]("error!")
            return

        side = "buy" if is_buy else "sell"
        response = self._send_order(
            side, ord_type, request["price"], request["amount"])
        if response is None or not response.get("ordId"):
            task["callback"]("error!")
            return

        result = self._create_success_result(request)
        self.order_map[request["id"]] = {
            "order_id": response["ordId"],
            "callback": task["callback"],
            "result": result,
        }
        task["callback"](result)
        self.logger.debug(f"request inserted {self.order_map[request['id']]}")
        self._start_timer()

    def _send_order(self, side, ord_type, price, amount):
        """OKX 현물 주문 전송 (signed POST /api/v5/trade/order)

        - 지정가:      ordType=limit, px(가격), sz(코인 수량)
        - 시장가 매수:  ordType=market, tgtCcy=quote_ccy, sz(USDT 총액)
        - 시장가 매도:  ordType=market, tgtCcy=base_ccy,  sz(코인 수량)

        tgtCcy는 현물 시장가에서 방향에 따라 기본값이 달라지므로 양쪽 모두 명시한다.
        """
        payload = {"instId": self.market, "tdMode": "cash", "side": side}
        if ord_type == order_spec.MARKET and side == "buy":
            payload["ordType"] = "market"
            payload["tgtCcy"] = "quote_ccy"
            payload["sz"] = self._format_number(float(price) * float(amount))
        elif ord_type == order_spec.MARKET:
            payload["ordType"] = "market"
            payload["tgtCcy"] = "base_ccy"
            payload["sz"] = self._format_number(amount)
        else:
            payload["ordType"] = "limit"
            payload["px"] = self._format_number(price)
            payload["sz"] = self._format_number(amount)

        self.logger.info(f"ORDER ##### {side} {payload['ordType']}")
        self.logger.info(f"{self.market}, payload: {payload}")
        return self._signed_post("/api/v5/trade/order", payload)

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

        단, 재조회 결과의 state가 TERMINAL_STATES(filled/canceled/mmp_canceled)가
        아니면(예: live, partially_filled) 주문은 거래소에 여전히 살아있는
        것이다. 취소 POST가 네트워크 오류나 sCode 오류로 실패했는데 주문이
        아직 live 상태로 남아있거나, 취소 시도 중 부분체결만 반영된 경우가
        이에 해당한다. 이때 done 콜백을 쏘면 이미 order_map에서 지운 주문을
        영영 놓치고 이후 체결/잔여 수량을 반영하지 못하므로, order_map에
        되돌리고 폴링 타이머를 재시작해 기존 폴링 루프가 정상적으로
        재조회하도록 한다. (Binance는 취소 실패 시 재조회 결과의 상태를
        확인하지 않고 그대로 done 처리하는데, OKX cancel-order 응답이 체결
        정보를 전혀 담지 않아 상태 확인이 필수이므로 이 부분만 다르게
        처리한다. BinanceTrader는 건드리지 않는다.)
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

        if response.get("state") not in self.TERMINAL_STATES:
            self.logger.warning(
                f"order still working after cancel attempt, keep tracking: "
                f"{order['order_id']} state={response.get('state')}")
            self.order_map[request_id] = order
            self._start_timer()
            return

        result["date_time"] = datetime.now().strftime(self.ISO_DATEFORMAT)
        result["price"] = self._fill_price(response)
        result["amount"] = self._fill_amount(response)
        result["state"] = "done"
        self._call_callback(order["callback"], result)
