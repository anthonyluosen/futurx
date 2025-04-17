import pickle
import math


def load_pickle(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


# 辅助数据存放位置
from gen_facfmk_config import facfmk_root_path, config_data_path, label_data_path, base_itvl

tsbt_support_path = rf'{facfmk_root_path}/support_data'
# 基础字段路径
base_data_fea_root_path = rf'{facfmk_root_path}/BaseData/Feather'
base_data_mmap_root_path = rf'{facfmk_root_path}/BaseData/Mmap'
# 因子输出路径
factor_output_path_root = rf'{facfmk_root_path}/FactorOutput'

# 时间 -> idx dim0
trade_time_loc_dict = load_pickle(rf'{config_data_path}/trade_time_loc_dict.pkl')
# 股票 -> idx dim1
trade_code_loc_dict = load_pickle(rf'{config_data_path}/trade_code_loc_dict.pkl')
# 日期 -> idx 日期序列上的位置，每日占一个位置
trade_date_loc_dict = load_pickle(rf'{config_data_path}/trade_date_loc_dict.pkl')
# 连续的时间轴
trade_time_cont = load_pickle(rf'{config_data_path}/trade_time_cont.pkl')

date_num = len(list(trade_date_loc_dict.keys()))  # 改成了有效的日期天数
code_num = len(list(trade_code_loc_dict.keys()))  # 只保留有效标的
time_step_num = len(list(trade_time_loc_dict.keys()))

# 手工指定的标的列表
code_str_ls1 = load_pickle(rf'{tsbt_support_path}/code_str_ls1.pkl')
code_str_ls2 = load_pickle(rf'{tsbt_support_path}/code_str_ls2.pkl')
code_str_ls3 = load_pickle(rf'{tsbt_support_path}/code_str_ls3.pkl')
code_str_ls4 = load_pickle(rf'{tsbt_support_path}/code_str_ls4.pkl')
# code_idx_ls1 = load_pickle(rf'{tsbt_support_path}/code_idx_ls1.pkl')
# code_idx_ls2 = load_pickle(rf'{tsbt_support_path}/code_idx_ls2.pkl')
# code_idx_ls3 = load_pickle(rf'{tsbt_support_path}/code_idx_ls3.pkl')
# code_idx_ls4 = load_pickle(rf'{tsbt_support_path}/code_idx_ls4.pkl')
# valid_mask_daily_ls1 = load_pickle(rf'{tsbt_support_path}/valid_mask_daily_ls1.pkl')


class GlobalConfig:
    # 指定计算的标的idx
    sel_code_list = None
    # sel_code_list = load_pickle(rf'{tsbt_support_path}/code_idx_ls1.pkl')
    # 基础数据和计算设定
    date_num = date_num
    code_num = code_num
    sel_code_num = code_num if sel_code_list is None else len(sel_code_list)
    base_data_time_step_1d = len(list(trade_time_loc_dict.keys()))
    base_data_shape = (date_num * base_data_time_step_1d, code_num)
    base_data_shape_1d = (date_num * base_data_time_step_1d,)
    # 为时序算子前d个时间步产生空值而预留的额外时间步
    time_step_left_for_nan = base_data_time_step_1d
    # 每个循环进行的时间步
    # 自动选择time_step_each_loop数量。如果其设置过大导致显存不足，尝试减小每个循环时间步的数量
    time_step_each_loop_try_list = [1440 * x for x in [5, 3, 2, 1]]

    # 回测相关设定
    backtest_group_num = 20
    backtest_head_num_list = [1, 3, 5]
    backtest_tail_num_list = [1, 3, 5]

    # 因子计算使用的设备
    use_device = 'cpu'
    # use_device = 'cuda:0'

    # 相关数据
    trade_date_list = []
    trade_code_list = []

    # 路径
    base_data_root_path = base_data_mmap_root_path
    factor_output_path_root = factor_output_path_root

    # 临时变量字典
    temp_data_dict = dict()
    trade_time_loc_dict = None
    trade_code_loc_dict = None
    trade_date_loc_dict = None


GlobalConfig.trade_time_loc_dict = trade_time_loc_dict
GlobalConfig.trade_code_loc_dict = trade_code_loc_dict
GlobalConfig.trade_date_loc_dict = trade_date_loc_dict
GlobalConfig.trade_date_list = sorted(GlobalConfig.trade_date_loc_dict,
                                      key=lambda k: GlobalConfig.trade_date_loc_dict[k])
GlobalConfig.trade_code_list = sorted(GlobalConfig.trade_code_loc_dict,
                                      key=lambda k: GlobalConfig.trade_code_loc_dict[k])


# 对于base_data_slice_list 第一个slice总是从0开始 每个silce的长度是time_step_each_loop+time_step_left_for_nan 相邻slice的重合量是time_step_left_for_nan
# 对于output_data_slice_list 第一个slice总是从time_step_left_for_nan开始 每个silce的长度是time_step_each_loop 相邻slice的重合量是0
def get_slice_for_fac_exp_exec_loop_all(tot_time_step: int, time_step_each_loop: int, time_step_left_for_nan: int):
    tot_valid_time_step = tot_time_step - time_step_left_for_nan
    num_loop = math.floor(tot_valid_time_step / time_step_each_loop)
    base_data_slice_list = [slice(time_step_left_for_nan + i * time_step_each_loop - time_step_left_for_nan,
                                  time_step_left_for_nan + (i + 1) * time_step_each_loop)
                            for i in range(num_loop)]
    base_data_slice_list.append(
        slice(time_step_left_for_nan + num_loop * time_step_each_loop - time_step_left_for_nan, tot_time_step))
    output_data_slice_list = [slice(time_step_left_for_nan + i * time_step_each_loop,
                                    time_step_left_for_nan + (i + 1) * time_step_each_loop)
                              for i in range(num_loop)]
    output_data_slice_list.append(
        slice(time_step_left_for_nan + num_loop * time_step_each_loop, tot_time_step))
    return base_data_slice_list, output_data_slice_list


# 日期转换信息
# 根据一日当中的时间步长，日期列表，选定计算日期，每次计算时间步数量等推出计算所需的切片索引
# 2D代表专用于二维数据，第一维为时间，第二维为标的
class DateConfig2D:
    def __init__(self, time_step_1d, trade_date_list, calc_date_list=None, calc_start=None, calc_end=None,
                 calc_mode=None, date_num=None, code_num=None, intraday_data_only=None):
        assert intraday_data_only in [True, False]
        self.time_step_1d = time_step_1d
        self.trade_date_list = trade_date_list
        # 如果指定日期列表 这时默认按天计算
        if (not calc_start) and (not calc_end) and calc_date_list:
            self.calc_date_list = calc_date_list
            assert calc_mode == 'daily'
            assert intraday_data_only == True
        # 如果指定起止日期 可以连续计算也可以按天计算
        elif calc_start and calc_end and (not calc_date_list):
            self.calc_date_list = [x for x in trade_date_list if calc_start <= x <= calc_end]
            assert calc_mode in ['cont', 'daily']
            if calc_mode == 'cont':
                assert intraday_data_only == False
            if calc_mode == 'daily':
                assert intraday_data_only == True
        else:
            raise NotImplementedError
        self.calc_start = calc_start
        self.calc_end = calc_end
        self.calc_mode = calc_mode
        # 是否只使用当日数据
        self.intraday_data_only = intraday_data_only
        self.output_shape = self._get_output_shape(date_num=date_num, code_num=code_num)

    def get_calc_slice(self, time_step_each_loop, time_step_left_for_nan, return_type):
        # 连续计算 前面time_step_left_for_nan个时间步是空值
        if self.calc_mode == 'cont':
            start_date_idx = self.trade_date_list.index(self.calc_start)
            end_date_idx = self.trade_date_list.index(self.calc_end)
            # 例如，start_date_idx=2，则应该从2*target_data_time_step_1d开始计算
            start_delta = start_date_idx * self.time_step_1d
            # 根据计算天数确定总共计算的时间步数量
            tot_time_step = (end_date_idx - start_date_idx + 1) * self.time_step_1d
            base_data_slice_list, output_data_slice_list = get_slice_for_fac_exp_exec_loop_all(tot_time_step,
                                                                                               time_step_each_loop,
                                                                                               time_step_left_for_nan)
            base_data_slice_list = [slice(x.start + start_delta, x.stop + start_delta) for x in base_data_slice_list]
            # output_data不加start_delta

        # # 按天计算 旧版
        # # 每次补前一天的数值以应对空值 强制要求time_step_left_for_nan=time_step_each_loop=time_step_1d
        # # 同时 要求天数列表最早只能从第二天开始 否则找不到前一日数据
        # # 注意 daily模式要找上一个日期的数据 所以暂时不支持trade_date_list为乱序或不连续的情形
        # elif self.calc_mode == 'daily':
        #     assert time_step_left_for_nan == time_step_each_loop == self.time_step_1d, (
        #         self.calc_mode, time_step_left_for_nan, time_step_each_loop, self.time_step_1d)
        #     assert min(self.calc_date_list) > min(self.trade_date_list), (
        #         min(self.calc_date_list), min(self.trade_date_list))
        #     base_data_slice_list = []
        #     for date in self.calc_date_list:
        #         start_date_idx = self.trade_date_list.index(date) - 1  # -1代表填充一日
        #         end_date_idx = self.trade_date_list.index(date)
        #         # 例如，start_date_idx=2，则应该从2*target_data_time_step_1d开始计算
        #         start_delta = start_date_idx * self.time_step_1d
        #         # 根据计算天数确定总共计算的时间步数量
        #         tot_time_step = (end_date_idx - start_date_idx + 1) * self.time_step_1d
        #         base_data_slice_list_daily, _ = get_slice_for_fac_exp_exec_loop_all(
        #             tot_time_step,
        #             time_step_each_loop,
        #             time_step_left_for_nan)
        #         base_data_slice_list += [slice(x.start + start_delta, x.stop + start_delta) for x in
        #                                  base_data_slice_list_daily[:1]]
        #     # output_data不加start_delta
        #     # 注意调用的时候令time_step_left_for_nan=0且跳过最后一个长度为0的slice
        #     tot_time_step = len(self.calc_date_list) * self.time_step_1d
        #     _, output_data_slice_list = get_slice_for_fac_exp_exec_loop_all(tot_time_step,
        #                                                                     time_step_each_loop,
        #                                                                     0)
        #     if output_data_slice_list[-1].stop == output_data_slice_list[-1].start:
        #         output_data_slice_list = output_data_slice_list[:-1]
        #     assert len(base_data_slice_list) == len(output_data_slice_list) == len(self.calc_date_list)

        # 按天计算 新版
        # 暂时强制要求只使用当日数据，所以支持trade_date_list为乱序或不连续的情形
        elif self.calc_mode == 'daily':
            base_data_slice_list = []
            for date in self.calc_date_list:
                # 当日的idx
                date_idx = self.trade_date_list.index(date)
                # 注意此start可能为负值，这时在fac_exp_exec中需要额外做操作
                # 实际的slice长度为time_step_1d + time_step_left_for_nan
                start = date_idx * self.time_step_1d - time_step_left_for_nan
                stop = (date_idx + 1) * self.time_step_1d
                base_data_slice_list += [slice(start, stop)]

            # output_data不加start_delta
            # 注意调用的时候令time_step_each_loop=time_step_1d, time_step_left_for_nan=0且跳过最后一个长度为0的slice
            tot_time_step = len(self.calc_date_list) * self.time_step_1d
            _, output_data_slice_list = get_slice_for_fac_exp_exec_loop_all(tot_time_step,
                                                                            self.time_step_1d,
                                                                            0)
            if output_data_slice_list[-1].stop == output_data_slice_list[-1].start:
                output_data_slice_list = output_data_slice_list[:-1]
            assert len(base_data_slice_list) == len(output_data_slice_list) == len(self.calc_date_list), (
                base_data_slice_list, output_data_slice_list)

        else:
            raise NotImplementedError
        return {'base_data': base_data_slice_list, 'output_data': output_data_slice_list}[return_type]

    def get_output_data_time_loc_in_base_data(self, base_data_time_step_1d, output_data_time_loc_list):
        output_data_time_loc_in_base_data = []
        for date in self.calc_date_list:
            date_idx = self.trade_date_list.index(date)
            output_data_time_loc_in_base_data += [x + date_idx * base_data_time_step_1d for x in
                                                  output_data_time_loc_list]
        return output_data_time_loc_in_base_data

    def _get_output_shape(self, date_num=None, code_num=None):
        if date_num is None:
            date_num = len(self.calc_date_list)
        elif date_num:
            assert date_num == len(self.calc_date_list)
        if code_num is None:
            code_num = GlobalConfig.sel_code_num
        if code_num == 0:
            return (date_num * self.time_step_1d,)
        return (date_num * self.time_step_1d, code_num)

    def reset_output_shape(self, code_num):
        self.output_shape = self._get_output_shape(date_num=len(self.calc_date_list), code_num=code_num)

    def get_output_slice_one_date(self, date):
        # 目前仅支持对输出数据使用
        assert self.trade_date_list == self.calc_date_list
        date_idx = self.trade_date_list.index(date)
        return slice(date_idx * self.time_step_1d, (date_idx + 1) * self.time_step_1d)


# 输入输出的日期信息配对
class DateConfig2DMatch:
    def __init__(self, base_data_date_config: DateConfig2D, output_data_date_config: DateConfig2D):
        assert base_data_date_config.trade_date_list == output_data_date_config.trade_date_list
        assert base_data_date_config.calc_date_list == output_data_date_config.calc_date_list
        assert base_data_date_config.calc_start == output_data_date_config.calc_start
        assert base_data_date_config.calc_end == output_data_date_config.calc_end
        assert base_data_date_config.calc_mode == output_data_date_config.calc_mode
        assert base_data_date_config.intraday_data_only == output_data_date_config.intraday_data_only
        assert base_data_date_config.output_shape[0] == output_data_date_config.output_shape[0]
        self.trade_date_list = base_data_date_config.trade_date_list
        self.calc_date_list = base_data_date_config.calc_date_list
        self.calc_start = base_data_date_config.calc_start
        self.calc_end = base_data_date_config.calc_end
        self.calc_mode = base_data_date_config.calc_mode
        self.intraday_data_only = base_data_date_config.intraday_data_only

        self.base_data_date_config = base_data_date_config
        self.output_data_date_config = output_data_date_config

    def get_calc_slice(self, time_step_each_loop, time_step_left_for_nan):
        base_data_slice_list = self.base_data_date_config.get_calc_slice(time_step_each_loop, time_step_left_for_nan,
                                                                         'base_data')
        output_data_slice_list = self.output_data_date_config.get_calc_slice(time_step_each_loop,
                                                                             time_step_left_for_nan, 'output_data')
        assert len(base_data_slice_list) == len(output_data_slice_list)
        return base_data_slice_list, output_data_slice_list


# 每种输出数据类型的信息
class OutputConfig:
    def __init__(self, factor_output_name, output_data_time_list,
                 trade_time_loc_dict=GlobalConfig.trade_time_loc_dict,
                 factor_output_path_root=GlobalConfig.factor_output_path_root):
        self.factor_output_name = factor_output_name
        # 输出因子的存储目录
        self.factor_output_path = rf'{factor_output_path_root}/{factor_output_name}'
        # 形如 [959*100000, 1029*100000]
        self.output_data_time_list = output_data_time_list
        self.trade_time_loc_dict = trade_time_loc_dict
        # 形如 [29, 59],  输出数据在base_data中的idx，长度为date_num * base_data_time_step_1d
        self.output_data_time_loc_list = [trade_time_loc_dict[time] for time in output_data_time_list]
        self.output_data_time_step_1d = len(self.output_data_time_loc_list)

        # 跟日期相关的形状推断转移至date_config
        # #  形如 [29, 59, 29+237, 59+237, ... ], 默认全历史的输出数据在base_data中的idx，长度为date_num * base_data_time_step_1d
        # self.output_data_time_loc_in_base_data = []
        # for day in range(GlobalConfig.date_num):
        #     self.output_data_time_loc_in_base_data += [x + day * GlobalConfig.base_data_time_step_1d for x in
        #                                                self.output_data_time_loc_list]
        self._default_output_data_shape = (
            GlobalConfig.date_num * self.output_data_time_step_1d, GlobalConfig.code_num)
        self._default_output_data_shape_1d = (GlobalConfig.date_num * self.output_data_time_step_1d,)


# 每个标签的信息
class LabelConfig:
    def __init__(self, label_name, valid_mask_name, output_config):
        self.label_name = label_name
        self.valid_mask_name = valid_mask_name
        self.output_config = output_config
        self.label_output_path = self.output_config.factor_output_path + rf'_{self.label_name}'


# 输出信息按名称保存至output_config_dict
output_config_dict = dict()

# 1小时输出一次
output_name = 'output1h'
# output_data_time_list = [x * 100000 for x in [959, 1029, 1059, 1129, 1329, 1359, 1429]]
# output_data_time_list = [59, 119, 179, 239, 299, 359, 419, 479, 539, 599, 659, 719, 779, 839, 899, 959, 1019, 1079,
#                          1139, 1199, 1259, 1319, 1379, 1439]
output_data_time_list = ['00:59:00', '01:59:00', '02:59:00', '03:59:00', '04:59:00', '05:59:00', '06:59:00', '07:59:00',
                         '08:59:00', '09:59:00',
                         '10:59:00', '11:59:00', '12:59:00', '13:59:00', '14:59:00', '15:59:00', '16:59:00', '17:59:00',
                         '18:59:00', '19:59:00',
                         '20:59:00', '21:59:00', '22:59:00', '23:59:00', ]
output_config_dict[output_name] = OutputConfig(output_name, output_data_time_list)

# label信息和valid_mask信息
label_config_dict = dict()
valid_mask_config_dict = dict()

# 1小时输出一次
label_name = 'avg_1_vwap_mean_ret_1h'
valid_mask_name = 'amt_mean_24h_top60'
output_name = 'output1h'
label_config_dict[label_name] = LabelConfig(label_name, valid_mask_name, output_config_dict[output_name])
valid_mask_config_dict[valid_mask_name] = LabelConfig(label_name, valid_mask_name, output_config_dict[output_name])


def unit_test():
    # 测试DateConfig
    sample_date_list = GlobalConfig.trade_date_list[:5]
    sample_time_step_1d = 237
    # 连续日期
    sample_calc_start = sample_date_list[1]
    sample_calc_end = sample_date_list[-1]
    sample_base = DateConfig2D(sample_time_step_1d, sample_date_list, calc_start=sample_calc_start,
                               calc_end=sample_calc_end, calc_mode='cont', intraday_data_only=False)
    sample_output = DateConfig2D(sample_time_step_1d, sample_date_list, calc_start=sample_calc_start,
                                 calc_end=sample_calc_end, calc_mode='cont', intraday_data_only=False)
    sample_match = DateConfig2DMatch(base_data_date_config=sample_base, output_data_date_config=sample_output)
    temp1, temp2 = sample_match.get_calc_slice(time_step_each_loop=100, time_step_left_for_nan=50)
    print(temp1)
    print(temp2)
    temp1, temp2 = sample_match.get_calc_slice(time_step_each_loop=237, time_step_left_for_nan=237)
    print(temp1)
    print(temp2)
    print(sample_base.output_shape, sample_output.output_shape)
    # 抽样日期
    sample_calc_date = [sample_date_list[x] for x in [1, 4, 2]]
    sample_base = DateConfig2D(sample_time_step_1d, sample_date_list, calc_date_list=sample_calc_date,
                               calc_mode='daily', intraday_data_only=True)
    sample_output = DateConfig2D(sample_time_step_1d, sample_date_list, calc_date_list=sample_calc_date,
                                 calc_mode='daily', intraday_data_only=True)
    sample_match = DateConfig2DMatch(base_data_date_config=sample_base, output_data_date_config=sample_output)
    temp1, temp2 = sample_match.get_calc_slice(time_step_each_loop=237, time_step_left_for_nan=100)
    print(temp1)
    print(temp2)
    temp1, temp2 = sample_match.get_calc_slice(time_step_each_loop=-1, time_step_left_for_nan=300)
    print(temp1)
    print(temp2)
    temp1, temp2 = sample_match.get_calc_slice(time_step_each_loop=-1, time_step_left_for_nan=237)
    print(temp1)
    print(temp2)
    print(sample_base.output_shape, sample_output.output_shape)
    sample_output.get_output_data_time_loc_in_base_data(237, [1, 10])
