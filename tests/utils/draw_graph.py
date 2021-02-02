"""Data 가져와서 그래프 그리기

Example) python .\draw_graph.py --path=data50.json --mav="5,10,20"
"""
import argparse
import json
import mplfinance as mpf
import pandas as pd
import numpy as np


def get_average(list):
    sum = 0
    count = 0
    for item in list:
        sum += item
        count += 1
    return round(sum / count)


def get_sma_changes(ohlc, mav):
    sma = []
    initial_list = []
    sma_points = []
    closing_price = []
    for idx in range(len(mav)):
        initial_list.append(None)

    for idx in range(len(mav)):
        sma.append(
            {
                "count": mav[idx],
                "value": None,
                "is_higher": initial_list.copy(),
            }
        )

    for idx, item in enumerate(ohlc):
        closing_price.append(item["trade_price"])
        print(f"SMA for {idx} : {item['trade_price']} =========")
        # cal and update sma value
        for sma_idx, val in enumerate(sma.copy()):
            sma[sma_idx]["value"] = pd.Series(closing_price).rolling(val["count"]).mean().values[-1]

        # print and update change point
        point = []
        for sma_idx, val in enumerate(sma.copy()):
            if val["value"] is not None:
                print(f"SMA {val['count']:3}: {val['value']:20}")
            for sma_idx2, val2 in enumerate(sma.copy()):
                if (
                    sma_idx < sma_idx2
                    and np.isnan(val["value"]) == False
                    and np.isnan(val2["value"]) == False
                ):
                    is_higher = val["value"] > val2["value"]
                    if val["is_higher"][sma_idx2] != is_higher:
                        print(f"SMA Change {val['count']:3} & {val2['count']:3}, {val['value']}")
                        if val["is_higher"][sma_idx2] is not None:
                            point.append((val["count"], val["value"]))
                        sma[sma_idx]["is_higher"][sma_idx2] = is_higher

        if len(point) != 0:
            sma_points.append(point)
        else:
            sma_points.append(None)
    return sma_points


def draw_graph(filepath, mav=(5, 10)):
    if filepath is None:
        return

    new_mav = mav
    if isinstance(new_mav, str):
        new_mav = tuple(map(int, new_mav.split(",")))

    with open(filepath, "r") as data_file:
        json_data = json.loads(data_file.read())
    json_data.reverse()

    sma_map = {}
    sma_points = get_sma_changes(json_data, new_mav)
    for points in sma_points:
        if points is not None:
            for point in points:
                sma_map[str(point[0])] = True

    # print(sma_points)
    # print(sma_map.keys())
    for idx, val in enumerate(json_data.copy()):
        for key in sma_map.keys():
            json_data[idx][key] = None
            if sma_points[idx] is not None:
                for point in sma_points[idx]:
                    if key == str(point[0]):
                        json_data[idx][key] = point[1]
                        break

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

    apds = []
    for key in sma_map.keys():
        apds.append(mpf.make_addplot(total[key], type="scatter", markersize=50, marker="v"))

    mpf.plot(
        total,
        type="candle",
        volume=True,
        addplot=apds,
        mav=new_mav,
        style="starsandstripes",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", help="filepath", default="data.json")
    parser.add_argument("--mav", help="mav count ex) 5,10,20", default="5,10,20")
    args = parser.parse_args()

    draw_graph(args.path, args.mav)
