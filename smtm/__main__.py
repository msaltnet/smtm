"""smtm 모듈의 시작
mode:
    0 : simulator with interative mode
    1 : controller for real trading
    2 : execute single simulation
Example) python -m smtm --mode 0
Example) python -m smtm --mode 1
Example) python -m smtm --mode 2 --count 100 --end 2020-12-20T18:00:00Z --term 1 --strategy 0
Example) python -m smtm --from_dash_to 20201220.170000-20201220.180000 --term 1 --strategy 0
"""
import argparse
from . import Simulator

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--end",
        help="simulation end datetime yyyy-MM-dd HH:mm:ss ex)2020-02-10T17:50:37",
        default=None,
    )
    parser.add_argument("--count", help="simulation tick count", default="100")
    parser.add_argument("--term", help="simulation tick interval (seconds)", default="1")
    parser.add_argument("--strategy", help="strategy 0: buy and hold, 1: sma0", default="0")
    parser.add_argument("--mode", help="mode 0 : simulation, mode 1 : real trading", default="2")
    parser.add_argument("--from_dash_to", help="use %Y%m%d.%H%M%S ex) 20201220.170000-20201220.180000", default=None)
    args = parser.parse_args()

    if args.mode == "0":
        simulator = Simulator(args.end, args.count, args.term, args.strategy, args.from_dash_to)
        simulator.main()
    elif args.mode == "2":
        simulator = Simulator(args.end, args.count, args.term, args.strategy, args.from_dash_to)
        simulator.run_single()
