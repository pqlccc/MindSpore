import pandas as pd


DATA_PATH = './data/'

df_daily = pd.read_csv(DATA_PATH + 'daily_dataset.csv')
df_min = pd.read_csv(DATA_PATH + 'per5min_dataset.csv')
df_hour = pd.read_csv(DATA_PATH + 'hourly_dataset.csv')
df_test = pd.read_csv(DATA_PATH + 'test_public.csv')
df_sub = pd.read_csv(DATA_PATH + 'sample_submission.csv')
df_weather = pd.read_csv(DATA_PATH + 'weather.csv')
df_epidemic = pd.read_csv(DATA_PATH + 'epidemic.csv')
print(df_hour)
print(df_hour.tail())
print(df_hour.describe())

import matplotlib.pyplot as plt

# #画图显示,初步查看异常值
figure=plt.figure(figsize=(16, 16))
ax1=plt.subplot(221)
plt.plot(df_hour['flow_1'])
ax2=plt.subplot(222)
plt.plot(df_hour['flow_2'])
ax3=plt.subplot(223)
plt.plot(df_hour['flow_3'])
ax4=plt.subplot(224)
plt.plot(df_hour['flow_4'])
plt.show()


# 每个测试集都有168行
SEQ_LEN = 168

# #根据test分组，从datafram数据里面取出第一个和最后一个值，记得重置索引，然后再转变为list
test_list1 = df_test.groupby('train or test')['time'].first().reset_index()
test_list1 = test_list1['time'].values.tolist()
test_list2 = df_test.groupby('train or test')['time'].last().reset_index()
test_list2 = test_list2['time'].values.tolist()
test_list1.extend(test_list2)
test_list1.sort()
# print(test_list1)

COLUMNS_Y = ['flow_{}'.format(i) for i in range(1, 21)]
COLUMNS_X = COLUMNS_Y + ['day', 'hour', 'dayofweek']

def add_time_feat(data):
    data['time'] = pd.to_datetime(data['time'])
    data['day'] = data['time'].dt.day
    data['hour'] = data['time'].dt.hour
    data['minute'] = data['time'].dt.minute
    data['dayofweek'] = data['time'].dt.dayofweek
    return data.sort_values('time').reset_index(drop=True)


def add_other_feat(data, columns):
    data['flow_sum'] = data[columns].sum()
    data['flow_median'] = data[columns].median()
    data['flow_mean'] = data[columns].mean()
    return data


df_hour = add_time_feat(df_hour)


import numpy as np
class Trans:
    def __init__(self, data, name):
        self.min = max(0, np.percentile(data, 1))
        self.max = np.percentile(data, 99)
        self.base = self.max - self.min

    def transform(self, data, scale=True):
        _data = np.clip(data, self.min, self.max)
        if not scale:
            return _data
        return (_data - self.min) / self.base


class TransUtil:
    def __init__(self, data, exclude_cols=None):
        self.columns = data.columns
        self.exclude_cols = exclude_cols
        self.trans = {}
        for c in self.columns:
            if data[c].dtype not in [int, float]:
                print('column "{}" not init trans...'.format(c))
                continue

            if exclude_cols is None or (exclude_cols is not None and c not in exclude_cols):
                print('init trans column...', c)
                self.trans[c] = Trans(data[c].fillna(method='bfill').fillna(method='ffill'), c)

    def transform(self, data, col_name, scale=True):
        if self.exclude_cols is not None and col_name in self.exclude_cols:
            return data

        for t in self.trans:
            if t.startswith(col_name):
                return self.trans[t].transform(data, scale=scale)

        return data


trans_util = TransUtil(df_hour, exclude_cols=None)  # 数据标准化


def generate_xy_pair(data, seq_len, trans_util, columns_x, columns_y):
    data_x = pd.DataFrame()
    for c in columns_x:
        data_x[c] = trans_util.transform(data[c].fillna(data[c].median()), c)

    data_y = pd.DataFrame()
    for c in columns_y:
        data_y[c] = trans_util.transform(data[c].fillna(data[c].median()), c, scale=False)

    data_x = data_x.values
    data_y = data_y.values

    print(data_x.shape, data_y.shape)

    d_x = []
    d_y = []
    for i in range(len(data_x) - seq_len * 2 + 1):
        _x = data_x[i:i + seq_len]
        _y = data_y[i + seq_len:i + seq_len + seq_len]

        assert len(_x) == len(_y) == seq_len, (_x, _y, _x.shape, _y.shape, i, len(data_x))

        d_x.append(_x.T)
        d_y.append(_y.T)

    return np.asarray(d_x).transpose((0, 2, 1)), np.asarray(d_y).transpose((0, 2, 1))

data_x, data_y = generate_xy_pair(df_hour, seq_len=SEQ_LEN, trans_util=trans_util, columns_x=COLUMNS_X, columns_y=COLUMNS_Y)

data_x.shape, data_y.shape


# 根据每段测试集将对应的训练数据/测试数据的idx提取出来
_train_idx_1 = df_hour[df_hour['time']<test_list1[0]].index.values.tolist()
_train_idx_2 = df_hour[(df_hour['time']>test_list1[1])&(df_hour['time']<test_list1[2])].index.values.tolist()
_train_idx_3 = df_hour[(df_hour['time']>test_list1[3])&(df_hour['time']<test_list1[4])].index.values.tolist()
_train_idx_4 = df_hour[(df_hour['time']>test_list1[5])&(df_hour['time']<test_list1[6])].index.values.tolist()

# 每一段数据包括上一段时间
train_idx_1 = _train_idx_1[:-SEQ_LEN*2]
train_idx_2 = train_idx_1 + _train_idx_2[:-SEQ_LEN*2]
train_idx_3 = train_idx_2 + _train_idx_3[:-SEQ_LEN*2]
train_idx_4 = train_idx_3 + _train_idx_4[:-SEQ_LEN*2]

test_idx_1 = _train_idx_1[-SEQ_LEN]
test_idx_2 = _train_idx_2[-SEQ_LEN]
test_idx_3 = _train_idx_3[-SEQ_LEN]
test_idx_4 = _train_idx_4[-SEQ_LEN]

len(_train_idx_1), len(_train_idx_2), len(_train_idx_3), len(_train_idx_4)

len(train_idx_1), len(train_idx_2), len(train_idx_3), len(train_idx_4)

test_idx_1, test_idx_2, test_idx_3, test_idx_4

train_x_1 = data_x[train_idx_1]
train_y_1 = data_y[train_idx_1]
train_x_2 = data_x[train_idx_2]
train_y_2 = data_y[train_idx_2]
train_x_3 = data_x[train_idx_3]
train_y_3 = data_y[train_idx_3]
train_x_4 = data_x[train_idx_4]
train_y_4 = data_y[train_idx_4]

test_x_1 = data_x[test_idx_1]
test_x_2 = data_x[test_idx_2]
test_x_3 = data_x[test_idx_3]
test_x_4 = data_x[test_idx_4]

FEATURE_SIZE = train_x_1.shape[-1]
OUTPUT_SIZE = train_y_1.shape[-1]

train_x_1.shape, train_y_1.shape, test_x_1.shape

import mindspore
import mindspore.nn as nn
import os
# import mindspore.nn.functional as F


class Tt():
    def __init__(self,
                 seq_len,
                 feature_size,
                 output_size,
                 use_model='gru',
                 hidden_size=576,
                 hidden_sizes=[576],
                 max_position_embeddings=512,
                 max_hour=25,
                 max_min=61,
                 max_dow=8,
                 max_ts=1441):
        super(Tt, self).__init__()

        self.use_model = use_model
        self.feature_size = feature_size

        # 如果有相应的时间embedding则可以使用
        self.th_embeddings = nn.Embedding(max_hour, hidden_size)
        self.tm_embeddings = nn.Embedding(max_min, hidden_size)
        self.td_embeddings = nn.Embedding(max_dow, hidden_size)
        self.tt_embeddings = nn.Embedding(max_ts, hidden_size)

        # 位置编码
        self.position_embeddings = nn.Embedding(max_position_embeddings, hidden_size)
        self.layer_norm = nn.LayerNorm(hidden_sizes)
        self.fc_inputs = nn.Dense(feature_size, hidden_size)

        self.lstm = mindspore.nn.LSTM(input_size=hidden_size, hidden_size=hidden_size, num_layers=2)
        self.gru = mindspore.nn.GRU(input_size=hidden_size, hidden_size=hidden_size, num_layers=2)

        self.fc_output_1 = nn.Dense(hidden_size, hidden_size)
        self.fc_output_2 = nn.Dense(hidden_size, hidden_size)
        self.fc_output_3 = nn.Dense(hidden_size, output_size)

    def forward(self,
                inputs,
                inputs_th=None,
                inputs_tm=None,
                inputs_td=None,
                inputs_tt=None,
                position_ids=None,
                attention_mask=None):

        if position_ids is None:
            ones = mindspore.ones(inputs.shape[:2], dtype="int64")
            seq_length = mindspore.cumsum(ones, axis=1)
            position_ids = seq_length - ones
            position_ids.stop_gradient = True

        position_embeddings = self.position_embeddings(position_ids)

        inputs = self.fc_inputs(inputs)
        inputs = nn.Tanh()(inputs)

        inputs = inputs + position_embeddings

        # 如果有相应的时间embedding则可以使用
        if inputs_th is not None:
            inputs += self.th_embeddings(inputs_th)

        if inputs_tm is not None:
            inputs += self.tm_embeddings(inputs_tm)

        if inputs_td is not None:
            inputs += self.td_embeddings(inputs_td)

        if inputs_tt is not None:
            inputs += self.tt_embeddings(inputs_tt)

        inputs = self.layer_norm(inputs)

        # 选择使用LSTM或者gru
        if self.use_model == 'lstm':
            encoder_outputs, (h, c) = self.lstm(inputs)
        elif self.use_model == 'gru':
            encoder_outputs, h = self.gru(inputs)

        output = self.fc_output_1(encoder_outputs)
        output = nn.ReLU()(output)
        output = self.fc_output_2(output)
        output = self.fc_output_3(output)

        return output

# model = Tt(seq_len=SEQ_LEN, feature_size=FEATURE_SIZE, output_size=OUTPUT_SIZE)
# print(model)

from sklearn.metrics import mean_squared_log_error as msle


def calc_score(y_true, y_pred):
    return 1 / (1 + msle(np.clip(np.reshape(y_true, -1), 0, None), np.clip(np.reshape(y_pred, -1), 0, None)))


def eval_model(model, data_loader):
    model.eval()

    y_pred = []
    y_true = []
    for step, batch in enumerate(data_loader, start=1):
        data = batch['data'].astype('float32')
        label = batch['label'].astype('float32')

        # 计算模型输出
        output = model(inputs=data)
        y_pred.extend(output.numpy())
        y_true.extend(label.numpy())

    score = calc_score(y_true, y_pred)
    model.train()
    return score


def make_data_loader(data_x, idx, batch_size, data_y=None, shuffle=False):
    data = [{
        'data': data_x[i],
        'label': 0 if data_y is None else data_y[i]}
        for i in idx]
    ds = data
    batch_sampler = ds
    return ds, batch_sampler


import time
from sklearn.model_selection import KFold

EPOCHS = 30
BATCH_SIZE = 256
CKPT_DIR = 'work/output'
K_FOLD = 5
epoch_base = 0
step_eval = 5
step_log = 100


def do_train(train_x, train_y, prefix):
    print('-' * 20)
    print('training ...', prefix)
    print('train x:', np.shape(train_x), 'train y:', np.shape(train_y))

    mindspore.set_seed(2022)

    for kfold, tv_idx in enumerate(KFold(n_splits=K_FOLD, shuffle=True, random_state=2022).split(train_x)):
        print('training fold...', kfold)

        train_idx, valid_idx = tv_idx

        model = Tt(seq_len=SEQ_LEN, feature_size=FEATURE_SIZE, output_size=OUTPUT_SIZE)

        train_data_loader = make_data_loader(
            train_x, train_idx, BATCH_SIZE, data_y=train_y, shuffle=True)
        valid_data_loader = make_data_loader(
            train_x, valid_idx, BATCH_SIZE, data_y=train_y, shuffle=False)

        # optimizer = nn.AdamWeightDecay(parameters=model.trainable_params())
        criterion = mindspore.nn.MSELoss()

        epochs = EPOCHS  # 训练轮次
        save_dir = CKPT_DIR  # 训练过程中保存模型参数的文件夹
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        global_step = 0  # 迭代次数
        tic_train = time.time()

        # model.train(100, train_data_loader)

        best_score = 0
        for epoch in range(1 + epoch_base, epochs + epoch_base + 1):
            for step, batch in enumerate(train_data_loader, start=1):
                data = batch[0]
                label = batch[1]

                # 计算模型输出
                output = model(inputs=data)
                loss = criterion(output, label)
                # print(loss)

                # 打印损失函数值、准确率、计算速度
                global_step += 1
                if global_step % step_eval == 0:
                    score = eval_model(model, valid_data_loader)
                    if score > best_score:
                        # print('saving best model...', score)
                        _save_dir = os.path.join(save_dir, '{}_kfold_{}_best_model.pdparams'.format(prefix, kfold))
                        mindspore.save(
                            model.state_dict(),
                            _save_dir)
                        best_score = score
                    if global_step % step_log == 0:
                        print(
                            'global step %d, epoch: %d, batch: %d, loss: %.5f, valid score: %.5f, speed: %.2f step/s'
                            % (global_step, epoch, step, loss, score,
                               10 / (time.time() - tic_train)))
                        tic_train = time.time()

                # 反向梯度回传，更新参数
                loss.backward()
                nn.Optimizer.step()
                nn.Optimizer.clear_grad()


def do_pred(test_x, prefix):
    print('-' * 20)
    print('predict ...', prefix)
    print('predict x:', np.shape(test_x))

    # 预测
    test_data_loader = make_data_loader(
        [test_x], [0], BATCH_SIZE, data_y=None, shuffle=False)

    sub_df = []
    save_dir = CKPT_DIR

    for kfold in range(K_FOLD):
        print('predict kfold...', kfold)
        model = Tt(seq_len=SEQ_LEN, feature_size=FEATURE_SIZE, output_size=OUTPUT_SIZE)
        model.set_dict(mindspore.load(os.path.join(save_dir, '{}_kfold_{}_best_model.pdparams'.format(prefix, kfold))))
        model.eval()

        y_pred = []
        for step, batch in enumerate(test_data_loader, start=1):
            data = batch['data'].astype('float32')
            label = batch['label'].astype('float32')

            # 计算模型输出
            output = model(inputs=data)
            y_pred.extend(output.numpy())

        sub_df.append(np.clip(y_pred, 0, None))

    return sub_df


# 依次训练每个测试集对应的模型
do_train(train_x_1, train_y_1, 'm1')
do_train(train_x_2, train_y_2, 'm2')
do_train(train_x_3, train_y_3, 'm3')
do_train(train_x_4, train_y_4, 'm4')

# 以此预测数据
pred_1 = do_pred(test_x_1, 'm1')
pred_2 = do_pred(test_x_2, 'm2')
pred_3 = do_pred(test_x_3, 'm3')
pred_4 = do_pred(test_x_4, 'm4')

