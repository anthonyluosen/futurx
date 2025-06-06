import os

base_dir = os.path.dirname(os.path.dirname(__file__))
base_dir = os.path.join(os.path.dirname(base_dir),"data")

position_path = os.path.join(base_dir,'positions')
os.makedirs(position_path,exist_ok = True)


api_key = "MTRrwMPMBIrFJ0Pqgo02MlapNwIXM5PuKHXwsy0ZAd76TXvYdc6AdGKNgTy1UEpA"
secret_key = "jg99TGTGKsE2lvH8m2xnSmNuC0mL2b6RjmeMTFj0GxPVM6sDWK9lgWyG275XqN6m"

min_notional = 2.0 # 最小名义价值


########################################################
# xzy
# 字段频率
base_itvl = "15min"
# 框架总目录
facfmk_root_path = rf'{base_dir}/facfmk/{base_itvl}'
static_config_data_path = rf'{base_dir}/facfmk/support_data'
config_data_path = rf'{facfmk_root_path}/support_data'
base_data_fea_root_path = rf'{facfmk_root_path}/BaseData/Feather'
base_data_mmap_root_path = rf'{facfmk_root_path}/BaseData/Mmap'
os.makedirs(static_config_data_path, exist_ok=True)
os.makedirs(config_data_path, exist_ok=True)
os.makedirs(base_data_fea_root_path, exist_ok=True)
os.makedirs(base_data_mmap_root_path, exist_ok=True)

fmk_start_date = '2022-01-01'
fmk_end_date = '2026-12-31'
########################################################