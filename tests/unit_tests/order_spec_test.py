import unittest

from smtm.trader import order_spec
from smtm.trader.trader import Trader


class OrderSpecTest(unittest.TestCase):
    def test_get_ord_type_defaults_to_limit_when_absent(self):
        self.assertEqual(order_spec.get_ord_type({"type": "buy"}), "limit")

    def test_get_ord_type_defaults_to_limit_when_none(self):
        self.assertEqual(order_spec.get_ord_type({"ord_type": None}), "limit")

    def test_get_ord_type_returns_declared_value(self):
        self.assertEqual(order_spec.get_ord_type({"ord_type": "market"}), "market")

    def test_is_conditional_true_for_stop_loss(self):
        self.assertTrue(order_spec.is_conditional({"ord_type": "stop_loss"}))

    def test_is_conditional_false_for_limit(self):
        self.assertFalse(order_spec.is_conditional({"type": "buy"}))

    def test_make_rejected_result_shape(self):
        req = {"id": "1", "type": "buy", "price": 100, "amount": 2}
        result = order_spec.make_rejected_result(req, "unsupported ord_type: oco")
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["msg"], "unsupported ord_type: oco")
        self.assertEqual(result["price"], 0)
        self.assertEqual(result["amount"], 0)
        self.assertEqual(result["type"], "buy")
        self.assertIs(result["request"], req)

    def test_base_trader_supports_limit_only_by_default(self):
        self.assertEqual(Trader.SUPPORTED_ORD_TYPES, frozenset({"limit"}))
