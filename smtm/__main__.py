"""smtm 모듈의 시작
mode:
    0 : simulator with interative mode
    1 : execute single simulation
    2 : controller for real trading
Example) python -m smtm --mode 0
Example) python -m smtm --mode 1
Example) python -m smtm --budget 50000 --from_dash_to 201220.170000-201220.180000 --term 1 --strategy 0
"""
import argparse
from . import Simulator

parser = argparse.ArgumentParser()
parser.add_argument("--budget", help="simulation budget", default="10000")
parser.add_argument("--term", help="simulation tick interval (seconds)", default="1")
parser.add_argument("--strategy", help="strategy 0: buy and hold, 1: sma0", default="0")
parser.add_argument(
    "--mode",
    help="0: interactive simulator, 1: single simulation, 2: real trading",
    default="1",
)
parser.add_argument(
    "--from_dash_to",
    help="use %%Y[-2:]%%m%%d.%%H%%M%%S format ex) 201220.170000-201220.180000",
    default="201220.170000-201220.180000",
)
args = parser.parse_args()

simulator = Simulator(
    budget=args.budget,
    interval=args.term,
    strategy=args.strategy,
    from_dash_to=args.from_dash_to,
)
if args.mode == "0":
    simulator.main()
elif args.mode == "1":
    simulator.run_single()
