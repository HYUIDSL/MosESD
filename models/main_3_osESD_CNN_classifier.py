
import math
from math import e
import numpy as np
import pandas as pd

from .main_osESD_components import osESD
# from osESD_components import SESD_tcha
# from osESD_components import SESD_tres
# from osESD_components import TCHA
# from osESD_components import TRES
from utils.data_config import index_to_preds
# from sklearn.metrics import f1_score, classification_report
from utils.scoring import f1_score
from utils.data_config import anom_replace

class LogisticRegressionSequential:
    def __init__(self):
        self.w = None
        self.b = None

    def sigmoid(self, z):
        return 1 / (1 + np.exp(-z))

    def initialize_parameters(self, dim):
        self.w = np.zeros((dim, 1))
        self.b = 0

    def forward_propagation(self, X):
        z = np.dot(X, self.w) + self.b
        a = self.sigmoid(z)
        return a

    def compute_cost(self, a, y):
        m = len(y)
        cost = (-1/m) * np.sum(y * np.log(a) + (1 - y) * np.log(1 - a))
        return cost

    def backward_propagation(self, X, a, y):
        m = len(y)
        dz = a - y
        dw = (1/m) * np.dot(X.T, dz)
        db = (1/m) * np.sum(dz)
        return dw, db

    def update_parameters(self, lrs, dw, db):

        # print(lrs[0])
        # print(dw)
        # adadasd
        self.w = self.w - lrs[:-1] * dw
        self.b = self.b - lrs[-1] * db
        # self.w = self.w - lrs[0] * dw
        # self.b = self.b - lrs[0] * db

    def train(self, X, y, num_iterations, lrs):
        m, n = X.shape
        # print(m,n)
        self.initialize_parameters(n)
        for i in range(num_iterations):
            # print(self.w)
            # if i==2:
            #     aoisdjasoid
            a = self.forward_propagation(X)
            cost = self.compute_cost(a, y)
            dw, db = self.backward_propagation(X, a, y)
            self.update_parameters(lrs, dw, db)

    def train_incremental(self, X_new, y_new, lrs):
        a = self.forward_propagation(X_new)
        cost = self.compute_cost(a, y_new)
        dw, db = self.backward_propagation(X_new, a, y_new)
        self.update_parameters(lrs, dw, db)

    def predict(self, X):
        a = self.forward_propagation(X)
        # Assuming a threshold of 0.5 for binary classification
        predictions = (a >= 0.5).astype(int)
        return predictions





def anom_replace(orig_data, anom_preds):
    new_df = orig_data.copy()
    for col in new_df.columns:
        col_data = new_df[col]
        for i, pred in enumerate(anom_preds):
            if pred == 1:  # Check if it's an anomaly
                j = i + 1
                while j < len(anom_preds) and anom_preds[j] != 0:
                    j += 1  # Find the next 0
                if i > 0 and j < len(col_data):  # Check boundaries
                    mean_val = (col_data[i - 1] + col_data[j]) / 2
                    col_data = col_data.copy()
                    col_data[i] = mean_val
        new_df[col] = col_data
    return new_df



def multi_back_osESD(x_data, y_data, params,train_percent):

    rwin_size = params.rwin_size
    dwin_size = params.dwin_size
    init_size = params.init_size
    alpha = params.alpha
    maxr = params.maxr
    epochs = params.epochs
    early_stop = params.early_stop
    total_change_rate = params.total_change_rate
    total_o_change_rate =params.total_o_change_rate

    train_size = int(len(x_data) * train_percent)
    cols = [col for col in x_data.columns]

    uni_col_preds = []

    for col in cols:
        col_df = list(x_data[col])
        col_class = osESD(data=col_df, dwins=dwin_size, rwins=rwin_size, init_size=init_size, alpha=alpha, maxr=maxr,
                          condition=True)
        col_class.initiate()
        col_index = col_class.predict_all()
        uni_col_preds.append(index_to_preds(col_index, len(col_df)))

    Col_num = len(cols) * 4
    train_online_len = train_size - init_size
    transformed_data = [[-1 for _ in range(Col_num)] for _ in range(train_online_len)]


    log_lr = [total_change_rate for _ in range(Col_num + 1)]
    log_lr_array = np.array(log_lr).reshape(1, -1)
    log_lr_array_transposed = log_lr_array.T
    lr_sum = sum(log_lr)

    log_online_lr = [total_o_change_rate for _ in range(Col_num + 1)]
    log_online_lr_array = np.array(log_online_lr).reshape(1, -1)
    log_online_lr_array_transposed = log_online_lr_array.T
    online_lr_sum = sum(log_online_lr)

    best_f1 = -1  ### For comparing for early stop
    best_anoms = [0 for _ in range(len(x_data)-train_online_len-init_size)]
    early_stop_count = 0   ### For counting consecutive stops.

    past_i_f1_cols = [-1 for _ in range(len(cols))] ### for saving past epoch f1 scores
    lr_update = [1 for _ in range(len(cols))] ### for setting direction in moving next gradient
    col_idx_list = [i for i in range(len(past_i_f1_cols))]

    k = math.log(2)/train_size ### for decaying lr, making it to 0.5 at the end
    for train_epoch in range(epochs):

        CLASSES = {}
        for col in cols:
            col_df = list(x_data[col])
            col_class = osESD(data=col_df, dwins=dwin_size, rwins=rwin_size, init_size=init_size, alpha=alpha,
                              maxr=maxr, condition=True)
            col_class.initiate()
            CLASSES[col] = col_class
        # print(train_online_len)
        # adadassd
        for i in range(train_online_len):
            for idx, col in enumerate(cols):  # cols
                col_class = CLASSES[col]
                c_val, r_val, c_anom, r_anom = col_class.test_values(i)
                transformed_data[i][idx * 4] = c_val
                transformed_data[i][idx * 4 + 1] = r_val
                transformed_data[i][idx * 4 + 2] = c_anom
                transformed_data[i][idx * 4 + 3] = r_anom
                anom_val = col_class.check_values(c_anom, r_anom)

        train_x = []
        train_y = []

        for idx in range(train_online_len):
            vals = transformed_data[idx]
            if sum(vals) == 0:
                if np.random.uniform(0, 1) > 0.1:
                    continue
            train_x.append(vals)
            train_y.append(y_data[idx + init_size])

        log_model = LogisticRegressionSequential()
        log_model.train(np.array(train_x), np.array(train_y).astype(int).reshape(-1, 1), num_iterations=100,
                        lrs=log_lr_array_transposed)

        anom_idx = []
        anoms = []

        for i in range(train_online_len, len(x_data) - init_size):
            row_vals = []
            real_y = y_data[i + init_size]
            for idx, col in enumerate(cols):  # cols
                col_class = CLASSES[col]
                results = col_class.test_values(i)  # c_val, r_val, c_anom, r_anom
                row_vals.append(results[0])
                row_vals.append(results[1])
                row_vals.append(results[2])
                row_vals.append(results[3])

            row_pred = log_model.predict(row_vals)[0]
            anoms.append(row_pred)
            log_model.train_incremental(np.array([row_vals]), np.array([[real_y]]), lrs=log_online_lr_array_transposed)

            if row_pred == 1:
                anom_idx.append(i + init_size)
                for single_anom_idx, single_anom_val in enumerate(row_vals):
                    if single_anom_val == 1:
                        col_idx = single_anom_idx // 4
                        col_class = CLASSES[cols[col_idx]]
                        if single_anom_idx % 2 == 0:
                            anom_val = col_class.check_values(row_vals[single_anom_idx], row_vals[single_anom_idx + 1])
                        else:
                            anom_val = col_class.check_values(row_vals[single_anom_idx - 1], row_vals[single_anom_idx])

        check = pd.DataFrame({'y': y_data[train_size:len(y_data)], 'preds': anoms})

        recent_f1 = f1_score(check['y'], check['preds'])
        print(log_lr_array)
        print("New F1 : {:.4f}, Best F1 : {:.4f}".format(recent_f1,best_f1))
        if best_f1>recent_f1:  ### Case where next epoch yielded worse results than final epoch.
            early_stop_count +=1
            if early_stop_count==early_stop:
                print("Ended early with only {} epochs".format(train_epoch))
                return best_anoms
        else: ### New epoch is best.
            early_stop_count = 0
            best_f1 = recent_f1
            best_anoms = anoms

        ### End of training
        if train_epoch==epochs-1:
            return best_anoms



        ### 여기 아래 부분을 따로 function으로 만들든지 하는게 더 깔끔할듯?

        ### Strategy 1 : 역수.  폐기

        ### Strategy 2 : 1-f1_score 만큼 일단 추가하는데, 전보다 낮아지면 오히려 마이너스로.
        ### 그리고 이게 첫 f1_score은 -1이기 때문에 무조건 플러스 함.

        ### 지금 이게 1-X 로 하니까 다 너무 비슷비슷하다.

        i_col_f1s = []
        for idx, col in enumerate(cols):
            uni_preds = uni_col_preds[idx][train_online_len + init_size:]
            i_col_f1s.append(1-f1_score(uni_preds,anoms))
            # i_col_f1s.append(1 / f1_score(uni_preds, anoms))
        i_f1_sum = sum(i_col_f1s)

        for idx, past, now in zip(col_idx_list, past_i_f1_cols, i_col_f1s):
            if now<past:
                lr_update[idx]*=(-1)

        past_i_f1_cols = i_col_f1s
        i_f1_sum = sum(i_col_f1s)
        d_lr = [total_change_rate * i / i_f1_sum for i in i_col_f1s]
        d_o_lr = [total_o_change_rate * i / i_f1_sum for i in i_col_f1s]
        # print(d_lr)
        for col_idx in range(len(cols)):
            for times in range(4):
                log_lr[col_idx * 4 + times] += d_lr[col_idx] * lr_update[col_idx]
                log_online_lr[col_idx * 4 + times] += d_o_lr[col_idx] * lr_update[col_idx]

        new_sum = sum(log_lr)
        log_lr = [i*lr_sum/new_sum for i in log_lr]
        new_o_sum = sum(log_online_lr)
        log_online_lr = [i*lr_sum/new_o_sum for i in log_online_lr]

        log_lr_array = np.array(log_lr).reshape(1, -1)
        log_lr_array_transposed = log_lr_array.T
        log_online_lr_array = np.array(log_online_lr).reshape(1, -1)
        log_online_lr_array_transposed = log_online_lr_array.T

        total_o_change_rate *= e**(-k*i)

        continue
        '''
        Need to add replace mechanism and CNN classifier.
        '''





        ### 현재는 1-f1 +- gradient 방식으로 진행을 함.
        # ### 아래는 strategy 1 역수 방식.

        # i_col_f1s = []
        # for idx, col in enumerate(cols):
        #     uni_preds = uni_col_preds[idx][train_online_len + init_size:]
        #     i_col_f1s.append(1 / f1_score(uni_preds, anoms))
        #
        # i_f1_sum = sum(i_col_f1s)
        #
        # d_lr = [total_change_rate * i / i_f1_sum for i in i_col_f1s]
        # d_sum = sum(d_lr)
        # d_lr = [i * lr_sum / d_sum for i in d_lr]
        #
        # d_o_lr = [total_o_change_rate * i / i_f1_sum for i in i_col_f1s]
        # d_o_sum = sum(d_o_lr)
        # d_o_lr = [i * online_lr_sum / d_o_sum for i in d_o_lr]
        #
        #
        # for col_idx in range(len(cols)):
        #     for times in range(4):
        #         log_lr[col_idx * 4 + times] += d_lr[col_idx]
        #         log_online_lr[col_idx * 4 + times] += d_o_lr[col_idx]
        #
        # new_sum = sum(log_lr)
        # print(new_sum)
        #
        #
        #
        # log_lr = [i*lr_sum/new_sum for i in log_lr]
        # new_o_sum = sum(log_online_lr)
        # log_online_lr = [i*lr_sum/new_o_sum for i in log_online_lr]
        #
        # log_lr_array = np.array(log_lr).reshape(1, -1)
        # log_lr_array_transposed = log_lr_array.T
        # log_online_lr_array = np.array(log_online_lr).reshape(1, -1)
        # log_online_lr_array_transposed = log_online_lr_array.T
        #
        # total_o_change_rate *= e**(-k*i)