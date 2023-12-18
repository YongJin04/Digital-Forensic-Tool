import sys
from datetime import datetime, timedelta

def decode_time(hex_str):
    decimal_time = int(hex_str, 16)

    seconds = decimal_time / 10000000

    start_date = datetime(1601, 1, 1)
  
    result_date = start_date + timedelta(seconds=seconds)

    return result_date.strftime("%Y년 %m월 %d일 %H시 %M분 %S.%f초")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 dataTimeDecoder.py <hex_value>")
    else:
        hex_str = sys.argv[1]
        print(decode_time(hex_str))

