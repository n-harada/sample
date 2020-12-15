import os
import codecs
import pandas as pd
import re
import jaconv

ROOT_DIR = os.getcwd().rstrip('/').rstrip('algo')
#harada
ROOT_DIR = os.path.dirname(os.path.abspath(__file__)).rstrip('algo')

#-----------------------------------調剤数量の正規表現list生成-----------------------------------
l_chouzaiNum_units = ['X日分','XTD','Xds','Xdays','XTH','XTM','X回分'] #'(X)'の形は話をややこしくするのでいったんpop

def get_chouzai_units(l_chouzaiNum_units=l_chouzaiNum_units):
    return [jaconv.normalize(i) for i in l_chouzaiNum_units]

#-----------------------------------用法の正規表現list生成-----------------------------------
#=================hand definded part========================
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


#=================import csv part========================
csv_dir = os.path.join(ROOT_DIR,'mzd_for_upload/youhou_master/Usage.csv')
with codecs.open(csv_dir, 'r','shift_jis' , 'ignore') as f:
    df = pd.read_csv(f,header=None)

##init parse
youhou_vals = df[[3,4,5]].values
youhou_vals = list(youhou_vals.reshape(-1,))
youhou_vals = [jaconv.normalize(i) for i in youhou_vals]
youhou_vals = list(set(youhou_vals))


##parse out further
youhou_vals = [re.sub(re.escape('*'),'X',i) for i in youhou_vals]
youhou_vals = [re.sub('[0-9]','X',i) for i in youhou_vals]
youhou_vals = [re.sub('X+','X',i) for i in youhou_vals]
youhou_vals = [i.strip('X') for i in youhou_vals]

l = []
for val in youhou_vals:
    l.append(val)
    l.extend(val.split(' '))

youhou_vals = [i.strip() for i in youhou_vals]
youhou_vals = [i for i in youhou_vals if len(i)>=2]
youhou_vals = list(set(youhou_vals[:]))

def get_youhou_flat(l_meds_no_space,l_youhou_parts=l_youhou_parts,l_imported=youhou_vals):
    l_youhou_flat = []
    for list_ in l_youhou_parts:
        for l in list_:
            l_youhou_flat.extend(l)

    l_youhou_flat.extend(l_imported)
    l_youhou_flat = list(set(l_youhou_flat))

    l_youhou_flat.sort(key=len,reverse=True)
    l_youhou_flat = [jaconv.normalize(i) for i in l_youhou_flat]

    l_youhou_flat_stable = l_youhou_flat[:]
    for youhou_str in l_youhou_flat:
        for med in l_meds_no_space:
            if youhou_str in med:
                l_youhou_flat_stable.remove(youhou_str)
                break
        

    return l_youhou_flat, l_youhou_flat_stable


#-----------------------------------単位名(用量)の正規表現list生成-----------------------------------
def get_med_units(df_medicineInfo):
    l_unit = list(set(list(df_medicineInfo['unit'])))
    l_unit_customs = ['T','tab','C','Cap','ml','袋','mL','mg'] #正式のやつじゃないけど、よく使われる省略表現
    l_unit.extend(l_unit_customs)
    l_unit.sort(key=len)
    l_units_med = []
    for val in l_unit:
        if val=='':
            continue
        if type(val)==str:
            l_units_med.append('X'+val)

    return [jaconv.normalize(i) for i in l_units_med]
