"""Data 가져와서 파일로 저장

Example) python .\make_data_file.py --end="2021-01-30 11:00:00" --count=50 --path=data50.json
"""
import argparse
import requests
import json

URL = "https://api.upbit.com/v1/candles/minutes/1"
QUERY_STRING = {"market": "KRW-BTC"}


def get_data_from_server(end=None, count=100, filepath="data.json"):
    QUERY_STRING["to"] = end
    QUERY_STRING["count"] = count
    print(QUERY_STRING)
    response = requests.request("GET", URL, params=QUERY_STRING)
    response.raise_for_status()
    data = json.loads(response.text)
    data.reverse()
    with open(filepath, "w") as f:
        f.write(response.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--end",
        help="end datetime yyyy-MM-dd HH:mm:ss ex)2020-02-10T17:50:37",
        default=None,
    )
    parser.add_argument("--count", help="tick count", default=100)
    parser.add_argument("--path", help="tick interval (seconds)", default="data.json")
    args = parser.parse_args()

    get_data_from_server(args.end, args.count, args.path)
