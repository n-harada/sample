    '''
    #まず基本情報部分 ... 現在未対応のものは、try~except文をpatch.
    _1_hospital_name = basic_result["_1_hospital_name"]
    _1_hospital_code_type = basic_result["_1_hospital_code_type"]
    _1_hospital_code = basic_result["_1_hospital_code"]
    _1_hospital_place_code = basic_result["_1_hospital_place_code"]

    _5_doctor_name_kana=basic_result['_5_doctor_name_kana']
    _5_doctor_name_kanji = basic_result['_5_doctor_name_kanji']

    _11_patient_name_kanji =basic_result["_11_patient_name_kanji"]
    _11_patient_name_kana =basic_result["_11_patient_name_kana"]

    _12_patient_sex =basic_result["_12_patient_sex"]
    
    _13_patient_birthday = basic_result['_13_patient_birthday']

    _22_insurance_patient_num =basic_result["_22_insurance_patient_num"]

    _23_insurance_card_id =basic_result["_23_insurance_card_id"]
    _23_insurance_card_num = basic_result["_23_insurance_card_num"]

    _51_prescription_date = basic_result['_51_prescription_date']

    #以上がロジックにより取得され、basic_resultに格納されていた分

    #扱いが不明の要素
    _5_doctor_code =""
    _11_patient_code = ""
    _23_insurance_type =""#1:被保険者, 2:被扶養者
    _23_insurance_card_sub_num=""

    ''''''
    #以下補足分
    #保険医師
    _5_doctor_code =""
    _5_doctor_name_kana=""#ﾃｽﾄ ｲｼ
    _5_doctor_name_kanji = ""#テスト　医師
    #患者氏名レコード
    _11_patient_code = ""
    #生年月日レコード
    _13_patient_birthday = ""#4050505
    #記号番号レコード
    _23_insurance_type =""#1
    _23_insurance_card_sub_num=""
    
    #交付年レコード
    _51_prescription_date=""#"5020909"
    ''''''
    
    #以下で上の諸要素を結合
    row_1 ="1,"+_1_hospital_code_type+","+_1_hospital_code+","+_1_hospital_place_code+","+_1_hospital_name
    row_5 ="5,"+_5_doctor_code+","+_5_doctor_name_kana+","+_5_doctor_name_kanji
    row_11 ="11,"+_11_patient_code+","+_11_patient_name_kanji+","+_11_patient_name_kana
    row_12 ="12,"+_12_patient_sex
    row_13 ="13,"+_13_patient_birthday
    row_22 ="22,"+_22_insurance_patient_num
    row_23 ="23,"+_23_insurance_card_id+","+_23_insurance_card_num+","+_23_insurance_type+","+_23_insurance_card_sub_num
    row_51 ="51,"+_51_prescription_date
    
    basic_info_qr_text = version + EOL + row_1 + EOL + row_5 + EOL + row_11 + EOL + row_12 + EOL + row_13 + EOL + row_22 + EOL + row_23 + EOL + row_51 + EOL
    '''

#---------------------------------------------------------------------------------
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