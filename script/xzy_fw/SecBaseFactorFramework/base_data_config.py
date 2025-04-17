import os
import numpy as np
import torch
import time
from tqdm import tqdm
from .global_config import GlobalConfig, label_config_dict, valid_mask_config_dict, label_data_path

try:
    # 基础字段
    Base_data_dict = dict()
    Base_data_path = rf'{GlobalConfig.base_data_root_path}/Base'
    for file_name in os.listdir(Base_data_path):
        base_data_name = file_name.split('.')[0]
        Base_data_dict[base_data_name] = np.memmap(rf'{Base_data_path}/{file_name}',
                                                   dtype='float32', mode='r', shape=GlobalConfig.base_data_shape)

    base_data_name_list = list(Base_data_dict.keys())
    base_data_name_list.sort()

    # label
    for file_name in os.listdir(label_data_path):
        support_data_name = file_name.split('.')[0]
        if 'valid_mask' in support_data_name:
            # valid_mask储存时的类型是bool
            Base_data_dict[support_data_name] = torch.load(rf'{label_data_path}/{file_name}', mmap=True,
                                                           map_location='cpu').to(torch.bool)
        else:
            Base_data_dict[support_data_name] = torch.load(rf'{label_data_path}/{file_name}', mmap=True,
                                                           map_location='cpu').to(torch.float32)

except Exception as e:
    print('base_data_config error', e)
