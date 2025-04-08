#coding=utf-8

import pandas as pd
import os

import struct

"""
读取通达信日线数据
"""

class BaseReader(object):

    def unpack_records(self, format, data):
        record_struct = struct.Struct(format)
        return (record_struct.unpack_from(data, offset)
                for offset in range(0, len(data), record_struct.size))

    def get_df(self, code_or_file, exchange=None):
        raise NotImplementedError('not yet')

class TdxDailyBarReader(BaseReader):

    def __init__(self, vipdoc_path=None):
        
        self.vipdoc_path = vipdoc_path

    def generate_filename(self, code, exchange):
        
        if self.vipdoc_path == None:
            return

        fname = os.path.join(self.vipdoc_path, exchange)
        fname = os.path.join(fname, 'lday')
        fname = os.path.join(fname, '%s%s.day' % (exchange, code))        
        return fname
    
    def get_kline_by_code(self, code, exchange):
        
        fname = self.generate_filename(code, exchange)        
        return self.parse_data_by_file(fname)

    def parse_data_by_file(self, fname,line = -1):

        if not os.path.isfile(fname):
            raise RuntimeError('no tdx kline data, pleaes check path %s', fname)

        with open(fname, 'rb') as f:
            str_format = '<IIIIIfII'
            line_size = struct.Struct(str_format).size
            if line == -1:
                content = f.read()
            else:
                size = f.seek(0,os.SEEK_END)
                offset = size - (line_size *line)
                f.seek(max(0,offset))
                content = f.read()
            return self.unpack_records(str_format, content)
        return []
    
    def get_df(self, code_or_file, exchange=None,line = -1):

        if exchange == None:
            return self.get_df_by_file(code_or_file,line)
        else:
            return self.get_df_by_code(code_or_file, exchange,line)
        
    def get_df_by_file(self, fname,line = -1):

        if not os.path.isfile(fname):
            raise RuntimeError('no tdx kline data, pleaes check path %s', fname)
            
        security_type = self.get_security_type(fname)
        if security_type not in self.SECURITY_TYPE:
            print("Unknown security type !\n")
            raise NotImplementedError

        coefficient = self.SECURITY_COEFFICIENT[security_type]
        data = [self._df_convert(row, coefficient) for row in self.parse_data_by_file(fname,line)]

        df = pd.DataFrame(data=data, columns=('trade_date', 'open', 'high', 'low', 'close', 'amount', 'volume'))
        df.index = pd.to_datetime(df.trade_date)
        return df[['open', 'high', 'low', 'close', 'amount', 'volume']]

    def get_df_by_code(self, code, exchange,line = -1):

        fname = self.generate_filename(code, exchange)
        return self.get_df_by_file(fname,line)

    def _df_convert(self, row, coefficient):
        t_date = str(row[0])
        datestr = t_date[:4] + "-" + t_date[4:6] + "-" + t_date[6:]

        new_row = (
            datestr,
            row[1] * coefficient[0], # * 0.01 * 1000 , zipline need 1000 times to original price
            row[2] * coefficient[0],
            row[3] * coefficient[0],
            row[4] * coefficient[0],
            row[5],
            row[6] * coefficient[1]
        )
        return new_row

    def get_security_type(self, fname):

        exchange = str(fname[-12:-10]).lower()
        code_head = fname[-10:-8]

        if exchange == self.SECURITY_EXCHANGE[0]:
            if code_head in ["00", "30"]:
                return "SZ_A_STOCK"
            elif code_head in ["20"]:
                return "SZ_B_STOCK"
            elif code_head in ["39"]:
                return "SZ_INDEX"
            elif code_head in ["15", "16"]:
                return "SZ_FUND"
            elif code_head in ["10", "11", "12", "13", "14"]:
                return "SZ_BOND"
        elif exchange == self.SECURITY_EXCHANGE[1]:
            if code_head in ["60","68"]:
                return "SH_A_STOCK"
            elif code_head in ["90"]:
                return "SH_B_STOCK"
            elif code_head in ["00", "88", "99"]:
                return "SH_INDEX"
            elif code_head in ["50", "51"]:
                return "SH_FUND"
            elif code_head in ["01", "10", "11", "12", "13", "14"]:
                return "SH_BOND"
        elif exchange == self.SECURITY_EXCHANGE[2]:
            return "BJ_A_STOCK"
        else:
            print("Unknown security exchange !\n")
            raise NotImplementedError

    SECURITY_EXCHANGE = ["sz", "sh","bj"]
    SECURITY_TYPE = ["SH_A_STOCK", "SH_B_STOCK", "SH_INDEX", "SH_FUND", "SH_BOND", "SZ_A_STOCK", "SZ_B_STOCK", "SZ_INDEX", "SZ_FUND", "SZ_BOND","BJ_A_STOCK"]
    SECURITY_COEFFICIENT = {"BJ_A_STOCK":[0.01,0.01],"SH_A_STOCK": [0.01, 0.01], "SH_B_STOCK": [0.001, 0.01], "SH_INDEX": [0.01, 1.0], "SH_FUND": [0.001, 1.0], "SH_BOND": [0.001, 1.0], "SZ_A_STOCK": [0.01, 0.01], "SZ_B_STOCK": [0.01, 0.01], "SZ_INDEX": [0.01, 1.0], "SZ_FUND": [0.001, 0.01], "SZ_BOND": [0.001, 0.01]}

if __name__ == '__main__':
    tdx_reader = TdxDailyBarReader('d:/TDX/vipdoc/')
    df = tdx_reader.get_df('000001', 'sz',1)
    print(df)
