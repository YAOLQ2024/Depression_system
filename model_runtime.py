"""Shared packet-to-model adapter; preserve independent M1 calibration."""
from pathlib import Path
import joblib
import numpy as np
from dataset_converter import PACKET_FEAT_NAMES

MUSER_VERSION='muser5s_m1_holdout_v1'

def normalize_bundle(bundle):
    if not isinstance(bundle,dict):raise ValueError('模型必须是包含model/scaler的字典')
    b=dict(bundle)
    if b.get('version')==MUSER_VERSION:
        names=list(b.get('window_feature_names',b['feature_names']))
        if len(names)!=52:raise ValueError('Muser模型必须提供52维窗口特征顺序')
        trial=[f'{part}_{n}' for part in ('med','std','slope') for n in names]
        b.update(classifier_name='SVM_Muser64_5s_M1',input_kind='vector',norm_mode='independent_calibration',
            runtime_feature_source='packet',packet_feature_names=names,window_feature_names=names,
            trial_feature_names=trial,all_feature_names=trial,feature_names=trial,selected_features=list(range(156)),
            trial_feature_components=['med','std','slope'],runtime_window_frames=4,runtime_calibration_frames=87,
            feature_set_desc='T7/T8/Fpz 52维，独立M1校准，4帧聚合156维')
    return b

def load_model_bundle(path):
    # joblib also reads legacy plain pickle; export uses plain pickle for portability.
    return normalize_bundle(joblib.load(Path(path)))

class ModelRuntime:
    def __init__(self,bundle):
        self.bundle=normalize_bundle(bundle)
        self.requires_calibration=self.bundle.get('norm_mode')=='independent_calibration'
        self.window_names=list(self.bundle.get('window_feature_names') or self.bundle.get('packet_feature_names') or PACKET_FEAT_NAMES)
        if self.window_names!=list(PACKET_FEAT_NAMES):raise ValueError('模型窗口特征顺序与当前52维特征包不一致')
        names=list(self.bundle.get('trial_feature_names') or self.bundle.get('all_feature_names') or self.window_names)
        self.components=tuple(self.bundle.get('trial_feature_components') or (['med'] if len(names)==len(self.window_names) else ['med','std','slope']))
        self.selected=np.asarray(self.bundle.get('selected_features',np.arange(len(names))),dtype=int)
        self.trial_names=names
        if len(names)!=len(self.window_names)*len(self.components):raise ValueError('聚合特征数量不匹配')
        if not len(self.selected) or np.any(self.selected<0) or np.any(self.selected>=len(names)):raise ValueError('模型特征索引无效')
        expected=len(self.selected)
        if int(self.bundle['scaler'].n_features_in_)!=expected or int(self.bundle['model'].n_features_in_)!=expected:raise ValueError('分类器、标准化器和特征维度不一致')
        self.required_frames=self.bundle.get('runtime_window_frames') if self.requires_calibration else None
        self.calibration_target=int(self.bundle.get('runtime_calibration_frames',87))
        self.reset_calibration()

    @property
    def calibrated(self):return not self.requires_calibration or self.mean is not None

    def reset_calibration(self):
        self.calibration_rows=[];self.mean=None;self.std=None

    def set_calibration(self,rows):
        x=np.asarray(rows,dtype=float)
        if x.ndim!=2 or x.shape[1]!=52 or len(x)<2 or not np.isfinite(x).all():raise ValueError('校准必须是至少2行、每行52维的有限特征')
        self.mean=x.mean(0);self.std=np.maximum(x.std(0,ddof=int(self.bundle.get('calibration_std_ddof',1))),float(self.bundle.get('calibration_std_floor',1e-8)))
        self.calibration_rows=x.copy().tolist()

    def load_calibration(self,path):
        with np.load(Path(path)) as z:
            if 'calibration' not in z:raise ValueError('校准NPZ必须包含calibration数组，不能使用待分类窗口自动代替')
            self.set_calibration(z['calibration'])

    def add_calibration(self,row):
        if self.calibrated:return True
        x=np.asarray(row,dtype=float)
        if x.shape!=(52,) or not np.isfinite(x).all():raise ValueError('校准帧必须为52维有限特征')
        self.calibration_rows.append(x.copy().tolist())
        if len(self.calibration_rows)>=self.calibration_target:self.set_calibration(self.calibration_rows)
        return self.calibrated

    def prepare(self,rows):
        x=np.asarray(rows,dtype=float)
        if x.ndim!=2 or x.shape[1]!=52 or not np.isfinite(x).all():raise ValueError('输入必须为N×52维有限特征')
        if self.required_frames and len(x)!=self.required_frames:raise ValueError(f'此模型每次必须使用{self.required_frames}帧，对应训练的5秒片段')
        if not self.calibrated:raise ValueError('请先完成独立校准，再开始分类')
        if self.requires_calibration:x=(x-self.mean)/self.std
        elif self.bundle.get('norm_mode','none')=='session_zscore':
            sd=x.std(0);sd[sd<1e-12]=1;x=(x-x.mean(0))/sd
        t=np.arange(len(x),dtype=float);t-=t.mean();slope=np.zeros(52) if len(x)<2 else np.mean(x*(t/t.std())[:,None],0)
        parts={'med':np.median(x,0),'std':x.std(0),'slope':slope}
        if any(c not in parts for c in self.components):raise ValueError('未知聚合分量')
        full=np.concatenate([parts[c] for c in self.components]);scaled=self.bundle['scaler'].transform(full[self.selected].reshape(1,-1))
        return full,scaled
