#coding:utf-8
#必要なもののimport 
import base64
import json
from requests import Request, Session
from io import BytesIO
from PIL import Image
import pandas as pd
import jaconv
import re
import cv2
import numpy as np
from symspellpy.symspellpy import SymSpell, Verbosity
import pickle
from pykakasi import kakasi
import Levenshtein
from collections import OrderedDict
import itertools
import copy

#<別場所においておいた方が良さそうな関数>----------------------------------------------------
#切り出す作業。返り値は、保険者番号、記号、基本情報の部分、左下（PHCでは不要）、右下（PHCでは不要）、下全部
def image_cut(image):
    img_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    height=img_gray.shape[0]
    width=img_gray.shape[1]
    top = image[0: 400 * height // 1030, 0 :width]
    bottom1 = image[300 * height // 1030 :height, 0 :width//2]
    bottom2 = image[300 * height // 1030 :height, width // 2 :width]
    bottom_all = image[300 * height // 1030:height, 0:width]
    
    #保険者番号、記号、基本情報の部分、左下（PHCでは不要）、右下（PHCでは不要）、下全部、縦線消去したやつ(img4)、
    return top,bottom1,bottom2,bottom_all

def convert_days(str_,genngou):
    '''XX年XX月XX日の形のstringを受取、genngouにて表された元号番号を添えて
    JAHIS規格で返す処理'''

    year = str_.split('年')[0]
    month = str_.split('年')[1].split('月')[0]
    day = str_.split('月')[1].split('日')[0]
    
    l = [re.sub(' ','',year),re.sub(' ','',month),re.sub(' ','',day)]
    
    for i in range(len(l)):
        if len(l[i])==1:
            l[i] = '0'+l[i]

    return str(genngou) + str(l[0]) + str(l[1]) + str(l[2])
#<別場所においておいた方が良さそうな関数. end>----------------------------------------------------

#<ハイパーパラメータの定義>----------------------------------------------------

#symspellのモジュール
__sym_spell_med_long_pkl = 'medicine7_8.pickle'
__sym_spell_med_short_pkl = 'medicine1_5.pickle'
__dictionary_errors_long = 'medicine_errors_7_8.pickle'
__dictionary_errors_short = 'medicine_errors_1_5.pickle'
__l_ambiguous_medicine = 'l_ambiguous_medicine.pickle' #symspellに入れても, なんか変な挙動を返す医薬品list
__l_wrong_medicine_in = 'l_wrong_medicine_in.pickle' #名寄せの結果を間違う医薬品list
__l_wrong_medicine_out = 'l_wrong_medicine_out.pickle' #名寄せの結果を間違った結果の医薬品list

#名寄せにおいて操作を変更する文字列長閾値
__val_len_min=4
__val_len_max=27

#mainの名寄せにおいて使用するmax_edit_distance_lookup
__max_edit_distance_lookup=3

#患者GE変更意思に関するdummy bool変数
__patient_GE_OK=True

#<ハイパーパラメータの定義. end.>----------------------------------------------------

#<必要情報のload>----------------------------------------------------
#symspellの準備
print('loading med symspells...')
with open(__sym_spell_med_long_pkl, 'rb') as f:
    sym_spell_med_long = pickle.load(f)

with open(__sym_spell_med_short_pkl, 'rb') as f:
    sym_spell_med_short = pickle.load(f)

with open(__dictionary_errors_long,'rb') as f:
    dictionary_errors_long = pickle.load(f)

with open(__dictionary_errors_short,'rb') as f:
    dictionary_errors_short = pickle.load(f)

with open(__l_ambiguous_medicine,'rb') as f:
    l_meds_ambiguous = pickle.load(f)

with open(__l_wrong_medicine_out,'rb') as f:
    l_wrong_medicine_out = pickle.load(f)

#医薬品データベースの読み込み ※一般名含む
print('loading medicine DB...')
with open('df_medicineInfo.pickle', 'rb') as f:
    df_medicineInfo = pickle.load(f)
df_medicineInfo = df_medicineInfo.rename(columns={'name':'品名'})

#一般名~特定銘柄, 先発薬~特定銘柄, 辞書の読み込み
with open('dict_ippan2specific.pickle','rb') as f:
    dict_ippan2specific = pickle.load(f)
with open('dict_branded2GE.pickle','rb') as f:
    dict_branded2GE = pickle.load(f)

#表記揺れの修正
for index in df_medicineInfo.index:
    df_medicineInfo.at[index,'品名'] = jaconv.normalize(df_medicineInfo.at[index,'品名'])

#薬リストの作成
l_meds = df_medicineInfo['品名'].values.tolist()
l_meds_no_space = [re.sub(' ','',i) for i in l_meds]
dict_no_space_med2raw_med = {}
for i in range(len(l_meds)):
    dict_no_space_med2raw_med[l_meds_no_space[i]] = l_meds[i]

l_meds_tail = list(set([i[-3:] for i in l_meds]))
l_meds_ambiguous_head = list(set([i[:3] for i in l_meds_ambiguous]))

s_meds_withLen = pd.Series(l_meds_no_space,index=[len(i) for i in l_meds])
l_meds_ippan = df_medicineInfo[df_medicineInfo.GE_Branded_ippan=='ippan']['品名'].values.tolist()
l_meds_GE = df_medicineInfo[df_medicineInfo.GE_Branded_ippan=='GE']['品名'].values.tolist()

#病院情報の読み込み
print('loading hospital info in vision1_med.py...should optimize...')
with open('dict_hospitalInfo.pickle', 'rb') as f:
    dict_hospitalInfo_base = pickle.load(f)
l_hospital_no_space = [re.sub(' ','',jaconv.normalize(i)) for i in dict_hospitalInfo_base.keys()]

##<必要情報のload. end>----------------------------------------------------

#<正規表現modelの定義>----------------------------------------------------
#調剤数量の正規表現list生成
l_chozaiNum_units = ['X日分','XTD','Xds','Xdays','XTH','XTM','X回分'] #'(X)'の形は話をややこしくするのでいったんpop

#用法の正規表現list生成
##pattern 1
l_1_times = ['分X']
l_1_when = ['毎食後すぐ','毎食後','各食後','各食後すぐ','朝・昼・夕食前',
            '朝夕食後','朝夕食後すぐ','朝・夕食後','朝・夕食後すぐ','朝食後と夕食後','朝・夕食後',
            '朝食後','朝食後すぐ','昼食後','昼食後すぐ','夕食後','夕食後すぐ',
            '朝食前','隔日','朝・昼・夕食後', '朝、夕食後', '就寝前','不眠時']

l_1_when_added = []
for when in l_1_when:
    l_1_when_added.append('X×'+when)

l_1_action = ['服用']

l_1 = [l_1_times,l_1_when,l_1_when_added,l_1_action]

##pattern 2
l_2_times = ['X日X回','X日X~数回','X日X回','X日X枚']
l_2_when = ['疼痛時']
l_2_action = ['塗布','貼付','保湿']
l_2_where = ['部位 *:* *','足の裏','あしのうら','趾間','足底','爪','胸部','両肩','両下肢部']

l_2 = [l_2_times,l_2_when,l_2_action,l_2_where]

#free strings
l_3_comments_1 = ['各データを比較して最良と判断した為','上記薬剤配合お願い致します']
l_3_comments_2 = ['眠気強い様なら寝る前','X分間舌下で保持したあと内服']

l_3 = [l_3_comments_1,l_3_comments_2]

##group to single list
l_youhou_parts = [l_1,l_2,l_3]
l_youhou_flat = []
for list_ in l_youhou_parts:
    for l in list_:
        l_youhou_flat.extend(l)

#単位名(用量)の正規表現list生成
l_unit = list(set(list(df_medicineInfo['unit'])))
l_unit_customs = ['T','tab','C','Cap','ml','袋'] #正式のやつじゃないけど、よく使われる省略表現
l_unit.extend(l_unit_customs)
l_units_med = []
for val in l_unit:
    if type(val)==str:
        l_units_med.append('X'+val)

def list2str(l,numCondition='[0-9, ]+\.*[0-9, ]*\n* *',youbiCondition='[月,火,水,木,金,土,日, ]+'):
    '''listを正規表現用の文字列に変換する処理'''
    str_=''
    for val in l:
        val = jaconv.normalize(val)
        val = re.sub('X',numCondition,val)
        val = re.sub('Y',youbiCondition,val)
        str_+=val+'|'
    str_ = str_[:-1]
    return str_
#<正規表現modelの定義. end.>----------------------------------------------------

#<医薬品名称の推論>----------------------------------------------------
def clense_val(str_):
    '''splitlineされた生のOCR文字列を受けとり、ノイズとなる情報を除去した情報を返す処理
    clenseした情報のうち、情報として保持しておきたい情報も同時に返す'''

    def initialze_str(input_):
        while True:
            init_str_length = len(input_)
            input_ = input_.strip()
            input_ = input_.strip('|')
            input_ = input_.strip('*')
            input_ = input_.strip('x|X|×')
            if len(input_)==init_str_length:
                return input_

    #まず空白を削除
    str_ = re.sub(' ','',str_)

    #文字列から読み取れる一般名情報の保持
    if re.search('【.*般.*】',str_) is not None:
        _bool_ippan = True
    else:
        _bool_ippan = False

    #initialize
    str_ = initialze_str(str_)

    #医薬品付帯情報をclense
    str_ = re.sub(r'内服|内用|外用|頓服','',str_) #剤形区分情報
    str_ = re.sub(list2str(l_chozaiNum_units),'',str_) #調剤数量情報
    str_ = re.sub(list2str(l_youhou_flat),'',str_) #用法情報
    str_ = re.sub('【.*般.*】','',str_) #【般】をclense
    str_ = re.sub('【|】','',str_) #【,】をclense

    l_units_med_for_clense = l_units_med[:]
    l_units_med_for_clense.remove('Xg') #医薬品名にも含まれる用量単位をremove
    str_ = re.sub(list2str(l_units_med_for_clense),'',str_) #用量情報を落とす

    #RP番号情報をclense
    str_ = re.sub('RP *. *[0-9]* *. *','',str_, flags=re.IGNORECASE) #RP.~~にて示される番号情報をclense

    if re.search(r'^ *[0-9]+ *[mg|%]',str_) is None: #医薬品を特徴づける数値じゃない場合、先頭の数字を落とす
        str_ = re.sub(r'^ *[0-9]+ *. *','',str_)

    if re.search(r'^ *\(',str_) is not None: #文頭にカッコがある場合、それに囲まれる文字列を落とす, analysis result: 名前がカッコで始める医薬品はない20200727
        search = re.search(r'\) *',str_)
        if search is not None:
            str_ = str_[search.end():]

    #re-initialize
    str_ = initialze_str(str_)

    return str_,_bool_ippan

def symspell_med(_query,_max_edit_distance_lookup,_sym_module):
    '''_sym_moduleに対して_max_edit_distance_lookupにて_querryを名寄せした際の
    結果, symspellにて判定された距離, を返す処理'''

    answer=[]
    answer_distance=[]
    input_term =_query
    _max_edit_distance_lookup = _max_edit_distance_lookup
    suggestion_verbosity = Verbosity.CLOSEST  # TOP, CLOSEST, ALL
    
    suggestions = _sym_module.lookup(input_term, suggestion_verbosity,
                               _max_edit_distance_lookup)
    for suggestion in suggestions:
        answer.append(suggestion.term)
        answer_distance.append(suggestion.distance)
    return(answer,answer_distance)

import itertools
import Levenshtein as L

def get_edited_list(_max_edit_distance,_prefix,_med):
    '''_medに対し、_max_edit_distance, _prefix分, symspellの削除処理を行った文字列listを返す処理'''
    med = _med[:_prefix]
    
    l_dictionary = []
    l_dictionary.append(med)
    l_index = list(range(len(med)))
    
    for i in range(_max_edit_distance):
        i=i+1
        for del_index_tuple in itertools.combinations(l_index,i):
            med_edit = med[:]
            del_index_list = list(del_index_tuple) #文字を落とすindex

            for j in range(len(del_index_list)):
                med_edit = med_edit[:del_index_list[j]]+med_edit[del_index_list[j]+1:] #文字を落とす

                for k in range(len(del_index_list)):
                    del_index_list[k]-=1 #文字を落としたらindexが変わるので更新, 本来はj番目以前の項目は更新する必要なし。

            l_dictionary.append(med_edit)
    
    return l_dictionary[:]

def query2symspell_dict(_query,_dictionary,_max_edit_distance_lookup,_prefix,_acceptable_leven_dist=0,_end_acceptable_threshold=1):
    '''_querryに対し、_max_edit_distance_lookup, _prefixの深さで_dictionaryに名寄せを行う処理
    名寄候補及びそれらの_querryに対する編集距離を返す。完全合致があればそこでterminate.'''

    l_query = get_edited_list(_max_edit_distance_lookup,_prefix,_query)
    count_acceptable = 0

    l_hit,l_distance = [],[]
    for med in _dictionary.keys():
        list_ = _dictionary[med]

        for val in l_query:
            if val in list_:
                distance = L.distance(med,_query)
                l_hit.append(med)
                l_distance.append(distance)
                
                if distance<=_acceptable_leven_dist:
                    count_acceptable+=1
                break
        
        if count_acceptable>=_end_acceptable_threshold:
            print()
            break

    return l_hit,l_distance


def integrated_symspell_med(_val,_min_lookup_len,_val_len_min,_val_len_max,_max_edit_distance_lookup,_sym_spell_med_long,_sym_spell_med_short,_dictionary_errors_long,_dictionary_errors_short,_use_scratch=True):
    '''設定された文字列長毎に適切なsym_spell_medモジュールをあてがい、
    それによる名寄せ結果のlistを返す処理'''

    #initialize return
    r = [[],[]]

    #患者氏名,病院名, 患者氏名カナ, 薬局っぽい文字列はここで弾く
    for hospital in l_hospital_no_space:
        if hospital in _val:
            return r

    l_precise_clense = ['薬局','ジェネリック']
    for clense in l_precise_clense:
        if clense in _val:
            return r

    ###患者氏名判定はvision1_basicsに組み込まれたら行う.####


    #最低名寄せ文字列長をベタ打ちで定義
    short_max_edit_distance_lookup = 1

    #まず、symspellモジュールにて名寄せを行う
    if  (len(_val)>_val_len_min) and (len(_val)<_val_len_max):
        r =symspell_med(_val, _max_edit_distance_lookup, _sym_spell_med_long)
    elif (len(_val)<=_val_len_min) and (len(_val)>_min_lookup_len):
        r =symspell_med(_val, short_max_edit_distance_lookup, _sym_spell_med_short)
    else:
        pass
    
    #拡張性のため, そもそもスクラッチのsymspellを用いるかのゲートを設定　... 現在, symspell scratchを使う必要がない
    '''
    if _use_scratch==False:
        return r

    #続いて、scratch symspellに回す必要があるかを判定する

    bool_to_scratch = False

    for med in r[0]:
        ##名寄せ結果の中に, 誤り名寄の可能性がある医薬品名称が存在する場合
        if med in l_wrong_medicine_out:
            bool_to_scratch = True

    if len(r[0])==0 and bool_to_scratch==False and len(_val)<=_val_len_max:
        ##名寄せ結果はnullなものの、医薬品名称っぽい文字列が存在する場合
        ##加えて, 医薬品名称としては可能性の低い文字列長出ない場合(キメで30としている)

        for head in l_meds_ambiguous_head:
            if head in _val:
                bool_to_scratch=True
                break

    #必要があると判定された場合、scratchのsymspellで名寄せを行う
    if bool_to_scratch==True:
        print('using scratch symspell',len(_val),_val)
        if  (len(_val)>_val_len_min) and (len(_val)<_val_len_max):
            r = query2symspell_dict(_val,_dictionary_errors_long,_max_edit_distance_lookup,_prefix=8)
            
        elif (len(_val)<=_val_len_min) and (len(_val)>min_lookup_len):
            r = query2symspell_dict(_val,_dictionary_errors_short,short_max_edit_distance_lookup,_prefix=5)

        else:
            r = [[],[]]
    '''

    return copy.deepcopy(r)


def parse_symspell_med_result(_val,_raw_str1,_num,_symspell_medi_result,_symspell_medi_dist,boke,_bool_multiple,_s_meds_withLen=s_meds_withLen,_leven_dist_threshold=8):
    '''symspellにて名寄せされた部分医薬品名称を受け、
    順序情報付きで処方箋に記載されている医薬品名称の推論結果listを返す'''

    #次の文字列の名寄せをskipするかの情報を初期化
    skip_next = False

    #医薬品候補, symspell_distを取得する
    l_medi_candidate,l_symspell_dist=[],[]
    for j in range(len(_symspell_medi_result)):
        medi_name = _symspell_medi_result[j]
        #symspell_dist = _symspell_medi_dist[j]
        l_meds_search = _s_meds_withLen[_s_meds_withLen.index>=len(medi_name)].values.tolist()
        for i in l_meds_search:
            if medi_name in i:
                l_medi_candidate.append(dict_no_space_med2raw_med[i])
                #l_symspell_dist.append(symspell_dist)

    #l_medi内の医薬品名~1行分のval, の編集距離を取得
    l_leven_1=[]
    for i in l_medi_candidate:
        l_leven_1.append(Levenshtein.distance(_val,i))         
    
    if _bool_multiple==False:
        #l_medi内の医薬品名~2行分のval, の編集距離を取得
        l_leven_2=[]
        max_len = max([len(i) for i in l_medi_candidate])
        try:
            compare = _val+re.sub(' ','',_raw_str1[_num+1])
            if len(compare)>max_len:
                compare = compare[:max_len]
        except IndexError:
            compare = _val
        for i in l_medi_candidate:
            l_leven_2.append(Levenshtein.distance(compare,i))
            
        #base_val近いl_levenを採用する
        if min(l_leven_1)<=min(l_leven_2):
            l_leven=l_leven_1[:]
        else:
            l_leven=l_leven_2[:]
            skip_next = True
        print('compare',compare)
    else:
        l_leven=l_leven_1[:]
        
    #薬品名候補をsymspell_dist, leven_distでソート
    s_medi = pd.Series(l_medi_candidate,index=l_leven)
    l_medi_sorted = s_medi[s_medi.index<=_leven_dist_threshold].sort_index(ascending=False).values.tolist()
    print(_val,skip_next,l_medi_sorted)
    
    #取得医薬品名称の自信を離散化する ... 現状,キメの閾値で3段階表示(2>1>0)
    if boke==True:
        confidence='0'
    else:
        min_dist=min(l_leven)
        if min_dist==0:
            confidence='2'
        elif min_dist<=2:
            confidence='1'
        else:
            confidence='0'

    return l_medi_sorted, confidence, skip_next

def judge_GE_switch_OK(_val):
    '''推論対象医薬品がGE変更可能か否かをnaiveに判定し、結果を返す処理'''
    if re.search('x|X|×',_val[:4]) is None:
        ge_switch_OK = True
    else:
        ge_switch_OK = False

    return ge_switch_OK


def secure_medicine_name(_l_medi_sorted,_bool_ippan,_patient_GE_OK,_ge_switch_OK,_dict_branded2GE=dict_branded2GE,_dict_ippan2specific=dict_ippan2specific):
    '''推論された医薬品名称list, 医師の意向としてのGE変更可否, 患者の意向としてのGE変更可否, を受け,
    調剤確定されたlistを返す処理
    処方箋上は一般名なのにここで一般名として調剤確定がなされなかった場合、アラートを上げる'''
    ##サービス初期はここはpassさせる可能性アリ

    #必要な情報・変数の定義
    search_length = 2
    search_length = min(search_length,len(_l_medi_sorted))

    #調剤確定が必要なケースを判別,listを更新
    l_medi_sorted_secured = []
    bool_ippan_converted = False
    for i in range(search_length):
        med_selected = _l_medi_sorted[-(i+1)]
        
        #先発薬かつGE変更可の場合
        if _patient_GE_OK and _ge_switch_OK and med_selected in _dict_branded2GE.keys():
            l_medi_sorted_secured.extend(_dict_branded2GE[med_selected])
            
        #一般名処方の場合
        elif med_selected in _dict_ippan2specific:
            l_extend = _dict_ippan2specific[med_selected]
            if _patient_GE_OK==False:
                l_extend = [j for j in l_extend if j not in l_meds_GE]
            l_medi_sorted_secured.extend(l_extend)
            bool_ippan_converted = True
            
        l_medi_sorted_secured.append(med_selected)
    
    #表記上は一般名なのに, 一般名変換が働いていない場合は知らせてもらう ... 潜在エラー
    '''
    if _bool_ippan is True and bool_ippan_converted is False:
        print(val,compare,'seems to be ippan. ippan2specific dict maybe incomplete.')
    '''
    
    #l_medi_sortedの残りの要素を取得する
    l_tmp = _l_medi_sorted[:-search_length]
    l_tmp.reverse()
    l_medi_sorted_secured.extend(l_tmp)
    
    #重複している薬は、index若い方を残してsetする
    l_medi_sorted_secured = sorted(set(l_medi_sorted_secured), key=l_medi_sorted_secured.index)
    
    #listを見やすい長さに切り、interface用に順番を逆順にする(今は切らずにそのまま)
    l_medi_sorted_secured = l_medi_sorted_secured[:]
    l_medi_sorted_secured.reverse()

    return l_medi_sorted_secured

def identify_str_med_info(_txt,_val,_val_raw,_raw_str1,_num,_boke,_bool_ippan,_patient_GE_OK,_l_prev_vals,_bool_multiple,_val_len_min=__val_len_min,_val_len_max=__val_len_max,_max_edit_distance_lookup=__max_edit_distance_lookup,_sym_spell_med_long=sym_spell_med_long,_sym_spell_med_short=sym_spell_med_short,_dictionary_errors_long=dictionary_errors_long,_dictionary_errors_short=dictionary_errors_short):
    
    #symspell処理を実行
    symspell_medi_result, symspell_medi_dist = integrated_symspell_med(_val,4,_val_len_min,_val_len_max,_max_edit_distance_lookup,_sym_spell_med_long,_sym_spell_med_short,_dictionary_errors_long,_dictionary_errors_short)

    #symspellに医薬品名称がhitした場合、追加処理実行
    if symspell_medi_result != []:

        #symspellの結果を基に、処方箋に記載されている医薬品名を推論 & その自信も判定する
        l_medi_sorted,confidence,skip_next = parse_symspell_med_result(_val,_raw_str1,_num,symspell_medi_result,symspell_medi_dist,_boke,_bool_multiple)

        #false alarmであった場合, ここでreturnする
        if len(l_medi_sorted)==0:
            return None,None,None,None,None,False,False,None

        #ジェネリック変更可否を取得する...ここでのTrueは"本当にGE変更OK","本当はGE変更ダメだけどOCRできてない"の2パターンあることに留意
        ge_switch_OK = judge_GE_switch_OK(_val_raw)

        #調剤確定を行う ... 今はしない
        '''l_medi_sorted_secured = secure_medicine_name(l_medi_sorted,_bool_ippan,_patient_GE_OK,ge_switch_OK)'''
        l_medi_sorted_secured = l_medi_sorted[:]

        #後続の処理のために必要な情報を格納
        ##薬品名に紐づく文字ブロックの元を取得&格納
        block = ''
        if skip_next==True:
            split_key = _val_raw+'\n'+_raw_str1[_num+1]
        else:
            split_key = _val_raw
        l_txt_split = _txt.split(split_key)
        for i in range(_l_prev_vals.count(split_key)+1):
            if i>0:
                block+=split_key
            block+=l_txt_split[i]

        return l_medi_sorted[:],confidence,ge_switch_OK,l_medi_sorted_secured[:],block,True,skip_next,split_key
    
    else:
        return None,None,None,None,None,False,False,None


#医薬品名称の推論 ... main処理
def parse_med_txt(_txt,boke,_patient_GE_OK=True):
    '''OCR結果の生の文字列を受け, 医薬品名称の名寄せ・調剤確定処理・紐づく文字列情報の切り取り、を行いそれを返す処理'''
        
    medi_list = [] #医薬品読み取り結果を格納するlist
    medi_list_raw = [] #調剤確定前の読み取り結果を格納するlist
    l_ge_switch_OK = [] #ジェネリック変更可否情報を保持するlist(bools, True:変更可, False:変更不可)
    l_confidence = [] #各医薬品名称についてのシステムとしてのconfidenceを格納するlist
    l_prev_vals = [] #処理済みのvalを格納しておくlist

    medi_text_list = [] #テキストブロックを格納するlist

    bool_previously_med = False
    skip_next = False

    #splitlines of text and clense
    raw_str1 = _txt.splitlines()
    raw_str1_clensed = [clense_val(i) for i in raw_str1]
    for num in range(len(raw_str1)):

        #次の文字列は医薬品情報の一部 or 関係ない, と分かっている場合, 処理をskipする
        if skip_next:
            skip_next=False
            continue

        #検索対象文字列の取得
        val_raw = raw_str1[num] 
        val,bool_ippan = raw_str1_clensed[num]

        #print('valraw val',val_raw,val)

        #名寄せ処理実行
        l_medi_sorted,confidence,ge_switch_OK,l_medi_sorted_secured,block,bool_was_med,skip_next,split_key = identify_str_med_info(_txt,val,val_raw,raw_str1,num,boke,bool_ippan,_patient_GE_OK,l_prev_vals,_bool_multiple=False)

        if bool_was_med:
            #取得された情報をlistに格納する
            medi_list_raw.append(l_medi_sorted)
            l_confidence.append(confidence)
            l_ge_switch_OK.append(ge_switch_OK)
            medi_list.append(l_medi_sorted_secured)
            medi_text_list.append(block)

            #他, 情報を更新
            l_prev_vals.append(split_key)
            bool_previously_med = True

        #本iteration, 及び, 前のiterationで医薬品判定がなかった場合, それらを組み合わせたら医薬品名称が表出する可能性があるため, multiple処理を行う
        elif bool_previously_med==False:
            val_multiple = None

            #医薬品名称の末尾と完全一致が存在する場合, multiple処理を行うように設定
            for tail in l_meds_tail:
                if tail in val_raw:
                    val_raw_multiple = raw_str1[num-1]+'\n'+raw_str1[num]
                    val_multiple = raw_str1_clensed[num-1][0]+raw_str1[num]
                    bool_ippan = raw_str1_clensed[num-1][1] or raw_str1_clensed[num][1]
                    break

            #multipleに対して再度名寄せ処理
            if val_multiple is not None:

                l_medi_sorted,confidence,ge_switch_OK,l_medi_sorted_secured,block,bool_was_med,skip_next,_ = identify_str_med_info(_txt,val_multiple,val_raw_multiple,raw_str1,num,boke,bool_ippan,_patient_GE_OK,l_prev_vals,_bool_multiple=True)
                if bool_was_med:

                        #取得された情報をlistに格納する
                        medi_list_raw.append(l_medi_sorted)
                        l_confidence.append(confidence)
                        l_ge_switch_OK.append(ge_switch_OK)
                        medi_list.append(l_medi_sorted_secured)
                        medi_text_list.append(block)

                        #他, 情報を更新
                        l_prev_vals.append(val_raw_multiple)
                        bool_previously_med = True

        else:
            bool_previously_med = False

    #最後に全ての医薬品情報textを格納
    medi_text_list.append(_txt)

    #明示的に名寄せ対象となった文字列を定義
    l_base_val = l_prev_vals[:]

    return medi_list[:],medi_list_raw[:],medi_text_list[:],l_confidence[:],l_ge_switch_OK[:],l_base_val[:]

#<医薬品名称の推論. end.>----------------------------------------------------

#<医薬品付帯情報の取得>----------------------------------------------------
def update_RPNum(RP_num,RP_renbanNum,chouzai_previously_there,youhou_previously_there):
    '''txtの中の文字列に応じて、更新されたRP番号を返す処理'''
    #調剤数量の文字列がそこに存在するか否か, 用法の文字列がそこに存在するか否か、の2点で判定

    if RP_num==0:
        return 1,1
    else:
        if chouzai_previously_there or youhou_previously_there:
            return RP_num+1,1
        else:
            return RP_num,RP_renbanNum+1
        

def func_101(txt,med,l1=l_chozaiNum_units,l2=l_youhou_flat,df=df_medicineInfo):
    '''ある医薬品名称に紐づいた文字列ブロック及び医薬品名称を入力として、
    101_剤形レコードに関連する情報(剤形区分・調剤数量)と思われる文字列を返す処理'''
    
    #返り値の初期化
    chouzai_was_here = False
    raw_num, num = '','-1'

    #調剤数量の取得/調剤数量が存在する場合は、素直にその値を返す
    search_chouzaiNum = re.search(list2str(l1),txt)#調剤数量の単位を探す
    if search_chouzaiNum is not None:
        raw_num = search_chouzaiNum.group()
        chouzai_was_here = True
        for val in [re.sub('X','',i) for i in l1]:
            if val in raw_num:
                num = re.sub(val,'',raw_num).strip(' ')

    '''
    #調剤数量は存在しないものの用法は存在する場合、JAHISのルールに乗っ取り1を記録する
    else:
        num='blank'       
        for val in l2:
            search = re.search(list2str([val]),txt)
            if search is not None:
                num = '1'
                break
    '''

    #剤形区分の取得 ... 頓服などのケースもあるため、本来は文字列検索の上これを行うべき.
    #{内服:1, 頓服:2, 外用:3, 内服滴剤:4, 注射:5, 医療材料:6, 不明:9}
    kubun_num = df[df['品名']==med]['剤形区分'].iloc[0]
    if kubun_num == '1':
        kubun = '内服'
    elif kubun_num == '3':
        kubun = '外用'
    else:
        kubun_num = "9"
        kubun = '不明'
        
    return num,raw_num,chouzai_was_here,kubun,kubun_num

def func_111(txt,l=l_youhou_flat):
    '''ある医薬品名称に紐づいた文字列ブロックを入力として、
    111_用法レコードに関連する情報(用法)と思われる文字列を返す処理'''

    #re用のlistを, sortの順番を意識させた上で作成      
    l_youhou_sort = l_youhou_flat[:]
    l_youhou_sort.sort(key=len,reverse=True)
    list_ = list2str(l_youhou_sort)

    #initialize    
    youhou = ''
    youhou_was_here = False
    l_youhou_raw = []

    while True:
        search_result = re.search(list_,txt)
        if search_result is not None:
            youhou_part = search_result.group()
            youhou += youhou_part
            l_youhou_raw.append(youhou)
            txt = re.sub(re.escape(youhou_part),'',txt)
        else:
            break

    if len(youhou)>0:
        youhou_was_here = True
        return re.sub('\n','',youhou), youhou_was_here,l_youhou_raw
    else:
        return '用法未取得',youhou_was_here,[]
    
def func_201(txt,med,l=l_units_med,df=df_medicineInfo):
    '''ある医薬品名称に紐づいた文字列ブロックを入力として
    201_薬品レコードの情報(医薬品コード種別・医薬品コード・用量・単位)を返す処理'''
    
    med_type = df[df['品名']==med]['GE_Branded_ippan'].iloc[0]

    #特定銘柄の場合、レセプト電算コードを取得する
    if med_type!='ippan':
        med_codeType = '2'
        med_code = df[df['品名']==med]['2_レセプト電算コード'].iloc[0]
    
    #一般名の場合、一般名コードを取得する
    else:
        med_codeType = '7'
        med_code = df[df['品名']==med]['7_一般名コード'].iloc[0]

    #用量の返り値を初期化
    youryou_num,youryou_raw = '-1',''
    unit = df[df['品名']==med]['unit'].iloc[0]
    unit_was_here = False

    #各医薬品の単位をkeyに, 用量を取得する
    search = re.search(list2str(l),txt)
    if search is not None:
        unit_was_here = True
        youryou_raw = search.group()
        for val in [re.sub('X','',i) for i in l]:
            if val in youryou_raw:
                youryou_num = re.sub(val,'',youryou_raw).strip(' ')
                unit = val
    
    return med_codeType,med_code,youryou_num,unit,youryou_raw,unit_was_here
    
def func_281(bool_):
    '''ジェネリック医薬品変更可否を表すboolを入力とし、
    変更不可な場合はそれを表すJAHIS用の2次元listを返す処理'''
    #ユーザが確認画面でジェネリック変更可否を選択したのちに、いい感じに使う想定。
    #{1:一包化, 2:粉砕, 3:後発品変更不可, 4: 剤形変更不可, 5: 含量規格変更不可, 6: 剤形変更不可および含量規格変更不可, 7:JAMI補足用法, 省略: 不明}
    
    if bool_==False:
        return [1,3,'ジェネリック変更不可']
    else:
        return ['', '', '']

#医薬品付帯情報の取得 ... main処理
def parse_med_txt_blocks(_medi_list,_medi_text_list,_l_raw_list,_l_ge_switch_OK):
    '''推論された医薬品名称list, 紐づく情報が入った文字列list,を受け取り,
    処方箋から読み取られる医薬品名称 + 付帯情報を_output_typeの形で返す処理'''

    dict_medInfo = {1: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 2: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 3: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 4: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 5: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 6: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 7: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 8: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 9: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 10: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 11: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 12: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}}
    df_correct_info = pd.DataFrame(columns=[])

    RP_num,RP_renbanNum = 0,0
    for num in range(len(_medi_list)):

        #医薬品名称情報を取得
        med = _medi_list[num] 
        med_specific = _medi_list[num][-1] #最も確からしいmedをkeyとして設定する
        raw_med = _l_raw_list[num]

        #not much used variables
        symspell_result='removed. variable_is_Left_JustinCase_of_html_issues' #dummy変数化
        med2=[3] #dummy変数化
        ge_switch_OK = _l_ge_switch_OK[num]
        ##

        #ひとつ前のstepのtext blockを取得, num=0のときのパッチもここであてておく
        if num==0:
            text_block_prev = ''
            chouzai_was_here,youhou_was_here = None,None
        else:
            text_block_prev = text_block
            
        #RP番号を更新
        RP_num,RP_renbanNum = update_RPNum(RP_num,RP_renbanNum,chouzai_was_here,youhou_was_here)
        dict_medInfo[num + 1]['RP番号'] = RP_num

        #用法, 調剤数量が存在したかのboolを明示的に初期化
        unit_was_here = False
        chouzai_was_here = False
        youhou_was_here = False

        #2つのmedi_textの差分を取って、該当text_blockを取得
        text_block_raw = _medi_text_list[num+1].split(_medi_text_list[num])[1]
        
        #text_blockをclense
        text_block_raw = re.sub(re.escape(raw_med),'',text_block_raw)
        text_block = text_block_raw

        #101_剤形レコード
        chouzaiNum,raw_chouzai_str,chouzai_was_here, zaikeiKubun,zaikeiKubunNum = func_101(text_block,med_specific)
        dict_medInfo[num+1]['剤形区分'] = zaikeiKubun ##ここ, 反映お願いしまーす！！
        dict_medInfo[num+1]['調剤数量'] = chouzaiNum
        text_block = re.sub(re.escape(raw_chouzai_str),'',text_block)
        
        #111_用法レコード    
        youhou,youhou_was_here,l_youhou_str = func_111(text_block)
        dict_medInfo[num+1]['用法名称'] = youhou
        dict_medInfo[num+1]['用法コード種別'] = 1 #基本1でOKなはず。コードなしを示す。今後要確認。

        for youhou_ in l_youhou_str:
            text_block = re.sub(re.escape(youhou_),'',text_block)

        #201_薬品レコード
        med_codeType,med_code,youryou_num,unit,youryou_str,unit_was_here = func_201(text_block,med_specific)
        dict_medInfo[num+1]['PR番号内連番'] = RP_renbanNum
        dict_medInfo[num+1]['薬品コード種別'] = med_codeType
        dict_medInfo[num+1]['薬品コード'] = med_code
        dict_medInfo[num + 1]['薬品名称'] = med
        dict_medInfo[num + 1]['symspell結果']=symspell_result
        dict_medInfo[num+1]['用量'] = youryou_num
        dict_medInfo[num+1]['力価フラグ'] = 1
        dict_medInfo[num+1]['単位名'] = unit
        text_block = re.sub(re.escape(youryou_str),'',text_block)

        #raw_medに用法用量情報が入っていなかったかを確認する
        if chouzai_was_here==False:
            chouzaiNum,raw_chouzai_str,chouzai_was_here, _,__ = func_101(raw_med,med_specific)
            if chouzai_was_here:
                dict_medInfo[num+1]['調剤数量'] = chouzaiNum
                raw_med = re.sub(re.escape(raw_chouzai_str),'',raw_med)

        if youhou_was_here==False:
            youhou,youhou_was_here,l_youhou_str = func_111(raw_med)
            if youhou_was_here:
                dict_medInfo[num+1]['用法名称'] = youhou
                for youhou_ in l_youhou_str:
                    raw_med = re.sub(re.escape(youhou_),'',raw_med)
        
        if unit_was_here==False:
            #...薬の規格を取得しそうで怖い
            _,_,youryou_num,unit,youryou_str,unit_was_here = func_201(raw_med,med_specific)
            if unit_was_here:
                dict_medInfo[num+1]['用量'] = youryou_num
                dict_medInfo[num+1]['単位名'] = unit

        #調剤数量をJAHISルールに合わせる
        if youhou_was_here and dict_medInfo[num+1]['調剤数量']=='-1':
            dict_medInfo[num+1]['調剤数量'] = '1'


        ##以下, まだサービス設計を整えた上で再度構築する情報部分
        #281_薬品補足レコード
        bool_generics_changeOK = False
        list_of_l_hosoku = func_281(ge_switch_OK)
        
        dict_medInfo[num+1]['RP番号'] = RP_num
        dict_medInfo[num+1]['PR番号内連番'] = RP_renbanNum
        dict_medInfo[num+1]['薬品補足連番'] = list_of_l_hosoku[0] #一応、281領域だけ1薬品に対して複数存在しうる
        dict_medInfo[num+1]['薬品補足区分'] = list_of_l_hosoku[1]
        dict_medInfo[num+1]['薬品補足情報'] = list_of_l_hosoku[2]

        #MEMO of マツダ: この部分, もうちょい精緻化していきたいね〜〜
        if (3 in med2)or (4 in med2):
            dict_medInfo[num + 1]['accuracy_check'] = "あった"
        else:
            dict_medInfo[num + 1]['accuracy_check'] = "なかった"
        ##以上

    return dict_medInfo


#<医薬品付帯情報の取得. end.>----------------------------------------------------
    
#<入力/出力情報の成形用の処理>-----------------------------------------------------

def double_list_2_txt(double_list,connect='\n'):
    '''rotate関数を並列で行った場合に得られる2つのlistのlistを入力とし,
    それを一つの文字列に統合して返す処理'''

    list1=double_list[0]
    list2=double_list[1]
    
    str_=''
    for list_ in list1:
        for val in list_:
            str_=str_+connect+val
        str_+='\n'
    
    for list_ in list2:
        for val in list_:
            str_=str_+connect+val
        str_+='\n'
        
    str_ = str_.strip(connect)
    str_ = re.sub('\n'+connect,'\n',str_)
    return str_

def dict_2_dataframe(test_r,l_col=['RP番号','RP連番','医薬品名称','用量数量','用量単位','用法','調剤数量']):
    '''出力された文字パース結果dictを受け, それを正解データとして取得したい
    dataframeの形に変化する処理'''
        
    l_vals = []
    df_r = pd.DataFrame(columns=l_col)
    
    for i in range(1,13):
        if test_r[i]['RP番号']=='':
            continue
            
        l_vals = [test_r[i]['RP番号'],test_r[i]['PR番号内連番'],test_r[i]['薬品名称'][-1],
                  test_r[i]['用量'],test_r[i]['単位名'],test_r[i]['用法名称'],
                  test_r[i]['調剤数量']]
        df_r = df_r.append(pd.Series(l_vals,index=l_col,name=len(df_r)))
        
    
    for index in dr_r.index:
        dr_r.at[index,'用量数量'] = re.sub(' ','',dr_r.at[index,'用量数量'])
        dr_r.at[index,'用法'] = re.sub(' ','',dr_r.at[index,'用法'])
        
        if dr_r.at[index,'用量数量'] == '':
            dr_r.at[index,'用量数量'] = '-100'
    
    dr_r = dr_r.astype({'RP番号':int,'RP連番':int,'用量数量':float,'調剤数量':float})

    return df_r

#<入力/出力情報の成形用の処理. end.>-----------------------------------------------------


###main処理###
def text_processing_med(_raw_input,boke,_output_type=dict):
    '''OCRの生の入力を受け, それに対して_output_typeの形でparseされた情報を返す処理'''
        
    #入力情報の成型
    if type(_raw_input)==list:
        text = double_list_2_txt(_raw_input)
    else:
        text = _raw_input

    #元のtextのnormalize,旧字体処理
    text = jaconv.normalize(text)
    text = text.replace('險','険')

    #医薬品名称名寄せ
    medi_list,medi_list_raw,medi_text_list,l_confidence,l_ge_switch_OK,l_base_val = parse_med_txt(text,boke)    

    #各医薬品に紐づく情報の取得
    dict_medInfo = parse_med_txt_blocks(medi_list,medi_text_list,l_base_val,l_ge_switch_OK)

    #interface上で表示される医薬品の見え方を調整する処理群
    '''
    memo: この調整は行うべきだが、logic内で行うよりももっとfront寄りの処理にすべき。いったんcomment out。
    # #一般名には【般】をheadしてあげる-
    for i in range(len(l_medi_sorted_secured)):
        if l_medi_sorted_secured[i] in l_meds_ippan:
            l_medi_sorted_secured[i] = '【般】'+l_medi_sorted_secured[i]
    '''
    
    print(dict_medInfo)

    if _output_type==dict:
        return dict_medInfo[1],dict_medInfo[2],dict_medInfo[3],dict_medInfo[4],dict_medInfo[5],dict_medInfo[6],dict_medInfo[7],dict_medInfo[8],dict_medInfo[9],dict_medInfo[10]

    elif _output_type==pd.core.frame.DataFrame:
        return dict_2_dataframe(dict_medInfo)

    else:
        raise ValueError(_output_type,'is unsupported output type')