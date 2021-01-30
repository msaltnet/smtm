"""Data 가져와서 파일로 저장"""
import argparse
import json
import mplfinance as mpf
import pandas as pd
import numpy as np


def draw_graph(filepath, mav=(5, 10)):
    if filepath is None:
        return

    new_mav = mav
    if isinstance(new_mav, str):
        new_mav = tuple(map(int, new_mav.split(",")))

    with open(filepath, "r") as data_file:
        json_data = json.loads(data_file.read())

    total = pd.DataFrame(json_data)
    total = total.rename(
        columns={
            "candle_date_time_kst": "Date",
            "opening_price": "Open",
            "high_price": "High",
            "low_price": "Low",
            "trade_price": "Close",
            "candle_acc_trade_volume": "Volume",
        }
    )
    total = total.set_index("Date")
    total.index = pd.to_datetime(total.index)
    mpf.plot(
        total,
        type="candle",
        volume=True,
        mav=new_mav,
        style="starsandstripes",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", help="filepath", default="data.json")
    parser.add_argument("--mav", help="mav count ex) 5,10,20", default="5,10,20")
    args = parser.parse_args()

    draw_graph(args.path, args.mav)
