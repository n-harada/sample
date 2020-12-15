#coding:utf-8

try:
    from algo import make_qr as mq
except ModuleNotFoundError:
    from . import make_qr as mq
    print('imported using old dir struct')

def robot_statement(reading_DONE, boke, basic_result_confidence, med_result_confidence,within_expiration_date,acc_alert_shresh=0.5):
    '''処方箋認識が完了したか否かのboolを受け、それに応じたmediRobotの
    メッセージを返す処理'''
    
    basic_info_confidence = judge_basic_confidence(basic_result_confidence)
    med_info_confidence = judge_med_confidence(med_result_confidence)

    print('basic_info_confidence,med_info_confidence',basic_info_confidence,med_info_confidence)

    #PATCH
    boke = False

    if not reading_DONE:
        msg = '認識中にエラーが発生いたしました...\n お手数ですが, 再度撮影, 不具合ご報告をお願い出来れば幸いです...'

    elif basic_info_confidence<acc_alert_shresh or med_info_confidence<acc_alert_shresh:
        if med_info_confidence<=basic_info_confidence:
            msg = '医薬品情報を中心に, 読み取りの確度が低くなっております. \n お手数ですが, 念のため結果の確認をお願い出来れば幸いです...'
        else:
            msg = '患者様の情報を中心に, 読み取りの確度が低くなっております. \n お手数ですが, 念のため結果の確認をお願い出来れば幸いです...'

    elif boke:
        msg = '画像が少しだけブレていた可能性があります... \n お手数ですが, 念のため結果の確認をお願い出来れば幸いです...'

    else:
        msg = '認識が完了いたしました！'

    if within_expiration_date==False:
        msg = msg + '\n また, 処方箋の使用期限が切れている可能性があります. 念のためご確認ください'

    return msg

def judge_basic_confidence(basic_result_confidence):

    dict_ = basic_result_confidence

    #unpack needed info
    hospital_confidence = dict_['id_1_hospital_name']
    birthday_confidence = dict_['_13_patient_birthday']
    insurance_num_confidence = dict_['id_22_insurance_patient_num']
    kouhi_num_confidence = dict_['_27_1st_kouhi_futansha_num']
    kouhi_jukyuusha_confidence = dict_['_27_1st_kouhi_jukyuusha_num']
    #prescription_date_confidence = dict_['_51_prescription_date']

    l_vals = [hospital_confidence,birthday_confidence,insurance_num_confidence]

    if insurance_num_confidence==0:
        l_vals.extend([kouhi_num_confidence, kouhi_jukyuusha_confidence])

    if len(l_vals)==0:
        return 0
    else:
        return sum(l_vals)/len(l_vals)


def judge_med_confidence(med_result_confidence):
    
    l_target_keys = mq.l_target_keys[:]

    #remove unneeded ones
    l_target_keys.remove('RP番号')
    l_target_keys.remove('RP番号内連番')
    l_target_keys.remove('用法名称')
    l_target_keys.remove('単位名')

    total, cumsum_conf = 0,0
    for i in range(len(med_result_confidence)-1):
        dict_ = med_result_confidence[i]

        med_confidence = dict_['薬品名称']
        chouzai_confidence = dict_['調剤数量']
        unit_confidence = dict_['用量']

        l_vals = [med_confidence,unit_confidence]
        if chouzai_confidence>=0:
            l_vals.append(chouzai_confidence)

        total += len(l_vals)
        cumsum_conf += sum(l_vals)

    if total==0:
        return 0
    else:
        return cumsum_conf/total

def get_basic_confidence(dict_):
    '''患者基本情報のconfidenceがNoneで渡された場合、一番自身のない形の情報構造を
    返す処理'''

    if dict_ is not None:
        return dict_
    
    else:
        basic_confidence, _ = mq.create_dummy_results()
        for key in basic_confidence.keys():
            basic_confidence[key] = 0

        return basic_confidence.copy()

def get_med_confidence(list_):
    '''医薬品情報のconfidenceがNoneで渡された場合、一番自身のない形の情報構造を
    返す処理'''

    if list_ is not None:
        return list_

    else:
        _, med_confidence = mq.create_dummy_results()
        for key in mq.l_target_keys:
            med_confidence[0][key] = 0
    

    return med_confidence
