# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 12:16:05 2019

@author: nao
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import random
import math
import copy
import pandas as pd
from scipy.stats import entropy


######################constant values######################################################
CONDITION = 1
D_MAX_ARR = np.array([4])#MaxDepth of MetaTree
B_ARR = np.array([5])
#D_MAX_TRUE = 4#MaxDepth of true model
K = 22
N_ALL = 8000
N = 1000
TEST_EPOCH = 1#テストデータの繰り返し回数
THETA = 1#学習データの繰り返し回数
M =  1#the number of generating true model
TEST = 1000
BRANCH_NUM = 12
Y_VALUE = 2
BETA = np.ones(Y_VALUE) / Y_VALUE
N_WIDTH = 100
DATA_DIVISION_RATE = 0.05
RF_FEAT_NUM = math.ceil(math.sqrt(K))
######################tree structure######################################################
class Node:
    def __init__(self, depth):
        self.childs = [None for i in range(BRANCH_NUM)]
        self.depth = depth
        self.feat = -1
        self.division_index_list = []
        self.g = 1/2#division probability on each branch
        self.n = np.zeros(Y_VALUE)   
        self.P = 1 / 2#probability of y=0
        self.q = 1 / 2
        self.theta = np.ones(Y_VALUE) / Y_VALUE
        self.division = 0  #0:division 1:no division
        self.y_num = [0 for i in range(Y_VALUE)]
        self.pred_y = -1
    ######################entropy, division index################################################
    def entropy( y ):
        y_num = np.zeros(Y_VALUE)
        y_rate = np.zeros(Y_VALUE)
        size = len(y)
        ent = 0
        for y_value in range(Y_VALUE):        
            for j in range(size):
                if y[j] == y_value:
                    y_num[y_value] += 1
    
        for y_value in range(Y_VALUE):
            if y_num[y_value] != 0 and y_num[y_value] != size:#0log0,1log1=0
                y_rate[y_value] = y_num[y_value] / size        
                ent += -y_rate[y_value] * np.log2(y_rate[y_value])
            print(y_rate)
        return ent

    def division_index_cal(self, data, flist):#data is the tuple of xy
        self.division_index_list = [0 for i in range(len(flist))]
        for i in range(len(flist)):
            for branch in range(BRANCH_NUM):
                data_selected = np.delete(data.copy(), np.where(data[flist[i]][:] != branch), axis=1)#delete the row except for x_i=branch
                if data_selected.shape[1] == 0:#if no data
                    self.division_index_list[i] += np.log2(data.shape[1])
                else:
                    self.division_index_list[i] += data_selected.shape[1] * entropy([np.count_nonzero(data_selected[-1][:] == y_value) /data.shape[1]  for y_value in range(Y_VALUE)], base=2) / data.shape[1]
        if len(flist) != 0:
            self.feat = flist[np.argmin(self.division_index_list)]
                           
    ######################generate true tree for classification##########
    def make_RF(self,depth, flist, condition, data, n):#特徴量ランダムに選択
#        print('data= %s' % data)
#        print('n= %s' % n)
#        print('len(data[0,:])= %s' % len(data[0,:]))
        for y_value in range(Y_VALUE):
            self.y_num[y_value] += np.count_nonzero(data[-1,:] == y_value)
        if len(data[0,:]) < n * DATA_DIVISION_RATE:
            self.division = 1#分割終了
        else:                           
            if depth < D_MAX_ARR[condition]:
                self.division_index_cal(data, flist)
                flist_copied = flist.copy()
                if self.feat in flist_copied == True:
                    flist_copied.remove(self.feat)
            else:
                self.division = 1#分割終了                    
        if self.division == 0:
            for branch in range(BRANCH_NUM):                
                self.childs[branch] = Node(depth+1)
                self.childs[branch].make_RF(depth+1, flist_copied, condition, np.delete(data, np.where(data[self.feat] != branch)[0], axis=1), n)
        else:
            self.division = 1#分割終了                                
        if self.division == 1:
            self.pred_y = np.argmax(self.y_num)

    def make_tree_shape_only(self, condition):#特徴量ランダムに選択
#        print('depth= %s' % depth)
#        print('flist= %s' % flist)
#        featureの割り振りを入れ込む
        if self.depth < D_MAX_ARR[condition]:
            for branch in range(BRANCH_NUM):
                self.childs[branch] = Node(self.depth+1)
                self.childs[branch].make_tree_shape_only(condition)



    ######################with renewal of poseterior distribution###############################################
    def q_cal(self, y_value):
        return (self.n[y_value] + BETA[y_value]) / (self.n.sum() + np.sum(BETA))    

    def n_add(self, data):
        self.n[data[-1]] += 1
    
    def g_cal(self,data, condition):
        if self.division == 0:
            self.g *= self.childs[data[self.feat]].P / self.P

    def P_cal_with_update(self, data, condition):
        if self.division == 1:
            self.P = self.q_cal(data[-1])
        else:
            self.P = (1 - self.g) * self.q_cal(data[-1]) + self.g * self.childs[data[self.feat]].P_cal_with_update(data, condition)
        self.g_cal(data, condition)
        self.n_add(data)    
        return self.P

    ######################only classification######################################################
    def P_cal(self,data_x, condition, y_value):
        if self.division == 1:
            tmp_P = self.q_cal(y_value)
        else:
            tmp_P = (1 - self.g) * self.q_cal(y_value) + self.g * self.childs[data_x[self.feat]].P_cal(data_x, condition, y_value)
        return tmp_P
    ###################insert data and classification###############################################################
    def classify(self, new_data):
#        print(self.feat)
        if self.division == 1:
            y = self.pred_y
        else:
            y = self.childs[new_data[self.feat]].classify(new_data)
        return y

    ##############copy parameters on the tree############################################
    def feature_trees_copy_RF(self, node, condition, flist):#node:FT, node2:RF
#        print(type(self))
#        print(type(self.childs[0]))
        if node is None:#RFのノードがないとき
            self.division = 1
        elif node.division == 1:#RFにおける葉ノードであるとき
            self.division = 1
        else:#分割する
            self.feat = node.feat#int,floatなどの値の場合.copy不要
            flist_copied = flist.copy()
            if self.feat in flist_copied == True:
                flist_copied.remove(self.feat)
            if self.depth < D_MAX_ARR[condition]:
                for branch in range(BRANCH_NUM):
                    self.childs[branch].feature_trees_copy_RF(node.childs[branch], condition, flist_copied)


######################generate data######################################################
def y_decide(node, data):
    if node.division== 1:
        theta = node.theta
    elif node.division != 1:
        theta = y_decide(node.childs[data[node.feat]], data)
    return theta


######################Random Forest######################################################
class RF_trees:
    def __init__(self, condition, train_data, n):
        self.root_list = [None for i in range(B_ARR[condition])]
        for i in range(B_ARR[condition]):
            boot_num = np.random.randint(0, n, (n))
            bootstrap_sample = np.zeros((K+1,n), dtype='int')
#            print('bootstrap_sample= %s' % bootstrap_sample)           
#            print('boot_num= %s' % boot_num)  
#            print('train_data= %s' % train_data)  
            for bootstrap_sample_num in range(n):
                bootstrap_sample[:,bootstrap_sample_num] = train_data[:,boot_num[bootstrap_sample_num]]
            RF_flist = random.sample([i for i in range(K)], RF_FEAT_NUM)
            self.root_list[i] = Node(0)
            self.root_list[i].make_RF(0, RF_flist, condition, bootstrap_sample, n)
######################Feature Trees######################################################
class Feature_trees:
    def __init__(self, condition, train_data):
        self.root_list = [None for i in range(B_ARR[condition])]
        for i in range(B_ARR[condition]):
            self.root_list[i] = Node(0)
            self.root_list[i].make_tree_shape_only(condition)
        self.posterior = np.ones(B_ARR[condition]) / B_ARR[condition]

    ######################renew poseterior disribution######################################################
    def posterior_cal(self,data, condition):
        for i in range(B_ARR[condition]):
            self.root_list[i].P_cal_with_update(data, condition)
            self.posterior[i] *= self.root_list[i].P
        self.posterior /= self.posterior.sum()
    
    ######################classification######################################################
    def prediction(self,data, condition):
        tmp = np.zeros(Y_VALUE)
        for y_value in range(Y_VALUE):
            for i in range(B_ARR[condition]):
                tmp[y_value] += self.posterior[i] * self.root_list[i].P_cal(data, condition, y_value)

        return np.argmax(tmp)



######################main######################################################
correct_RF = np.zeros((CONDITION, int(N/N_WIDTH)), dtype = 'int')
incorrect_RF = np.zeros((CONDITION, int(N/N_WIDTH)), dtype = 'int')
correct = np.zeros((CONDITION, int(N/N_WIDTH)), dtype = 'int')
incorrect = np.zeros((CONDITION, int(N/N_WIDTH)), dtype = 'int')
rf_trees = [[None for i in range(int(N/N_WIDTH))] for i in range(CONDITION)]

for m in range(M):
#    print('m= %s' % m)
    df =pd.read_csv("mushroom_random.csv")
    for test in range(TEST_EPOCH):
        print('test= %s' % test)
        test_data = np.array(df.iloc[:, [random.randint(0,N_ALL) for i in range(TEST)]])
        for theta in range(THETA):
            train_data = np.array(df.iloc[:, [random.randint(0,N_ALL) for i in range(N)]])#エラー出るため10個ずつ余裕をもってとっておく    
            feature_trees = Feature_trees(-1, train_data) #condition=-1
            #generate tree for Random Forest
            for condition in range(CONDITION):
                for n in range(N_WIDTH, N + 1, N_WIDTH):#10,20,30,...
                    train_data_sub = train_data[:,:n+1].copy()
    #                print(train_data_sub)
                    rf_trees[condition][int(n/N_WIDTH)-1] = RF_trees(condition, train_data_sub, n) 
    #                print(rf_trees)
                    for j in range(TEST):
                        y_pred_arr = np.zeros(Y_VALUE, dtype = 'int')
    #                    print(y_pred_arr)
    #                    print(test_data[:,j])
                        
                        for b_arr in range(B_ARR[condition]):
                            y_pred_arr[rf_trees[condition][int(n/N_WIDTH)-1].root_list[b_arr].classify(test_data[:,j])] += 1
                        if np.argmax(y_pred_arr) == test_data[-1,j]:
                            correct_RF[condition][int(n/N_WIDTH)-1] += 1
                        else:
                            incorrect_RF[condition][int(n/N_WIDTH)-1] += 1
    
                    #generate tree for classification
                    feature_trees_deepcopy = copy.deepcopy(feature_trees)
                    for b_arr in range(B_ARR[condition]):
                        feature_trees_deepcopy.root_list[b_arr].feature_trees_copy_RF(rf_trees[condition][int(n/N_WIDTH)-1].root_list[b_arr], condition,  [i for i in range(K)])
                    #renew posterior distribution
                    for j in range(0, n):
                        feature_trees_deepcopy.posterior_cal(train_data[:,j], condition)
    
                    #classification
                    for j in range(TEST):
                        if feature_trees_deepcopy.prediction(test_data[:,j], condition) == test_data[-1,j]:
                            correct[condition][int(n/N_WIDTH)-1] += 1
                        else:
                            incorrect[condition][int(n/N_WIDTH)-1] += 1

num = np.zeros(int(N/N_WIDTH), dtype = 'int')
error_rate_RF = np.zeros((CONDITION, int(N/N_WIDTH)), dtype = 'float')
for n in range(N_WIDTH, N + 1, N_WIDTH):
    num[int((n-1)/N_WIDTH)] = n
for condition in range(CONDITION):
    for n in range(N_WIDTH, N + 1, N_WIDTH):
        error_rate_RF[condition][int((n-1)/N_WIDTH)] = incorrect_RF[condition][int((n-1)/N_WIDTH)] / (THETA * TEST * M * TEST_EPOCH)
    error_rate_list_RF = error_rate_RF[condition].tolist()
    fig, ax = plt.subplots()
    ax.get_xaxis().get_major_formatter().set_useOffset(False)
    ax.get_xaxis().set_major_locator(ticker.MaxNLocator(integer=True))
    plt.plot(num,error_rate_list_RF)
    print(error_rate_list_RF)



error_rate = np.zeros((CONDITION, int(N/N_WIDTH)), dtype = 'float')
for condition in range(CONDITION):
    for n in range(N_WIDTH, N + 1, N_WIDTH):
        error_rate[condition][int((n-1)/N_WIDTH)] = incorrect[condition][int((n-1)/N_WIDTH)] / (THETA * TEST * M *TEST_EPOCH)
    error_rate_list = error_rate[condition].tolist()
    fig, ax = plt.subplots()
    ax.get_xaxis().get_major_formatter().set_useOffset(False)
    ax.get_xaxis().set_major_locator(ticker.MaxNLocator(integer=True))
    plt.plot(num,error_rate_list)
    print(error_rate_list)
