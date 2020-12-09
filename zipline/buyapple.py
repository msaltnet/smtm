from zipline.api import order, record, symbol
from zipline.finance import commission, slippage


def initialize(context):
    context.asset = symbol('AAPL')

    # Explicitly set the commission/slippage to the "old" value until we can
    # rebuild example data.
    # github.com/quantopian/zipline/blob/master/tests/resources/
    # rebuild_example_data#L105
    context.set_commission(commission.PerShare(cost=.0075, min_trade_cost=1.0))
    context.set_slippage(slippage.VolumeShareSlippage())


def handle_data(context, data):
    order(context.asset, 10)
    record(AAPL=data.current(context.asset, 'price'))
#    print('HIT')

#zipline run -f ./buyapple.py --start 2016-1-1 --end 2018-1-1 -o buyapple_out.pickle --no-benchmark
