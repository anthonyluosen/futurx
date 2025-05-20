import requests
import logging
import time
from factor_crypto.write_mmap import *


class BinanceRest:
    def __init__(self, proxies=None):
        self.proxies = proxies
        self.logger = logging.getLogger("BinanceRest")

    def get_rest_fapi_weight(self):
        response = requests.get("https://fapi.binance.com/fapi/v1/ping", proxies=self.proxies)
        used_weight = int(response.headers.get('x-mbx-used-weight-1m', 0))
        weight_left = max(0, 1200 - used_weight)
        self.logger.info(f"当前已用权重: {used_weight} | 剩余可用: {weight_left}/1200")
        return weight_left

    def get_rest_fapi_klines(self, code, interval, start_time=None, end_time=None, limit=1000):
        base_url = "https://fapi.binance.com/fapi/v1/klines"
        params = {
            "symbol": code,
            "interval": interval,
            "limit": limit
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        response = requests.get(base_url, params=params, proxies=self.proxies)

        res = []
        if response.status_code == 200 and isinstance(response.json(), list):
            self.logger.info(r"请求成功 | HTTP状态码: {response.status_code}")
            klines = response.json()
            columns = [
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'count', 'taker_buy_volume',
                'taker_buy_quote_volume', 'ignore'
            ]
            for kline in klines:
                kline_dict = dict(zip(columns, kline))
                res.append(kline_dict)
            return res

        elif response.status_code == 429:
            self.logger.info(f"触发频率限制！错误信息: {response.text}")
            raise RuntimeError
        else:
            self.logger.info(f"请求失败 | HTTP状态码: {response.status_code} | 错误信息: {response.text}")
            raise RuntimeError

    def is_kline_complete(self, kline, interval):
        open_ts = kline['open_time']
        close_ts = kline['close_time']
        exp_close = open_ts + {
            '1m': 60000, '5m': 300000, '15m': 900000,
            '1h': 3600000, '4h': 14400000, '1d': 86400000
        }[interval] - 1
        return close_ts == exp_close

    def kline_to_mmap(self, time_ls, code, interval):
        code_loc = get_mmap_code_loc(code)
        sep_ls = sep_list(time_ls, 800)
        for ls in tqdm(sep_ls):
            start_tm = ls[0]
            end_tm = ls[-1]
            start_msts = second_str_to_msts(start_tm)
            end_msts = second_str_to_msts(end_tm)
            assert msts_to_second_str(start_msts) == start_tm
            assert msts_to_second_str(end_msts) == end_tm
            succ = False
            while not succ:
                weight_left = self.get_rest_fapi_weight()

                if weight_left > 300:
                    self.logger.info(rf'尝试下载k线 {code} {len(ls)} {start_tm} {end_tm}')
                    klines = self.get_rest_fapi_klines(code, interval,
                                                       start_time=start_msts, end_time=end_msts,
                                                       limit=1000)
                    # assert len(klines) == len(ls), (len(klines), len(ls), start_tm, end_tm)
                    for kline in klines:
                        assert self.is_kline_complete(kline, interval), kline
                        time_loc = get_mmap_time_loc(msts_to_second_str(kline['open_time']))
                        write_mmap_byloc(time_loc, code_loc, 'Open', kline['open'])
                        write_mmap_byloc(time_loc, code_loc, 'High', kline['high'])
                        write_mmap_byloc(time_loc, code_loc, 'Low', kline['low'])
                        write_mmap_byloc(time_loc, code_loc, 'Close', kline['close'])
                        write_mmap_byloc(time_loc, code_loc, 'Volume', kline['volume'])
                        write_mmap_byloc(time_loc, code_loc, 'Amt', kline['quote_volume'])
                    succ = True
                    for bn in base_name_list:
                        mmap_dict[bn].flush()
                    self.logger.info(rf'k线下载成功 {code} {len(ls)} {start_tm} {end_tm}')

                else:
                    self.logger.info(rf'权重不足，等待权重恢复')
                    time.sleep(60)

    def update_miss_kline(self, code, interval):
        time.sleep(0.1)
        last_update_time = get_last_mmap_update_time(code, base_name_list)
        now_time, now_comp_time = now_time_to_trade_time()
        time_to_update = [x for x in trade_time_cont if last_update_time < x <= now_comp_time]
        self.kline_to_mmap(time_to_update, code, interval)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    for code in tqdm(trade_code_list):
        interval = '15m'
        # last_update_time = get_last_mmap_update_time(code, base_name_list)
        last_update_time = trade_time_cont[0]
        now_time, now_comp_time = now_time_to_trade_time()
        time_to_update = trade_time_cont[:trade_time_cont.index('2025-05-16 23:45:00')]
        time_to_update = [x for x in time_to_update if last_update_time < x <= now_comp_time]
        display_ls(time_to_update, '')
        rest_api = BinanceRest()
        rest_api.kline_to_mmap(time_to_update, code, interval)
