#coding:utf-8
#必要なもののimport 
import os
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
import Levenshtein as L
from collections import OrderedDict
import itertools
import copy
from warnings import warn

#別ファイル化したcodes読み込み
try:
    from algo import med_info_def_res as def_res
except ModuleNotFoundError:
    from . import med_info_def_res as def_res
    print('imported using old dir struct')

#<ハイパーパラメータの定義>----------------------------------------------------

ROOT_DIR = os.getcwd().rstrip('/').rstrip('algo')
#harada
ROOT_DIR = os.path.dirname(os.path.abspath(__file__)).rstrip('algo')

#symspellのモジュール
__sym_spell_med_long_pkl = os.path.join(ROOT_DIR,'DB_module_pickles/medicine_front20_7_8.pickle')
__sym_spell_med_short_pkl = os.path.join(ROOT_DIR,'DB_module_pickles/medicine_front20_1_5.pickle')
_head_str_num = int(__sym_spell_med_long_pkl.split('front')[1].split('_')[0])

#名寄せにおいて操作を変更する文字列長閾値
__min_lookup_len=4
__val_len_min=4
__val_len_max=30

#mainの名寄せにおいて使用するmax_edit_distance_lookup
__long_max_edit_distance_lookup=3
__short_max_edit_distance_lookup=1

#患者GE変更意思に関するdummy bool変数
__patient_GE_OK=True

#文字列パースの際のkey
_space_connector = '<space>'
_EOL = '\n'


#<ハイパーパラメータの定義. end.>----------------------------------------------------

#<必要情報のload>----------------------------------------------------
#ベースのsymspellの準備
print('loading med symspells...')
with open(__sym_spell_med_long_pkl, 'rb') as f:
    sym_spell_med_long = pickle.load(f)

with open(__sym_spell_med_short_pkl, 'rb') as f:
    sym_spell_med_short = pickle.load(f)


#医薬品データベースの読み込み ※一般名含む
print('loading medicine DB...')
load_dir = os.path.join(ROOT_DIR,'DB_module_pickles/df_medicineInfo.pickle')
with open(load_dir, 'rb') as f:
    df_medicineInfo = pickle.load(f)
df_medicineInfo = df_medicineInfo.rename(columns={'name':'品名'})

#一般名~特定銘柄, 先発薬~特定銘柄, 辞書の読み込み
'''
with open('dict_ippan2specific.pickle','rb') as f:
    dict_ippan2specific = pickle.load(f)
with open('dict_branded2GE.pickle','rb') as f:
    dict_branded2GE = pickle.load(f)
'''

#表記揺れの修正
for index in df_medicineInfo.index:
    df_medicineInfo.at[index,'品名'] = jaconv.normalize(df_medicineInfo.at[index,'品名'])

#薬リストの作成
l_meds = df_medicineInfo['品名'].values.tolist()
l_meds_no_space = [re.sub(' ','',i) for i in l_meds]
dict_no_space_med2raw_med = {}
for i in range(len(l_meds)):
    dict_no_space_med2raw_med[l_meds_no_space[i]] = l_meds[i]

l_meds_tail = list(set([i[-3:] for i in l_meds_no_space]))

s_meds_withLen = pd.Series(l_meds_no_space,index=[len(i) for i in l_meds_no_space])
l_meds_ippan = df_medicineInfo[df_medicineInfo.GE_Branded_ippan=='ippan']['品名'].values.tolist()
l_meds_GE = df_medicineInfo[df_medicineInfo.GE_Branded_ippan=='GE']['品名'].values.tolist()

#病院情報の読み込み
print('loading hospital info in med_info.py...should optimize...')
load_dir = os.path.join(ROOT_DIR,'DB_module_pickles/dict_hospitalInfo.pickle')
with open(load_dir, 'rb') as f:
    dict_hospitalInfo_base = pickle.load(f)
l_hospital_no_space = [re.sub(' ','',jaconv.normalize(i)) for i in dict_hospitalInfo_base.keys()]

##<必要情報のload. end>----------------------------------------------------

#<正規表現modelの定義>----------------------------------------------------

#ベースの正規表現辞書の読み込み
l_chouzaiNum_units = def_res.get_chouzai_units()
l_youhou_flat,l_youhou_flat_stable = def_res.get_youhou_flat(l_meds_no_space)
l_units_med = def_res.get_med_units(df_medicineInfo)

def list2str(l,numCondition='([0-9, ]+)(\.*)([0-9, ]*)'+'(['+_EOL+'|'+_space_connector+'|'+' ]*)',youbiCondition='[月,火,水,木,金,土,日, ]+'):
    '''listを正規表現用の文字列に変換する処理'''

    str_=''
    for val in l:
        val = re.sub('X',numCondition,val)
        val = re.sub('Y',youbiCondition,val)
        str_+=val+'|'
    str_ = str_[:-1]
    return str_

def create_l_units_med_stable(l_base=l_units_med,l_meds=l_meds,unit_stable_threshold=10):
    '''医薬品規格情報でないとみなす用量単位を求める処理
    医薬品名称の中でunit_stable_threshold以内の出現回数の場合、上記とみなす'''

    l_units_med_stable = l_base[:]
    for unit in l_base:
        cnt = 0
        for med in l_meds:
            if re.search(list2str([unit]),med) is not None:
                cnt+=1
        if cnt > unit_stable_threshold:
            l_units_med_stable.remove(unit)

    return l_units_med_stable

try:
    print('loading l_units_med_stable...')
    load_dir = os.path.join(ROOT_DIR,'DB_module_pickles/l_units_med_stable.pickle')
    with open(load_dir,'rb') as f:
        l_units_med_stable = pickle.load(f)
except FileNotFoundError:
    print('l_units_med_stable was not found, creating now...')
    l_units_med_stable = create_l_units_med_stable()

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
    str_ = re.sub(list2str(l_chouzaiNum_units),'',str_) #調剤数量情報
    str_ = re.sub(list2str(l_youhou_flat_stable),'',str_) #用法情報
    str_ = re.sub('【.*般.*】','',str_) #【般】をclense
    str_ = re.sub('【|】','',str_) #【,】をclense

    str_ = re.sub(list2str(l_units_med_stable),'',str_) #確実の医薬品規格情報でない用量情報を落とす

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


def integrated_symspell_med(_val,head_str_num=_head_str_num,_val_len_min=__val_len_min,_val_len_max=__val_len_max,_min_lookup_len=__min_lookup_len,_long_max_edit_distance_lookup=__long_max_edit_distance_lookup,_short_max_edit_distance_lookup=__short_max_edit_distance_lookup,_sym_spell_med_long=sym_spell_med_long,_sym_spell_med_short=sym_spell_med_short):
    '''設定された文字列長毎に適切なsym_spell_medモジュールをあてがい、
    それによる名寄せ結果のlistを返す処理'''

    #initialize return
    r = [[],[]]

    #患者氏名,病院名, 患者氏名カナ, 薬局っぽい文字列はここで弾く
    l_precise_clense = ['薬局','ジェネリック','クリニック','医院','病院']
    for clense in l_precise_clense:
        if clense in _val:
            return r

    for hospital in l_hospital_no_space:
        if hospital in _val:
            return r

    ###患者氏名判定はvision1_basicsに組み込まれたら行う.####

    #valを使用するstringに短縮する
    _val = _val[:head_str_num]

    #まず、symspellモジュールにて名寄せを行う
    if  (len(_val)>_val_len_min) and (len(_val)<_val_len_max):
        r =symspell_med(_val, _long_max_edit_distance_lookup, _sym_spell_med_long)
    elif (len(_val)<=_val_len_min) and (len(_val)>=_min_lookup_len):
        r =symspell_med(_val, _short_max_edit_distance_lookup, _sym_spell_med_short)
    else:
        pass
    
    return copy.deepcopy(r)


def parse_symspell_med_result(_val,_raw_str,_num,_symspell_medi_result,_bool_multiple,_s_meds_withLen=s_meds_withLen,_leven_ratio_threshold=0.5,confident_ratio_threshold=0.05):
    '''symspellにて名寄せされた部分医薬品名称を受け、
    順序情報付きで処方箋に記載されている医薬品名称の推論結果listを返す'''

    #initalize base len
    base_len = len(_val)

    #次の文字列の名寄せをskipするかの情報を初期化
    skip_next = False

    #医薬品候補, symspell_distを取得する
    l_medi_candidate,l_symspell_dist=[],[]
    for j in range(len(_symspell_medi_result)):
        medi_name = re.sub(' ','',_symspell_medi_result[j])
        l_meds_search = _s_meds_withLen[_s_meds_withLen.index>=len(medi_name)].values.tolist()
        for i in l_meds_search:
            if medi_name in i:
                l_medi_candidate.append(i)

    #l_medi内の医薬品名~1行分のval, の編集距離を取得
    l_leven_1=[]
    for i in l_medi_candidate:
        l_leven_1.append(L.distance(_val,i))       
    
    if _bool_multiple==False:
        #l_medi内の医薬品名~2行分のval, の編集距離を取得
        l_leven_2=[]
        max_len = max([len(i) for i in l_medi_candidate])
        try:
            compare = _val+re.sub(' ','',_raw_str[_num+1])
            if len(compare)>max_len:
                compare = compare[:max_len]
                base_len = max_len
        except IndexError:
            compare = _val
        for i in l_medi_candidate:
            l_leven_2.append(L.distance(compare,i))
            
        #base_val近いl_levenを採用する
        if min(l_leven_1)<=min(l_leven_2):
            l_leven=l_leven_1[:]
        else:
            l_leven=l_leven_2[:]
            skip_next = True
    else:
        l_leven=l_leven_1[:]

    l_leven_ratio = [i/base_len for i in l_leven]
        
    #薬品名候補をsymspell_dist, leven_distでソート
    s_medi = pd.Series(l_medi_candidate,index=l_leven_ratio)
    s_medi_sorted = s_medi[s_medi.index<_leven_ratio_threshold].sort_index(ascending=False)
    l_medi_sorted = s_medi_sorted.values.tolist()
    l_leven_r_sorted = s_medi_sorted.index.values.tolist()
    
    #取得医薬品名称の自信を離散化する ... 現状,キメの閾値で3段階表示(2>1>0) ###UPDATE##
    if len(l_medi_sorted)==0:
        confidence = 0
    else:
        min_ratio = l_leven_r_sorted[-1]
        #print(_val,l_medi_sorted[-1],'min_ratio:',min_ratio) ##DEBUG PRINT
        if min_ratio<=confident_ratio_threshold:
            confidence = 1
            #print('-> confident') ##DEBUG PRINT
        else:
            confidence = 0
            #print('-> NOT confident') ##DEBUG PRINT

    #最後に、空白のあるもとの医薬品名称に戻す
    l_medi_sorted = [dict_no_space_med2raw_med[i] for i in l_medi_sorted]

    return l_medi_sorted, confidence, skip_next

def judge_GE_switch_OK(_val):
    '''推論対象医薬品がGE変更可能か否かをnaiveに判定し、結果を返す処理'''
    if re.search('x|X|×',_val[:4]) is None:
        ge_switch_OK = True
    else:
        ge_switch_OK = False

    return ge_switch_OK


def secure_medicine_name(_l_medi_sorted,_bool_ippan,_patient_GE_OK,_ge_switch_OK,_dict_branded2GE=None,_dict_ippan2specific=None):
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

def identify_str_med_info(_txt,_val,_val_raw,_raw_str,_num,_bool_ippan,_patient_GE_OK,_l_prev_vals,_l_connectors,_bool_multiple):
    
    #symspell処理を実行
    symspell_medi_result, _ = integrated_symspell_med(_val)

    #symspellに医薬品名称がhitした場合、追加処理実行
    if symspell_medi_result != []:

        if _bool_multiple == False:
            #2行に渡る医薬品名称の後半が別の医薬品として判別されるケースではないか、判定する
            val_lookback = clense_val(_raw_str[_num-1]+_val_raw)[0]
            lookback_result, _ = integrated_symspell_med(val_lookback)

            if lookback_result != []:
                if min([L.distance(i,_val) for i in symspell_medi_result]) > min([L.distance(i,val_lookback) for i in lookback_result]):
                    _val = val_lookback
                    _bool_multiple = True

        #symspellの結果を基に、処方箋に記載されている医薬品名を推論 & その自信も判定する
        l_medi_sorted,confidence,skip_next = parse_symspell_med_result(_val,_raw_str,_num,symspell_medi_result,_bool_multiple)

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
            split_key = _val_raw+_l_connectors[_num]+_raw_str[_num+1]
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


def judge_end(str_,prescription_sheet_num):
    '''医薬品名称の探索を取りやめるか否かを判断する処理'''
    #各処方箋の最後に"以下余白"が記載されている前提だが、これが正しいかは要検証

    l_end_key = ['以下余白']

    cnt = 0
    for val in l_end_key:
        if val in str_:
            cnt+=1
            if cnt>=prescription_sheet_num:
                return True
    return False

#医薬品名称の推論 ... main処理
def parse_med_txt(_txt,prescription_sheet_num,_patient_GE_OK=True,space_connector=_space_connector,EOL=_EOL):
    '''OCR結果の生の文字列を受け, 医薬品名称の名寄せ・調剤確定処理・紐づく文字列情報の切り取り、を行いそれを返す処理'''
        
    medi_list = [] #医薬品読み取り結果を格納するlist
    medi_list_raw = [] #調剤確定前の読み取り結果を格納するlist
    l_ge_switch_OK = [] #ジェネリック変更可否情報を保持するlist(bools, True:変更可, False:変更不可)
    l_med_name_confidence = [] #各医薬品名称についてのシステムとしてのconfidenceを格納するlist
    l_prev_vals = [] #処理済みのvalを格納しておくlist

    medi_text_list = [] #テキストブロックを格納するlist

    bool_previously_med = False
    skip_next = False

    #splitlines of text and clense
    raw_str,l_connectors = [],[]
    for val in _txt.splitlines():
        extend_list = val.split(space_connector)
        raw_str.extend(extend_list)
        l_connectors.extend([space_connector]*(len(extend_list)-1))
        l_connectors.append(EOL)

    raw_str_no_space = [re.sub(' ','',i) for i in raw_str]
    raw_str_clensed = [clense_val(i) for i in raw_str]
    for num in range(len(raw_str)):

        #次の文字列は医薬品情報の一部 or 関係ない, と分かっている場合, 処理をskipする
        if skip_next:
            skip_next=False
            continue

        #検索対象文字列の取得
        val_raw = raw_str[num]
        val_raw_no_space = raw_str_no_space[num]
        val,bool_ippan = raw_str_clensed[num]

        #名寄せ処理実行
        l_medi_sorted,confidence,ge_switch_OK,l_medi_sorted_secured,block,bool_was_med,skip_next,split_key = identify_str_med_info(_txt,val,val_raw,raw_str,num,bool_ippan,_patient_GE_OK,l_prev_vals,l_connectors,_bool_multiple=False)

        if bool_was_med:
            #取得された情報をlistに格納する
            medi_list_raw.append(l_medi_sorted)
            l_med_name_confidence.append(confidence)
            l_ge_switch_OK.append(ge_switch_OK)
            medi_list.append(l_medi_sorted_secured)
            medi_text_list.append(block)

            #他, 情報を更新
            l_prev_vals.append(split_key)
            bool_previously_med = True

        #本iteration, 及び, 前のiterationで医薬品判定がなかった場合, それらを組み合わせたら医薬品名称が表出する可能性があるため, multiple処理を行う
        elif bool_previously_med==False:
            val_multiple = None

            #spaceを落として表記ゆれを無くした上での、医薬品名称の末尾と完全一致が存在する場合, multiple処理を行うように設定
            for tail in l_meds_tail:
                if tail in val_raw_no_space:
                    val_raw_multiple = raw_str[num-1]+l_connectors[num-1]+raw_str[num]
                    val_multiple,bool_ippan = clense_val(raw_str_clensed[num-1][0]+raw_str[num])
                    bool_ippan = raw_str_clensed[num-1][1] or raw_str_clensed[num][1] or bool_ippan
                    break

            #multipleに対して再度名寄せ処理
            if val_multiple is not None:

                l_medi_sorted,confidence,ge_switch_OK,l_medi_sorted_secured,block,bool_was_med,skip_next,_ = identify_str_med_info(_txt,val_multiple,val_raw_multiple,raw_str,num,bool_ippan,_patient_GE_OK,l_prev_vals,l_connectors,_bool_multiple=True)
                if bool_was_med:

                        #取得された情報をlistに格納する
                        medi_list_raw.append(l_medi_sorted)
                        l_med_name_confidence.append(confidence)
                        l_ge_switch_OK.append(ge_switch_OK)
                        medi_list.append(l_medi_sorted_secured)
                        medi_text_list.append(block)

                        #他, 情報を更新
                        l_prev_vals.append(val_raw_multiple)
                        bool_previously_med = True

        else:
            bool_previously_med = False

        #searchを取りやめるかを判定する
        end_search = judge_end(val_raw,prescription_sheet_num)
        if end_search:
            break

    #最後に全ての医薬品情報textを格納
    medi_text_list.append(_txt)

    #明示的に名寄せ対象となった文字列を定義
    l_base_val = l_prev_vals[:]

    return medi_list[:],medi_list_raw[:],medi_text_list[:],l_med_name_confidence[:],l_ge_switch_OK[:],l_base_val[:]

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
        

def func_101(txt,med,l1=l_chouzaiNum_units,df=df_medicineInfo,space_connector=_space_connector,EOL=_EOL):
    '''ある医薬品名称に紐づいた文字列ブロック及び医薬品名称を入力として、
    101_剤形レコードに関連する情報(剤形区分・調剤数量)と思われる文字列を返す処理'''
    
    #返り値の初期化
    chouzai_was_here = False
    raw_num, num = '','-1'
    confidence = -1

    #調剤数量の取得/調剤数量が存在する場合は、素直にその値を返す
    search_chouzaiNum = re.search(list2str(l1),txt)#調剤数量の単位を探す
    if search_chouzaiNum is not None:
        raw_num = search_chouzaiNum.group()
        chouzai_was_here = True
        confidence = 1
        for val in [re.sub('X','',i) for i in l1]:
            if val in raw_num:
                num = re.sub('['+val+'|'+space_connector+'|'+EOL+'| ]','',raw_num).strip(' ')


    #調剤数量は存在しないものの用法は存在する場合、JAHISのルールに乗っ取り1を記録する
    # ... 本処理はmain側に配置
    '''
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
        
    return num,raw_num,chouzai_was_here,kubun,kubun_num, confidence

def func_111(txt,l=l_youhou_flat):
    '''ある医薬品名称に紐づいた文字列ブロックを入力として、
    111_用法レコードに関連する情報(用法)と思われる文字列を返す処理'''

    #re用のlistを, sortの順番を意識させた上で作成      
    list_ = list2str(l)

    #initialize    
    youhou = ''
    youhou_was_here = False
    l_youhou_raw = []

    while True:
        search_result = re.search(list_,txt)
        if search_result is not None:
            youhou_part = search_result.group()
            youhou += youhou_part
            l_youhou_raw.append(youhou_part)
            txt = re.sub(re.escape(youhou_part),'',txt)
        else:
            break

    if len(youhou)>0:
        youhou_was_here = True
        return youhou, youhou_was_here,l_youhou_raw
    else:
        return '用法未取得',youhou_was_here,[]
    
def func_201(txt,med,l=l_units_med,use_ambiguous=True,df=df_medicineInfo,space_connector=_space_connector,EOL=_EOL,EOL_search_limit=2):
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
    youryou_num,youryou_raw = '0',''
    unit = df[df['品名']==med]['unit'].iloc[0]
    unit_was_here = False
    confidence = 0

    #各医薬品の単位をkeyに, 用量を取得する
    search = re.search(list2str(l),txt)
    if search is not None:
        unit_was_here = True
        youryou_raw = search.group()
        for val in [re.sub('X','',i) for i in l]:
            if val in youryou_raw:
                youryou_num = re.sub('['+val+'|'+space_connector+'|'+EOL+'| ]','',youryou_raw).strip(' ')
                unit = val
                confidence = 1

    #医薬品名称が存在する行のEOL付近の数値を医薬品用量と推定する
    if unit_was_here==False and use_ambiguous:
        txt = txt.strip(EOL)
        txt = txt.strip(space_connector)
        l_withEOL = txt.split(space_connector)
        
        l = []
        for str_ in l_withEOL:
            l_split = str_.split(' ')
            for split in l_split:
                l.extend(split.splitlines())

        cnt = 0
        for val in l:
            search = re.search('([0-9]+)(\.*)([0-9]*)(\n*)',val)
            if search is not None:
                unit_was_here = True
                youryou_raw = search.group()
                youryou_num = re.sub('['+EOL+'| ]','',youryou_raw).strip()
                print(med,'unit was ambiguously obtained',youryou_num) ##DEBUG PRINT
                break
                
            cnt+=1
            if cnt>=EOL_search_limit:
                break
    
    return med_codeType,med_code,youryou_num,unit,youryou_raw,unit_was_here, confidence
    
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

dict_medInfo_base = {'RP番号': '', 'RP番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': ''}
def parse_med_txt_blocks(_medi_list,_medi_text_list,_l_raw_list,l_med_name_confidence,_l_ge_switch_OK):
    '''推論された医薬品名称list, 紐づく情報が入った文字列list,を受け取り,
    処方箋から読み取られる医薬品名称 + 付帯情報を_output_typeの形で返す処理'''

    dict_medInfo, dict_medInfo_confidence = {}, {}
    RP_num,RP_renbanNum = 0,0
    for num in range(len(_medi_list)):
        
        #新しい情報の格納先を定義
        dict_medInfo[num+1] = dict_medInfo_base.copy()
        dict_medInfo_confidence[num+1] = dict_medInfo_base.copy()

        #initialize confidence part
        dict_medInfo_confidence[num+1]['剤形区分'] = 100
        dict_medInfo_confidence[num+1]['調剤数量'] = 100
        dict_medInfo_confidence[num+1]['用法名称'] = 100
        dict_medInfo_confidence[num+1]['薬品名称'] = 100
        dict_medInfo_confidence[num+1]['用量'] = 100
        dict_medInfo_confidence[num+1]['単位名'] = 100

        #医薬品名称情報を取得
        med = _medi_list[num] 
        med_specific = _medi_list[num][-1] #最も確からしいmedをkeyとして設定する
        raw_med = _l_raw_list[num]
        med_name_confidence = l_med_name_confidence[num]

        #not much used variables
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
        if len(_medi_text_list[num])==0 and num==0: ##医薬品名称がraw_txtのど頭にあった場合, ここが''になることにパッチ
            text_block_raw = _medi_text_list[num+1]

        else:
            text_block_raw = _medi_text_list[num+1].split(_medi_text_list[num])[1]
        
        #text_blockをclense
        text_block_raw = re.sub(re.escape(raw_med),'',text_block_raw)
        text_block = text_block_raw

        #101_剤形レコード
        chouzaiNum,raw_chouzai_str,chouzai_was_here, zaikeiKubun, kubun_num, confidence= func_101(text_block,med_specific)
        dict_medInfo[num+1]['剤形区分'] = zaikeiKubun
        dict_medInfo[num+1]['調剤数量'] = chouzaiNum
        text_block = re.sub(re.escape(raw_chouzai_str),'',text_block)

        ##confidence info
        dict_medInfo_confidence[num+1]['剤形区分'] = 100
        dict_medInfo_confidence[num+1]['調剤数量'] = confidence
        
        #111_用法レコード
        youhou,youhou_was_here,l_youhou_str = func_111(text_block)
        dict_medInfo[num+1]['用法名称'] = youhou
        dict_medInfo[num+1]['用法コード種別'] = 1 #生の文字列を渡すことを宣言する1を設定

        for youhou_ in l_youhou_str:
            text_block = re.sub(re.escape(youhou_),'',text_block)

        ##confidence info
        dict_medInfo_confidence[num+1]['用法名称'] = 100

        #201_薬品レコード
        med_codeType,med_code,youryou_num,unit,youryou_str,unit_was_here, youryou_confidence = func_201(text_block,med_specific,use_ambiguous=True)
        dict_medInfo[num+1]['RP番号内連番'] = RP_renbanNum
        dict_medInfo[num+1]['薬品コード種別'] = med_codeType
        dict_medInfo[num+1]['薬品コード'] = med_code
        dict_medInfo[num + 1]['薬品名称'] = med
        dict_medInfo[num+1]['用量'] = youryou_num
        dict_medInfo[num+1]['力価フラグ'] = 1
        dict_medInfo[num+1]['単位名'] = unit
        text_block = re.sub(re.escape(youryou_str),'',text_block)

        ##confidence info
        dict_medInfo_confidence[num+1]['薬品名称'] = med_name_confidence
        dict_medInfo_confidence[num+1]['用量'] = youryou_confidence
        dict_medInfo_confidence[num+1]['単位名'] = youryou_confidence

        #raw_medに用法用量情報が入っていなかったかを確認する
        raw_med = raw_med + text_block
        if chouzai_was_here==False:
            chouzaiNum,raw_chouzai_str,chouzai_was_here, _,_,_ = func_101(raw_med,med_specific)
            if chouzai_was_here:
                dict_medInfo[num+1]['調剤数量'] = chouzaiNum
                dict_medInfo_confidence[num+1]['調剤数量'] = 0
                raw_med = re.sub(re.escape(raw_chouzai_str),'',raw_med)

        if youhou_was_here==False:
            youhou,youhou_was_here,l_youhou_str = func_111(raw_med)
            if youhou_was_here:
                dict_medInfo[num+1]['用法名称'] = youhou
                for youhou_ in l_youhou_str:
                    raw_med = re.sub(re.escape(youhou_),'',raw_med)
        
        if unit_was_here==False:
            #...薬の規格を取得してしまうリスクが一定存在することに留意
            _,_,youryou_num,unit,youryou_str,unit_was_here, youryou_confidence = func_201(raw_med,med_specific,l=l_units_med_stable,use_ambiguous=False)
            youryou_confidence = 0
            if unit_was_here:
                dict_medInfo[num+1]['用量'] = youryou_num
                dict_medInfo[num+1]['単位名'] = unit

                dict_medInfo_confidence[num+1]['用量'] =youryou_confidence
                dict_medInfo_confidence[num+1]['単位名'] =youryou_confidence

        #調剤数量をJAHISルールに合わせる
        if youhou_was_here and dict_medInfo[num+1]['調剤数量']=='-1':
            dict_medInfo[num+1]['調剤数量'] = '1'
            dict_medInfo_confidence[num+1]['調剤数量'] = 1


        ##以下, まだサービス設計を整えた上で再度構築する情報部分
        #281_薬品補足レコード
        bool_generics_changeOK = False
        list_of_l_hosoku = func_281(ge_switch_OK)
        
        dict_medInfo[num+1]['RP番号'] = RP_num
        dict_medInfo[num+1]['RP番号内連番'] = RP_renbanNum
        dict_medInfo[num+1]['薬品補足連番'] = list_of_l_hosoku[0] #一応、281領域だけ1薬品に対して複数存在しうる
        dict_medInfo[num+1]['薬品補足区分'] = list_of_l_hosoku[1]
        dict_medInfo[num+1]['薬品補足情報'] = list_of_l_hosoku[2]

    #最後に、空白の場所を定義
    dict_medInfo[len(_medi_list)+1] = dict_medInfo_base.copy()
    dict_medInfo_confidence[len(_medi_list)+1] = dict_medInfo_base.copy()

    return dict_medInfo, dict_medInfo_confidence


#<医薬品付帯情報の取得. end.>----------------------------------------------------
    
#<入力/出力情報の成形用の処理>-----------------------------------------------------

def double_list_2_txt(double_list,connect='\n'):
    '''rotate関数を並列で行った場合に得られる2つのlistのlistを入力とし,
    それを一つの文字列に統合して返す処理'''

    warn('double_list_2_txt currently using old Rules.')

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

def single_list_2_txt(single_list,space_connector=_space_connector,EOL=_EOL):
    '''
    行ごとに取得したOCR結果の二次元配列を入力とし、それらをspace_connector, EOLでつなぎ合わせ、
    一つの文字列として返す処理
    '''

    list1=single_list
    
    str_=''
    for list_ in list1:
        for val in list_:
            str_=str_+space_connector+val
        str_+=EOL
    
    str_ = str_.strip(space_connector)
    str_ = str_.strip(EOL)
    str_ = re.sub(EOL+space_connector, EOL, str_)
    return str_

def dict_2_dataframe(test_r,l_col=['RP番号','RP連番','医薬品名称','用量数量','用量単位','用法','調剤数量']):
    '''出力された文字パース結果dictを受け, それを正解データとして取得したい
    dataframeの形に変化する処理'''
        
    l_vals = []
    df_r = pd.DataFrame(columns=l_col)
    
    for i in range(1,13):
        if test_r[i]['RP番号']=='':
            continue
            
        l_vals = [test_r[i]['RP番号'],test_r[i]['RP番号内連番'],test_r[i]['薬品名称'][-1],
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
def text_processing_med(raw_input,prescription_sheet_num,_output_type=list):
    '''OCRの生の入力を受け, それに対して_output_typeの形でparseされた情報を返す処理'''
        
    #入力情報の成型
    if type(raw_input)==list:
        text = single_list_2_txt(raw_input)
    else:
        text = raw_input

    #元のtextのnormalize,旧字体処理
    text = text.replace('險','険')

    #医薬品名称名寄せ
    medi_list,medi_list_raw,medi_text_list,l_med_name_confidence,l_ge_switch_OK,l_base_val = parse_med_txt(text,prescription_sheet_num) 

    #各医薬品に紐づく情報の取得
    dict_medInfo,dict_medInfo_confidence = parse_med_txt_blocks(medi_list,medi_text_list,l_base_val,l_med_name_confidence,l_ge_switch_OK)

    #interface上で表示される医薬品の見え方を調整する処理群
    ##一般名には【般】をheadしてあげる-

    for key in dict_medInfo.keys():
        l_meds = dict_medInfo[key]['薬品名称'][:]
        
        for i in range(len(l_meds)):
            if l_meds[i] in l_meds_ippan:
                l_meds[i] = '【般】'+l_meds[i]

        dict_medInfo[key]['薬品名称'] = l_meds[:]
    
    if _output_type==list:
        med_result, med_result_confidence = [], []
        for i in range(len(dict_medInfo)):
            med_result.append(dict_medInfo[i+1])
            med_result_confidence.append(dict_medInfo_confidence[i+1])
        return med_result, med_result_confidence

    elif _output_type==pd.core.frame.DataFrame:
        return dict_2_dataframe(dict_medInfo)

    else:
        raise ValueError(_output_type, 'is unsupported output type')
