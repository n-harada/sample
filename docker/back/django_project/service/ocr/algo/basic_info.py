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
import regex
import copy
import cv2
import numpy as np
from symspellpy.symspellpy import SymSpell, Verbosity
import pickle
from pykakasi import kakasi
import Levenshtein as L
from collections import OrderedDict
import itertools
#import MeCab
from janome.tokenizer import Tokenizer
import datetime as dt
import warnings

ROOT_DIR = os.getcwd().rstrip('/').rstrip('algo')
#harada
ROOT_DIR = os.path.dirname(os.path.abspath(__file__)).rstrip('algo')

#文字列 -> コードの対応dict生成
_dict_gengou_ids = {'明治':'1', '大正':'2', '昭和':'3', '平成':'4', '令和':'5'}
_dict_patient_sex_ids = {'男':'1','女':'2'}
_dict_insurance_type_ids = {'被保険者':'1','被扶養者':'2'}
_dict_era_start = {'明治':1868, '大正':1912, '昭和':1926, '平成':1989, '令和':2019}
_dict_era_length = {'明治':45, '大正':15, '昭和':64, '平成':31, '令和':dt.date.today().year-_dict_era_start['令和']+1}

#保険の法別番号 ... https://www.shaho.co.jp/shaho/shop/usr_data/sample/17121-sample.pdf
insurance_bylaw_header = {
    '01':'全国健康保険協会管掌健康保険','02':'船員保険','03':'日雇特例被保険者の保険_一般療養','04':'日雇特例被保険者の保険_特別療養費',
    '06':'組合管掌健康保険','07':'防衛省職員給与法による自衛官等の療養の給付',
    '31':'国家公務員共済組合','32':'地方公務員等共済組合','33':'警察共済組合_日本私立学校振興・共済事業団','39':'高齢者の医療の確保に関する法律による療養の給付',
    '63':'特定健康保険組合（特例退職被保険者）','67':'国民健康保険法による退職者医療'
}

kouhi_bylaw_header = {
    '10':'結核患者の適正医療','11':'結核患者の入院','28':'一類感染症等の患者の入院','29':'新感染症の患者の入院',
    '12':'生活保護法による医療扶助','25':'中国残留邦人等の円滑な帰国の促進並びに永住帰国した中国残留邦人等及び特定配偶者の自立の支援に関する法律第14条第４項に規定する医療支援給付',
    '13':'戦傷病者特別援護法による_療養の給付','14':'戦傷病者特別援護法による_更生医療',
    '15':'障害者総合支援法による_更生医療','16':'障害者総合支援法による_育成医療', '21':'障害者総合支援法による_精神通院医療','24':'障害者総合支援法による_療養介護医療及び基準該当療養介護医療',
    '17':'児童福祉法による_療育の給付','79':'児童福祉法による_肢体不自由児通所医療及び障害児入所医療',
    '18':'原子爆弾被爆者に対する援護に関する法律による_認定疾病医療','19':'原子爆弾被爆者に対する援護に関する法律による_一般疾病医療費',
    '20':'精神保健及び精神障害者福祉に関する法律による措置入院','22':'麻薬及び向精神薬取締法による入院措置',
    '23':'母子保健法による養育医療','30':'心神喪失等の状態で重大な他害行為を行った者の医療及び観察等に関する法律による医療の実施に係る医療の給付',
    '38':'肝炎治療特別促進事業に係る医療の給付','62':'特定B型肝炎ウイルス感染者給付金等の支給に関する特別措置法による定期検査費及び母子感染防止医療費の支給',
    '51':'特定疾患治療費、先天性血液凝固因子障害等治療費、水俣病総合対策費の国庫補助による療養費及び研究治療費、茨城県神栖町における有機ヒ素化合物による環境汚染及び健康被害に係る緊急措置事業要綱による医療費及びメチル水銀の健康影響による治療研究費',
    '52':'児童福祉法による小児慢性特定疾病医療支援','53':'児童福祉法の措置等に係る医療の給付',
    '54':'難病の患者に対する医療等に関する法律による特定医療','66':'石綿による健康被害の救済に関する法律による医療費の支給'
}

#janomeのtokenizerの定義
print('loading janome tokneizer...')
csv_dir = os.path.join(ROOT_DIR,'DB_module_pickles/merge.csv')
name_tokenizer = Tokenizer(csv_dir, udic_enc="utf-8")

#------------------------------
#基本情報取得部分全体
basic_result_base={
    "id_1_hospital_name":"","_1_hospital_code_type":"","_1_hospital_code":"","_1_hospital_place_code":"",
    '_5_doctor_name_kana':'','_5_doctor_name_kanji':'',
    "id_11_patient_name_kanji":"","id_11_patient_name_kana":"",
    "id_12_patient_sex":"",
    '_13_patient_birthday':"",'id_13_patient_birthday_nonJAHIS':'',
    "id_22_insurance_patient_num":"",
    "id_23_insurance_card_id":"","id_23_insurance_card_num":"","_23_insurance_type":"",
    "_27_1st_kouhi_futansha_num":"","_27_1st_kouhi_jukyuusha_num":"",
    '_51_prescription_date':"",'id_51_prescription_date_nonJAHIS':''}

def basic_info(ocr_result, base_dict=basic_result_base):
    '''
    基本情報処理全体の関数
    input:OCR結果を入れた辞書{"top_left_1":"","top_left_2":"","top_right_1":"","top_right_2":"","med":"","insurance_patient_num":""}
    output:basic_result
    '''
    
    #initialize
    basic_result = base_dict.copy()
    basic_result_confidence = base_dict.copy()

    #医療機関
    hospital_result, nxt_input, confidence, hospital_not_found=hospital_name_search(ocr_result["top_right_2"])
    basic_result["id_1_hospital_name"] = hospital_result["name"]
    basic_result["_1_hospital_code_type"] =hospital_result["code_list"][0]
    basic_result["_1_hospital_code"]=hospital_result["code_list"][1]
    basic_result["_1_hospital_place_code"] = hospital_result["code_list"][2]

    basic_result_confidence["id_1_hospital_name"] = confidence
    basic_result_confidence["_1_hospital_code_type"] = confidence
    basic_result_confidence["_1_hospital_code"]= confidence
    basic_result_confidence["_1_hospital_place_code"] = confidence

    #医師氏名
    name_result = kanji_name([nxt_input],flag='doctor',hospital_notFound=hospital_not_found)
    basic_result['_5_doctor_name_kanji'] = name_result[1]+"　"+name_result[2]
    basic_result['_5_doctor_name_kana'] = kana_name(name_result[1])+" "+kana_name(name_result[2])

    basic_result_confidence['_5_doctor_name_kanji'] = 100
    basic_result_confidence['_5_doctor_name_kana'] = 100

    #患者氏名
    name_result = kanji_name([ocr_result["top_left_1"]],flag='patient')
    basic_result["id_11_patient_name_kanji"] = name_result[1]+"　"+name_result[2]
    basic_result["id_11_patient_name_kana"] = kana_name(name_result[1])+" "+kana_name(name_result[2])

    basic_result_confidence["id_11_patient_name_kanji"] = 100
    basic_result_confidence["id_11_patient_name_kana"] = 100

    #患者生年月日・処方箋交付年月日
    try:
        _13_patient_birthday,_13_patient_birthday_visible, _,_,_, confidence = get_dates([ocr_result["top_left_1"]],key_now='_13_')
    except Exception as e: ##PATCH
        print('ERROR IN BIRTHDAY',e.args)
        _13_patient_birthday, _13_patient_birthday_visible,confidence = 'XXX','XXX', 0
    basic_result['_13_patient_birthday'] = _13_patient_birthday
    basic_result['id_13_patient_birthday_nonJAHIS'] = _13_patient_birthday_visible
    basic_result_confidence['_13_patient_birthday'] = confidence
    basic_result_confidence['id_13_patient_birthday_nonJAHIS'] = confidence

    try:
        _, _, _51_prescription_date,_51_prescription_date_visible, within_expiration_date, confidence = get_dates([ocr_result["top_left_1"]],key_now='_51_')
    except Exception as e: ##PATCH
        print('ERROR IN KOUFUDAY',e.args)
        _51_prescription_date, _51_prescription_date_visible,within_expiration_date, confidence = 'XXX','XXX',None,0
    basic_result['_51_prescription_date'] = _51_prescription_date
    basic_result['id_51_prescription_date_nonJAHIS'] = _51_prescription_date_visible
    basic_result_confidence['_51_prescription_date'] = confidence
    basic_result_confidence['id_51_prescription_date_nonJAHIS'] = confidence

    #性別
    basic_result["id_12_patient_sex"] = kata2gender(basic_result["id_11_patient_name_kana"])
    basic_result_confidence["id_12_patient_sex"] = 0

    #保険情報群
    if ocr_result['insurance_kigou_bangou'][0][0] == 'was_empty_img':
        parsed_result, parsed_result_confidence = get_kouhi_hokensha_nums(ocr_result['top_band'])
        _27_1st_kouhi_futansha_num, id_22_insurance_patient_num = parsed_result[0][0],parsed_result[1][0]
        _27_1st_kouhi_jukyuusha_num = parsed_result[2][0]
        id_23_insurance_card_id, id_23_insurance_card_num = parsed_result[3][0], parsed_result[3][1]

        _27_futansha_confidence, _22_confidence = parsed_result_confidence[0],parsed_result_confidence[1]
        _27_jukyuusha_confidence = parsed_result_confidence[2]
        _, _ = parsed_result_confidence[3], parsed_result_confidence[4]

    else:
        #保険者番号
        lid_22_insurance_patient_num, _22_confidence = get_num_using_checkDigit(ocr_result["insurance_patient_num"],search_type='hokensha_num')
        id_22_insurance_patient_num = lid_22_insurance_patient_num[0]

        #記号番号
        symbol_number_result =symbol_number(ocr_result["insurance_kigou_bangou"])
        id_23_insurance_card_id = symbol_number_result[0]
        id_23_insurance_card_num = symbol_number_result[1]

        #公費番号
        l_27_1st_kouhi_futansha_num, _27_futansha_confidence = get_num_using_checkDigit(ocr_result["kouhi_1"],search_type='kouhi_num',l_permitted_len=[8])
        _27_1st_kouhi_futansha_num = l_27_1st_kouhi_futansha_num[0]
        l_27_1st_kouhi_jukyuusha_num, _27_jukyuusha_confidence = get_num_using_checkDigit(ocr_result["kouhi_2"],search_type='kouhi_num',l_permitted_len=[7])
        _27_1st_kouhi_jukyuusha_num = l_27_1st_kouhi_jukyuusha_num[0]

    basic_result["id_22_insurance_patient_num"] = id_22_insurance_patient_num
    basic_result["id_23_insurance_card_id"] = id_23_insurance_card_id
    basic_result["id_23_insurance_card_num"] = id_23_insurance_card_num
    basic_result["_23_insurance_type"] = 'XXX'
    basic_result["_27_1st_kouhi_futansha_num"] = _27_1st_kouhi_futansha_num
    basic_result["_27_1st_kouhi_jukyuusha_num"] = _27_1st_kouhi_jukyuusha_num

    basic_result_confidence["id_22_insurance_patient_num"] = _22_confidence
    basic_result_confidence["id_23_insurance_card_id"] = 100
    basic_result_confidence["id_23_insurance_card_num"] = 100
    basic_result_confidence["_23_insurance_type"] = 0
    basic_result_confidence["_27_1st_kouhi_futansha_num"] = _27_futansha_confidence
    basic_result_confidence["_27_1st_kouhi_jukyuusha_num"] = _27_jukyuusha_confidence
    
    return basic_result, basic_result_confidence, within_expiration_date
        

#---------------------------------------------------------------------------------
#氏名周り
def kanji_name(text_list,flag,hospital_notFound=False):
    '''
    患者氏名取得
    input:リスト内包リスト 例:[['(この処方せんは、ど'],[],[]]
    output:患者氏名,姓,名
    '''

    def init_clense_list(text_list,flag):
        '''氏名文字列を含む可能性の低い領域を落とす処理'''

        if flag=='patient':
            text_list=word_check_list(text_list,"受給者番号")
            text_list=word_check_list(text_list,"負担者番号")
            #text_list=kata_check_list(text_list)
            text_list=name_check_list(text_list)
            text_list=date_check_list(text_list)
        
        elif flag=='doctor':
            text_list=word_check_list(text_list,"電話")

            if hospital_notFound:
                text_list=word_check_list2(text_list,"医氏名")
                text_list=date_check_list(text_list)

        else:
            raise ValueError(flag,'is not supported')

        return text_list

    def acquire_name_string_candidates(text_list,flag):
        '''氏名文字列が入っている可能性のある3次元配列を受け、
        名前の可能性のある生の文字列list, 初期的に姓名を判定した結果のlist, を返す処理'''
        l_searched_raw_vals, l_wakati_results = [],[]
        for i in range(len(text_list)):
            #1行単位ごとに、氏名判定を実施していく
            vals_searched, after_wakati=[],[]
            for s in text_list[i]:
                for s_ in s:
                    if should_judge_name(s_,flag):
                        s_ = init_clense_str(s_)
                        vals_searched.append(fix_youon_main(s_))
                        after_wakati.append(wakati(fix_youon_main(s_)))
            #log result
            l_searched_raw_vals.append(vals_searched)
            l_wakati_results.append(after_wakati)

        return l_searched_raw_vals, l_wakati_results

    def should_judge_name(str_,flag):
        '''患者氏名をjanomeを用いて取得しに行くべきか否かを判別する処理'''

        if flag=='patient':
            l_complete_match_reject = ["患", '氏名', '氏', '関']
            l_if_inclusive_reject = ['所在', '及び名', '診療', '関の', '保健医療', '保険医']
        elif flag=='doctor':
            l_complete_match_reject = ["患", '氏名', '氏', '関']
            l_if_inclusive_reject = ['所在', '及び名', '診療', '関の']

        else:
            raise ValueError(flag,'is not supported')

        
        for val in l_complete_match_reject:
            if str_==val:
                return False
        for val in l_if_inclusive_reject:
            if val in str_:
                return False
        return True

    def init_clense_str(str_):
        '''姓名searchを行う前に、ルールベースで文字列をclenseする処理'''
     
        str_ = str_.split('氏名')[-1]
        return str_


    def parse_candidate_names_to_single_list(l_searched_raw_vals, l_wakati_results):
        '''初期的な姓名判定結果listsを受け、最終的に氏名文字列として再度判定を行う
        文字列を決定する'''

        l = [None] * len(l_wakati_results) #最終的に名前の文字列の候補とする文字列list

        for i in range(len(l_wakati_results)):
            wakati_result_now = l_wakati_results[i]
            searched_raw_val_now = l_searched_raw_vals[i]

            #姓名どちらも取得されたケースを集計する
            name_kouho_list=[]
            for j in range(len(wakati_result_now)):
                if wakati_result_now[j][0]!="" and wakati_result_now[j][1]!="":
                    name=searched_raw_val_now[j]
                    name_kouho_list.append(name)

            #姓名どちらも取得出来ていた場合、その出力を更にパースする 
            if len(name_kouho_list)>0:
                names_were_fully_katakana = True

                #name_kouho_listの中に漢字を含む文字列が存在した場合、それを氏名候補文字列とする
                for name_kouho in name_kouho_list:
                    if kata(name_kouho)==False:
                        l[i]=[name_kouho,""]
                        names_were_fully_katakana = False
                        break
                
                #漢字を含む文字列が存在しなかった場合、カタカナの氏名であると判断しそも文字列を氏名候補文字列とする
                if names_were_fully_katakana and len(name_kouho_list)==1:
                    #name_kouhoが一つしかない場合は, それをそのまま文字列候補とする
                    l[i]=name_kouho_list[0]
                if names_were_fully_katakana and len(name_kouho_list)>1:
                    #['ｼﾞｪｰﾑｽﾞ','ジェームズ',~無関係な文字列],という入力がempericalに多いため, index 1を取得
                    l[i]=name_kouho_list[1]

            #姓名のペアが存在し、それによりl[i]が更新されたら、ここでiteration終了
            if l[i] is not None:
                continue

            #姓名の片方のみを取得しているケースを集計する            
            for j in range(len(wakati_result_now)):
                if wakati_result_now[j][0]!="":#姓のみが取れている場合
                    try:
                        if searched_raw_val_now[j].split(wakati_result_now[j][0])[1]!="":
                            #wakatiで取得された文字列が一部のみであった場合、raw_valを氏名候補に定義する
                            l[i]=[searched_raw_val_now[j],""]
                            break
                        else:
                            #wakatiで完全に情報を取得していた場合、次の文字列を名の候補とする
                            l[i]=[searched_raw_val_now[j],searched_raw_val_now[j+1]]
                            break
                    except Exception  as e:
                        l[i]=[searched_raw_val_now[j],""]
                        print('name function Error 1, e.args',e.args)

                elif wakati_result_now[j][1]!="":#名のみが取れている場合
                    try:
                        if searched_raw_val_now[j].split(wakati_result_now[j][1])[0]!="":
                            #wakatiで取得された文字列が一部のみであった場合、raw_valを氏名候補に定義する
                            l[i]=["",searched_raw_val_now[j]]
                            break
                        else:
                            #wakatiで完全に情報を取得していた場合、一つ前の文字列を姓の候補とする
                            l[i]=[searched_raw_val_now[j-1],searched_raw_val_now[j]]
                            break
                    except Exception as e:
                        l[i]=[searched_raw_val_now[j],""]
                        print('name functino Error 2, e.args',e.args)

        #ここまでの処理で何もhitしなかった場合は、emptyなlistを返す
        for i in range(len(l)):
            if l[i] is None:
                l[i] = ["",""]

        return l

    def final_clense_str(name_str,flag):
        '''最後の姓名判定を行う前に、氏名候補文字列をclenseする処理'''
        
        if flag=='patient':
            #init clensing
            name_str = name_str.split('氏名')[-1]
            name_str = name_str.replace(" ","")
            name_str=name_str.replace("っ","つ")#小さい「っ」がつく名前は4つしかない

            #using re module
            name_str=re.sub(r'[^\w]', '',  name_str) #これ何しているか未理解
            search = re.search('[0-9]',name_str)         #数値があればそれ以降を落とす
            if search is not None:
                name_str = name_str.split(search.group())[0]

            #stripping the ends
            ##name_str=name_str.lstrip("名")
            name_str=name_str.lstrip("患")
            name_str=name_str.rstrip("様")

        elif flag=='doctor':
            #init clensing
            name_str = name_str.split('氏名')[-1]
            name_str = name_str.replace(" ","")
            name_str=name_str.replace("っ","つ")#小さい「っ」がつく名前は4つしかない

            #using re module
            name_str=re.sub(r'[^\w]', '',  name_str) #これ何しているか未理解
            search = re.search('[0-9]',name_str)         #数値があればそれ以降を落とす
            if search is not None:
                name_str = name_str.split(search.group())[0]

            #stripping the ends
            ##name_str=name_str.lstrip("名")
            ##name_str=name_str.lstrip("患")
            ##name_str=name_str.rstrip("様")


        else:
            raise ValueError(flag,'is not supported')

        return name_str

    ###main###

    #initialize and clense
    text_list = init_clense_list(text_list,flag)

    #氏名文字列をおそらく含んでいる文字列listを取得する
    l_searched_raw_vals, l_wakati_results = acquire_name_string_candidates(text_list,flag)

    #おそらく文字列を含んでいる、というステータスから、最終的に氏名候補として使用する文字列を特定する
    l_name_final_candidates = parse_candidate_names_to_single_list(l_searched_raw_vals,l_wakati_results)
        
    #最後に、検索をかける文字列をclenseし、姓名判別を行う
    if len(l_name_final_candidates)>1:
        warnings.warn('list of name candidates is longer than expected')

    for i in l_name_final_candidates:
        name="".join(i)
        name = final_clense_str(name,flag)
    final_janome_result = [token for token in name_tokenizer.tokenize(name)]
    final_janome_result_surface = [token.surface for token in final_janome_result]
    
    #final_janome_resultの結果に応じ、返す文字列を決定する
    if len(final_janome_result)==0:
        #janomeを最後に適用するべきと判定された文字列がない場合は、ダミー値を返す
        surname, given_name = 'XXX',''
    else:
        #janomeを最後に適用すべき文字列が存在する場合、姓の判定が連続している最初の文字群を姓、それ以降を名として取得する
        surname, surname_start = "",False
        for token in final_janome_result:
            l_part_of_speech = token.part_of_speech.split(',')
            if judge_part_of_speech_is_surname(l_part_of_speech)==True:
                surname+=token.surface
                surname_start = True
            elif surname_start==True and judge_part_of_speech_is_surname(l_part_of_speech)==False:
                break

        if surname=="":
            surname = final_janome_result_surface[0]
            given_name = "".join(final_janome_result_surface[1:])
        
        else:
            given_name = name.split(surname)[1]        
        
    #漢字 -> ひらがな という名前は無いものとして、それが存在した場合はclenseする
    p_kanji = regex.compile(r'\p{Script=Han}+')
    p_katakana = re.compile('[\u30A1-\u30FF]+')
    p_hiragana = re.compile('[\u3041-\u309F]+')

    s_kanji = p_kanji.search(given_name)
    s_hiragana = p_hiragana.search(given_name)

    if s_kanji is not None and s_hiragana is not None:
        kanji_end = s_kanji.span()[1]
        hiragana_start = s_hiragana.span()[0]
        if kanji_end<=hiragana_start:
            given_name = given_name[:hiragana_start]

    return surname+given_name, surname, given_name

def kata(text):
    '''
    入力が全てカタカナかどうかを判断する
    input:テキスト
    output:もし全部カタカナならTrue、違うならFalse
    '''
    re_katakana = re.compile(r'[\u30A1-\u30F4]+')
    if re_katakana.fullmatch(text):
        return True
    else:
        return False


def fix_youon_main(text):
    '''stringを入力として受け、その中に間違えている拗音があれば変換して返す処理'''

    dict_target_small_sounds = {"ゃ":"や","ゅ":"ゆ","ょ":"よ","ャ":"ヤ","ュ":"ユ","ョ":"ヨ"}
    l_youon_pre_characters=["み","ミ","び","ビ","に","ニ","ち","チ","し","シ","き","キ","り","リ","ぴ","ピ","ひ","ヒ","ぢ","ヂ","じ","ジ","ぎ","ギ"]

    l_target_small_sounds = list(dict_target_small_sounds.keys())
    for small_sound in l_target_small_sounds:
        if small_sound in text:
            text = fix_youon_convertion(text,small_sound,dict_target_small_sounds,l_youon_pre_characters)
    return text

def fix_youon_convertion(text,target_small_sound,dict_convert,l_youon_pre_characters):
    '''拗音の前に位置し得ない文字列が拗音の前にあった場合、小さい文字を大きくして返す処理'''
    
    for re_result in re.finditer(target_small_sound,text):      
        pre_character_index = re_result.span()[0]-1
        pre_character=text[pre_character_index]
        if pre_character_index>=0 and pre_character in l_youon_pre_characters:
            continue
        else:
            text = text[:pre_character_index+1]+dict_convert[target_small_sound]+text[pre_character_index+2:]

    return text

def judge_part_of_speech_is_surname(l_part_of_speech):
    '''part_of_speechをコンマでsplitしたlistを受け、それが姓の部分に該当するかを
    判定する処理'''

    return l_part_of_speech[2]=="人名" and (l_part_of_speech[3]=="姓" or l_part_of_speech[3]=="性")

def wakati(text):
    '''
    人名っぽい部分を取り出す関数
    input:テキスト
    output:(姓,名)
    '''
    sei,mei = "",""
    for token in name_tokenizer.tokenize(text):
        if judge_part_of_speech_is_surname(token.part_of_speech.split(",")):
            sei+=token.surface
        if token.part_of_speech.split(",")[2]=="人名" and token.part_of_speech.split(",")[3]=="名":
            mei+=token.surface
    return sei, mei

# def kana_name(text):
#     '''
#     漢字氏名をカタカナにする
#     '''
#     if text:
#         tagger = MeCab.Tagger("-Ochasen")
#         tagger.parse('')
#         node = tagger.parseToNode(text)
#         word_class = []
#         while node:
#             wclass = node.feature.split(',')
#             if wclass[0] != u'BOS/EOS':
#                 if wclass[6] == None:
#                     word_class.append((wclass[7]))
#                 else:
#                     word_class.append((wclass[7]))
#             node = node.next
#         mojiretsu=''.join(word_class) #性と名の間で半角空白を開ける
#         return zen2han(mojiretsu)
#     else:
#         return

def kana_name(text):
    ''' 漢字氏名をカタカナにする'''
    
    if text =='XXX':
        return 'XXX'
        
    tokens = name_tokenizer.tokenize(text)
    answer=""
    for token in tokens:
        answer=answer+token.reading
    answer = answer.replace('*','')

    return zen2han(answer)



def zen2han(text):
    '''
    全角を半角に
    input:text（全角カタカナ）
    output:text（半角カタカナ）
    '''
    result=jaconv.z2h(text.replace("　"," "))
    return (result)
    
#---------------------------------------------------------------------------------
#性別

kakasi = kakasi()

def kata2gender(text):
    '''
    カタカナの氏名から性別を推定する関数
    output:男なら1、女なら2
    '''
    text1=jp2rome(text)
    f = open(os.path.join(ROOT_DIR,'DB_module_pickles/my_classifier.pickle'), 'rb')
    classifier = pickle.load(f)
    f.close()
    if classifier.classify(feature_extraction(text1))=="female":
        return "2"
    else:
        return "1"

def jp2rome(text):
    '''
    カタカナをローマ字に
    input:text（カタカナ）
    output:text（アルファベット）
    '''
    #kakasi.setMode("H", "a")  # Hiragana to ascii
    kakasi.setMode("K", "a")  # Katakana to ascii
    #kakasi.setMode("J", "a")  # Japanese(kanji) to ascii
    #kakasi.setMode("r", "Hepburn")  # Use Hepburn romanization

    conv = kakasi.getConverter()
    result = conv.do(text)
    return (result)

def feature_extraction(word):
    '''後ろ3文字を取り出す関数'''

    return {"lastcharacter":word[-3:]}
    
#---------------------------------------------------------------------------------
#保険者番号周り
def get_num_using_checkDigit(l_input_str_raw,search_type='hokensha_num',l_permitted_len=[6,8],regex_num_patch = [('O','0'),('o','0'),('l','1'),('i','1')]):
    '''保険者番号のOCR結果stringを受け取り、そこから確からしい保険者番号を返す処理'''
    #現状はcheckdigitをクリアした保険者番号が複数存在する場合のconfidence分けができておらず、
    #各数値のconfidence等を通して今後ここを精緻化 or 枠を薄くする, 処理を入れる
    
    #文字列の重複の可能性を考慮しつつ、生の文字列を生成する  
    def judge_overlap(former_str,latter_str):
        '''2つのstringのtail, headに重複があるかを判定し、ある場合はTrue, 及びその重複の文字列長を
        返す処理'''

        overLap,cnt = False,None
        for i in range(len(former_str)+1):
            lookup_num = i+1
            sliced = former_str[-lookup_num:]
            if re.match(re.escape(sliced),re.escape(latter_str)) is not None:
                overLap = True
                cnt = lookup_num
        return overLap,cnt
    
    def acquire_confident_nums(l_concat_str):
        #生のstringから数値のみを取得する
        l_num_only_str,l_of_l_index_ones = [],[]
        for concat_str in l_concat_str:
            num_only_str = ''
            l_index_ones,cnt_index = [],0
            for result in re.finditer(r'[0-9]',concat_str):
                str_ = result.group()
                num_only_str+=str_
                if str_=='1':
                    l_index_ones.append(cnt_index)
                cnt_index+=1
                
            l_num_only_str.append(num_only_str)
            l_of_l_index_ones.append(l_index_ones)
                
        #文字列長, checkdigitを用いて, 確からしい保険者番号を取得する
        for num_only_str,l_index_ones in zip(l_num_only_str,l_of_l_index_ones):
            for i in range(len(l_index_ones)+1):
                if (len(num_only_str)-i) not in l_permitted_len:
                    continue

                else:
                    for tuple_indexes in itertools.combinations(l_index_ones,i):
                        num_only_str_inEdit = num_only_str[:]
                        for index in tuple_indexes:
                            num_only_str_inEdit = num_only_str_inEdit[0:index] + 'X' + num_only_str_inEdit[index+1:len(num_only_str_inEdit)]
                        num_only_str_inEdit = re.sub('X','',num_only_str_inEdit)
                        
                        if checkdigit(num_only_str_inEdit):
                            if num_only_str_inEdit not in l_confident_hokenshaBangou:
                                l_confident_hokenshaBangou.append(num_only_str_inEdit)
        
        return l_confident_hokenshaBangou

    def assert_hokensha_num(l_hokensha_candidates,dict_=insurance_bylaw_header):
        '''XXXX'''

        l_headers = list(dict_.keys())
        l_out = l_hokensha_candidates[:]
        for candidate in l_hokensha_candidates:
            if len(candidate)!=6 and candidate[:2] not in l_headers:
                print(candidate,'was removed') ##DEBUG PRINT
                l_out.remove(candidate)
        return l_out

    def assert_kouhi_num(l_kouhi_candidates,dict_=kouhi_bylaw_header):
        '''XXXX'''

        l_headers = list(dict_.keys())
        l_out,tmp = [],[]
        for candidate in l_kouhi_candidates:
            if candidate[:2] in l_headers:
                l_out.append(candidate)
            else:
                tmp.append(candidate)
        l_out.extend(tmp)
        return l_out

    #initialize return
    l_confident_hokenshaBangou = []
    
    #normalize
    l_input_str = []
    for list_ in l_input_str_raw:
        l_conved = []
        for str_ in list_:
            l_conved.extend(str_.split(' '))
            #文字列内にspaceが存在した場合、そこは2つのlistへと分割する
        l_input_str.append(l_conved)

    #前後のlistのoverlapを判定する
    l_overlap_results = []
    for i in range(len(l_input_str)):
        list_ = l_input_str[i]
        for j in range(len(list_)-1):
            overLap_there, len_overLap = judge_overlap(list_[j],list_[j+1])
            if overLap_there:
                l_overlap_results.append((i,j,j+1,len_overLap))

    l_concat_str = []
    for i in range(len(l_overlap_results)+1):
        l_input_str_inEdit = l_input_str[:]
        for tuple_overlaps in itertools.combinations(l_overlap_results,i):

            for overlap in tuple_overlaps:
                list_index,edit_str_index,_,overlap_len = overlap
                edit_str = l_input_str_inEdit[list_index][edit_str_index][:]
                l_input_str_inEdit[list_index][edit_str_index] = edit_str[:-overlap_len]

            concat_str = ''
            for list_ in l_input_str_inEdit:
                for val in list_:
                    concat_str+=val
          
        for patch_tuple in regex_num_patch:    
            concat_str = re.sub(patch_tuple[0],patch_tuple[1],concat_str)
        l_concat_str.append(concat_str)

    l_confident_hokenshaBangou = acquire_confident_nums(l_concat_str)

    #ここまでで一つも確からしい数値が存在しなかった場合、list単位での単純な判定を最後に行う
    for list_ in l_input_str_raw:
        str_input = ''
        for str_ in list_:
            str_input+=str_
        l_confident_hokenshaBangou = acquire_confident_nums([str_input])
        if len(l_confident_hokenshaBangou)>0:
            break

    #保険者番号については、法別番号の判定を行う
    if search_type=='hokensha_num':
        l_confident_hokenshaBangou = assert_hokensha_num(l_confident_hokenshaBangou[:])
    elif search_type=='kouhi_num':
        l_confident_hokenshaBangou = assert_kouhi_num(l_confident_hokenshaBangou[:])
    else:
        raise ValueError('unsupported search type was inputed.')

    #一つも確からしい数値が存在しなかった場合は、XXXを返す
    if len(l_confident_hokenshaBangou)==0:
        l_confident_hokenshaBangou = ['XXX']
        confidence = 0

    #confidenceを判定する
    elif len(l_confident_hokenshaBangou)==1:
        confidence = 1
    else:
        confidence = 0

    return l_confident_hokenshaBangou, confidence

    
def checkdigit(num):
    '''stringとしての数値の配列を受け取り、それがcheckdigitを満たしているかを判定する処理'''

    def over10(n):
        if n>9:
            n=n//10+n%10
        return n
    
    num_list=[int(x) for x in list(str(num))]
    if len(num_list)%2!=0:
        odd_num = [n*2 for n in num_list[1::2]]#奇数indexは二倍
        odd_num=[over10(n) for n in odd_num]
        even_num = num_list[0::2][:-1]#偶数idexはそのまま
        result=10-(sum(odd_num)+sum(even_num))%10

    else:
        even_num = [n*2 for n in num_list[0::2]]#奇数indexは二倍
        even_num=[over10(n) for n in even_num]
        odd_num = num_list[1::2][:-1]#偶数indexはそのまま
        result=10-(sum(odd_num)+sum(even_num))%10
    
    if result==10:
        result=0
    
    return (result == int(num[-1]))

def get_kouhi_hokensha_nums(input_raw):
    '''処方箋上部bandの生OCR結果を受け、そこから保険者番号, 記号・番号,
    公費負担者番号, 公費負担医療の受給者番号を返す処理'''
        
    def get_num_upto_kanji(input_,stop_key):
        '''inputのlistをforward lookupしていき、数値が開始してから漢字/カタカナ/ひらがな
        が出てくるまでを返す処理. stop_keyの文字列が出現してもbreakする'''
    
        input_inEdit = copy.deepcopy(input_)
    
        p_kanji = regex.compile(r'\p{Script=Han}+')
        p_katakana = re.compile('[\u30A1-\u30FF]+')
        p_hiragana = re.compile('[\u3041-\u309F]+')
        p_alphabet = re.compile('[a-zA-Zａ-ｚＡ-Ｚ]+')
            
        num_found, search_end,cnt = False, False,0
        l_str_out = []
        while search_end==False:
            l_append = []
            list_ = input_inEdit[0][cnt]
            for i in range(len(list_)):
                str_,str_raw = [list_[i]]*2
                
                if stop_key in str_:
                    break
                if search_end:
                    break
                
                num_start_index = 0
                search_num = re.search('[0-9]',str_)
                if search_num is not None:
                    num_start_index = search_num.span()[0]
                    num_found = True
                
                start_index_remove = len(str_raw)
                if num_found:
                    str_ = str_[num_start_index:]
                    l_search = p_kanji.search(str_),p_katakana.search(str_),p_hiragana.search(str_),p_alphabet.search(str_)
                    if l_search.count(None)==len(l_search):
                        l_append.append(str_)
                    else:
                        l_spans = []
                        for search in l_search:
                            if search is not None:
                                l_spans.append(search.span()[0])
                        start_index = min(l_spans)
                        start_index_remove = start_index+num_start_index
                        str_ = str_[:start_index]
                        l_append.append(str_)
                        search_end = True
                list_[i] = re.sub(re.escape(str_raw[:start_index_remove]),'',list_[i][:])
                
            l_str_out.append(l_append)
            cnt+=1
            
            if stop_key in str_:
                break
            if cnt>=len(input_inEdit[0]):
                break
        
        l_str_out_clensed = []
        for list_ in l_str_out:
            list_for_check_empty = [i for i in list_ if i!='']
            if len(list_)==0:
                continue
            elif len(list_for_check_empty)==0:
                continue            
            l_str_out_clensed.append(list_)
        if len(l_str_out_clensed)==0:
            l_str_out_clensed = [[]]

        return l_str_out_clensed,input_inEdit
    
    #initialize
    input_ = []
    for list_ in input_raw:
        l_append = []
        for str_ in list_:
            l_append.extend(str_.split(' '))
        input_.append(l_append)
        
    input_ = [copy.deepcopy(input_)]

    #公費負担者番号の取得
    input_ = word_check_list2(input_,'公費')
    l_kouhi_num_str, input_ = get_num_upto_kanji(input_,stop_key='保険')
    l_kouhi_num_str, kouhi_confidence = get_num_using_checkDigit(l_kouhi_num_str,search_type='kouhi_num',l_permitted_len=[8])

    #保険者番号の取得
    input_ = word_check_list2(input_,'保険')
    l_hokensha_num_str, input_ = get_num_upto_kanji(input_,stop_key='公費')
    l_hokensha_num_str, hokensha_confidence = get_num_using_checkDigit(l_hokensha_num_str,search_type='hokensha_num',l_permitted_len=[6,8])

    #公費負担医療の受給者番号の取得
    input_ = word_check_list2(input_,'公費')
    l_kouhi_jukyuusha_num_str, input_ = get_num_upto_kanji(input_,stop_key='保険')
    l_kouhi_jukyuusha_num_str, jukyuusha_confidence = get_num_using_checkDigit(l_kouhi_jukyuusha_num_str,search_type='kouhi_num',l_permitted_len=[7])

    #保険者の記号・番号の取得
    input_ = word_check_list2(input_,'公費')
    l_kigou_bangou_str, _ = get_num_upto_kanji(input_,stop_key='医療')
    l_kigou_bangou_str = symbol_number(l_kigou_bangou_str)
    kigou_confidence, bangou_confidence = None, None
    
    #返り値の成形
    l_numbers = [l_kouhi_num_str, l_hokensha_num_str,l_kouhi_jukyuusha_num_str,l_kigou_bangou_str]
    l_confidence = [kouhi_confidence, hokensha_confidence, jukyuusha_confidence, kigou_confidence, bangou_confidence]

    return l_numbers, l_confidence

#---------------------------------------------------------------------------------
#記号番号周り

def symbol_number(l_input_str_raw, connector_candidates=['·','•','・',r'.'],connector_candidates_sub=['-']):
    '''記号番号領域のOCR結果を入力として、記号, 番号を返す処理'''
    #記号と番号の境界を示す文字がそもそもOCR出来ていないケースに本関数のみでは対処できず、
    #処方箋全体をOCRした文字列を併用するなどが、今後考えられる
    
    concat_str = ''

    #入力のlistに分かれがあった場合、文字列内にconnector候補がない場合は、その分かれにdividerを入れる
    
    ##connectorの有無を判別する
    connector_found = False
    insert_index_1, insert_index_2 = -1, -1
    for list_ in l_input_str_raw:
        for val in list_:
            for connector in connector_candidates+connector_candidates_sub:
                if connector in val:
                    connector_found=True
                    break

    ##connectorは無いもののlist内に分断が存在した場合は、そこにconnectorを挿入する
    concat_str = ''
    inserted = False
    for list_ in l_input_str_raw:
        for val in list_:
            if connector_found==False and inserted==False:            
                concat_str = concat_str+val+connector_candidates[0]
                inserted = True
            else:
                concat_str += val

    concat_str = re.sub(' ','',concat_str)
    concat_str = concat_str.strip('|')
    l_symbols, connector_found = [concat_str], False

    #まずは確実に記号番号を分かつ値であるものをsearchする
    for connector in connector_candidates:
        if connector in concat_str:
            l_symbols = concat_str.split(connector)
            connector_found = True

    #次に、記号の一部出会った可能性のある分かち値をsearchする
    if connector_found==False:
        for connector in connector_candidates_sub:
            if connector in concat_str:
                l_symbols = concat_str.split(connector)            
    
    if len(l_symbols)==1:
        kigou, bangou = l_symbols[0],''
    elif len(l_symbols)==2:
        kigou, bangou = l_symbols
    else:
        print('UNEXPECTED FLOW in symbol_num')
        kigou, bangou = 'XXX','XXX'
    
    return kigou, bangou        

#---------------------------------------------------------------------------------
#word_check_list関数群

def name_check_list(text_list):
    '''
    氏名っぽい単語が入っていたら、それ以降を取得（その部分は含む）
    input:リスト内包リスト
    ouotput:リスト内包リスト
    '''
    candidate_list=[]
    for num in range(len(text_list)):
        num_sum=0
        for s in range(len(text_list[num])):
            texts=text_list[num][s]
                
            for i in range(len(texts)):
                if num_sum==0:
                    if ("氏名" in "".join(texts)or"名前" in "".join(texts))and"医氏名" not in "".join(texts):
                        num_sum=1
                        
                        candidate_list.append(text_list[num][s:])


        if num_sum==0:
            candidate_list.append(text_list[num])
            
    return (candidate_list)

def kata_check_list(text_list):
    '''
    仮名氏名っぽい単語（全部カタカナ）が入っていたら、それ以降の5つを取得
    input:リスト内包リスト
    ouotput:リスト内包リスト
    ''' 
    candidate_list=[]
    for num in range(len(text_list)):
        #num=1
        num_sum=0
        for s in range(len(text_list[num])):#処方箋ごとに、、
            candidate1=[]
            candidate2=[]
            candidate3=[]
            candidate4=[]
            candidate5=[]
            texts=text_list[num][s]#処方箋のリストが入っている[[],[]]
            #print(texts)#例:['氏名', '〜〜〜〜', '保険医療']
            for i in range(len(texts)):
                if num_sum==0:
                    if kata(texts[i].replace(" ",""))==True:
                        num_sum=1
                        #print(num)
                        try:
                            candidate1=texts
                        except:
                            pass
                        try:
                            candidate2=text_list[num][s+1]
                        except:
                            pass
                        try:
                            candidate3=text_list[num][s+2]
                        except:
                            pass
                        try:
                            candidate4=text_list[num][s+3]
                        except:
                            pass
                        try:
                            candidate5=text_list[num][s+4]
                        except:
                            pass
                
                        candidate_list.append([candidate1,candidate2,candidate3,candidate4,candidate5])
        if num_sum==0:
            candidate_list.append(text_list[num])
            
    return candidate_list

def word_check_list(text_list, check_word):
    '''[[['1'],['2','3'],['4','5','6']]], といった形式での3次元配列を受け、check_wordが含まれるより後の
    list群を返す処理. check_wordを含むlistは返り値には含まれない'''
    word=check_word
    candidate_list=[]
    for num in range(len(text_list)):
        #num=1
        num_sum=0
        for s in range(len(text_list[num])):

            texts=text_list[num][s]
            if num_sum==0:
                if (word in "".join(texts).replace(" ","")):
                    num_sum=1
                    try:
                        candidate_list.append(text_list[num][s+1:])
                    except:
                        pass


        if num_sum==0:
            candidate_list.append(text_list[num])
            
    return (candidate_list)


def word_check_list_before(text_list, check_word):
    '''
    ある単語を含んでいたら、それより前を全てを取得（その単語は含まない）
    input:リスト内包リスト,検索単語
    output:リスト内包リスト
    '''
    word=check_word
    candidate_list=[]
    for num in range(len(text_list)):
        num_sum=0
        for s in range(len(text_list[num])):
            texts=text_list[num][s]
            if num_sum==0:
                if (word in "".join(texts).replace(" ","")) :
                    num_sum=1

                    candidate_list.append(text_list[num][:s])


        if num_sum==0:
            candidate_list.append(text_list[num])
            
    return (candidate_list)


def word_check_list2(text_list, check_word):
    '''
    ある単語を含んでいたら、それ以降全てを取得（その単語は含む）
    （含まないversionはword_check_list)
    input:リスト内包リスト,検索単語
    output:リスト内包リスト
    '''
    word=check_word
    candidate_list=[]
    for num in range(len(text_list)):
        num_sum=0
        for s in range(len(text_list[num])):
            texts=text_list[num][s]
            if num_sum==0:
                if (word in "".join(texts).replace(" ","")) :
                    num_sum=1

                    candidate_list.append(text_list[num][s:])


        if num_sum==0:
            candidate_list.append(text_list[num])
            
    return (candidate_list)

def date_check_list(text_list):
    '''
    日付っぽい単語が入っていたら、それ以前を取得（その部分は含まない）
    input:リスト内包リスト
    ouotput:リスト内包リスト
    '''    
    candidate_list=[]
    for num in range(len(text_list)):
        num_sum=0
        for s in range(len(text_list[num])):
            texts=text_list[num][s]
            for i in range(len(texts)):
                if num_sum==0:
                    if date_check(texts[i].replace(" ",""))==True :
                        num_sum=1
                        candidate_list.append(text_list[num][:s])

        if num_sum==0:
            candidate_list.append(text_list[num])

    return candidate_list


def date_check(text):
    '''
    日付っぽい表現を発見する関数
    input:テキスト
    ooutput:もしも入っていたらTrue
    '''
    result = re.sub('[0-9]','', text.replace("・",""))
    if ("年月" in result) or ("年月" in result) or ("明大昭" in result) or ("大昭平" in result) or ("明治" in result) or("大正" in result) or("昭和" in result) or("平成" in result):
        return True

#---------------------------------------------------------------------------------
#医療機関名周り

##病院データベースのインポート(subは医科・歯科が併設されているケースの、sub側の医療機関のコードを格納したもの)
print('loading hospital DB and symspell...')
load_dir = os.path.join(ROOT_DIR, 'DB_module_pickles/dict_hospitalInfo.pickle')
with open(load_dir, 'rb') as f:
    dict_hospitalInfo_base = pickle.load(f)

load_dir = os.path.join(ROOT_DIR, 'DB_module_pickles/l_hospital_headers.pickle')
with open(load_dir, 'rb') as f:
    l_hospital_headers = pickle.load(f)

##病院symspell module
hospital_symspell_pickle=os.path.join(ROOT_DIR,'DB_module_pickles/hospital_front15_3_8.pickle')
max_edit_distance_lookup = 3
_head_str_num = int(hospital_symspell_pickle.split('front')[1].split('_')[0])

with open(hospital_symspell_pickle, 'rb') as f:
    sym_spell_hospital = pickle.load(f)

##病院名の表記揺れ修正してdict,listを生成
l_hospital = list(dict_hospitalInfo_base.keys())
l_hospital = [jaconv.normalize(i) for i in l_hospital]
l_hospital_nospace = [re.sub(' ','',i) for i in l_hospital]
dict_hospital_nospace_2_space = dict(zip(l_hospital_nospace,l_hospital))


def hospital_name_search(input_,l_hospital_nospace=l_hospital_nospace,confidence_thresh=0.06):
    '''ocrの生の結果から、病院を名寄せし、病院名・諸コードを返す処理'''
    
    def lookup_dict(hospital_nospace,dict_=dict_hospitalInfo_base,dict_conv=dict_hospital_nospace_2_space):
        '''spaceのない病院文字列をquerryされると、正規の病院名、及びその諸コードを返す処理
        Noneをquerryされた場合、初期値を返す'''
        
        l_keys,l_vals = ['name','code_list'],['XXX',['-1','-1','-1']]
        dict_out = dict(zip(l_keys,l_vals))
        if hospital_nospace is None:
            return dict_out
        
        dict_out['name'] = dict_conv[hospital_nospace]
        dict_out['code_list'] = dict_[dict_conv[hospital_nospace]]
        
        return dict_out.copy()
    
    def init_clense_hospital(list_):
        '''XXXX'''
        
        clensing = [list_]
        clensing = word_check_list(clensing,'記号')
        clensing = word_check_list_before(clensing,'コード')
        
        return clensing[0]

    def clense_val_hospital(str_):
        '''XXXX'''

        str_ = str_.lstrip('医療機関の')
        str_ = str_.split('所在地')[-1]
        str_ = str_.split('名称')[-1]
        str_ = str_.lstrip('名 ')

        return str_
            
    #init clense
    input_ = init_clense_hospital(input_)
    l_split_key = []

    #to string
    input_str = ''
    for list_ in input_:
        for val in list_:
            input_str+=val
            input_str+='\n'
    input_str = input_str[:-1]
    raw_str = input_str.splitlines()
    
    #initialize
    dict_hospital = lookup_dict(None)
    
    #完全一致の有無をcheckする ... 病院が包含関係の際にミスるので、一旦comment out. 
    '''
    input_str_whole = re.sub('[\n| ]','',input_str)
    l_hospital_whole_match,l_leven = [],[]
    for hospital in l_hospital_nospace:
        if hospital in input_str_whole:
            l_hospital_whole_match.append(hospital)
            l_leven.append(L.distance(hospital,input_str_whole))

    if len(l_hospital_whole_match)>0:
        s_hospital = pd.Series(l_hospital_whole_match,index=l_leven)
        l_hospital_sorted = s_hospital[s_hospital.index<=leven_thresh].sort_index(ascending=False).values.tolist()
        dict_hospital = lookup_dict(l_hospital_sorted[-1])
        return dict_hospital
    '''

    #それ以外の場合は、symspellをあてがう
    l_symspell_results,l_levens, l_lens = [],[],[]
    l_base_val = [] ##DEBUG
    raw_str_clensed = [clense_val_hospital(i) for i in raw_str]
    for i in range(len(raw_str_clensed)):

        #do symspell
        str_ = raw_str_clensed[i]
        l_symspell_result,l_leven,l_len = integrate_hospital_symspell(str_)

        #log split key
        if len(l_symspell_result)>0:
            l_split_key.extend([raw_str[i]]*len(l_symspell_result))

        #log result
        l_symspell_results.extend(l_symspell_result)
        l_levens.extend(l_leven)
        l_lens.extend(l_len)
        #l_base_val.extend([str_]*len(l_len)) ##DEBUG
    
    #次に、2行単位で見ていく
    for i in range(len(raw_str_clensed)-1):

        #do symspell
        str_concat = raw_str_clensed[i]+raw_str_clensed[i+1]
        l_symspell_result,l_leven,l_len = integrate_hospital_symspell(str_concat)

        #log split key
        if len(l_symspell_result)>0:
            l_split_key.extend([raw_str[i+1]]*len(l_symspell_result))

        #log result
        l_symspell_results.extend(l_symspell_result)
        l_levens.extend(l_leven)
        l_lens.extend(l_len)
        #l_base_val.extend([str_]*len(l_len)) ##DEBUG

    l_leven_ratio = [10**4]
    if len(l_symspell_results)>0:
        l_leven_ratio = [l_levens[i]/l_lens[i] for i in range(len(l_levens))]

        s_hospital = pd.Series(l_symspell_results,index=l_leven_ratio)
        s_sorted = s_hospital.sort_index(ascending=False)        
        l_hospital_sorted = s_sorted.values.tolist()

        s_split_key = pd.Series(l_split_key,index=l_leven_ratio)
        s_sorted = s_split_key.sort_index(ascending=False)
        l_split_key = s_sorted.values.tolist()

        '''##DEBUG
        s_base_val = pd.Series(l_base_val,index=l_leven_ratio)
        s_sorted = s_base_val.sort_index(ascending=False)
        l_base_val = s_sorted.values.tolist()
        ##'''

        #編集距離が最も短いものを、確定的に返す
        dict_hospital = lookup_dict(l_hospital_sorted[-1])

        #print('base,result,ratio',l_base_val[-1],l_hospital_sorted[-1],min(l_leven_ratio)) ##DEBUG PRINT

    #confidenceを判定する
    if min(l_leven_ratio) < confidence_thresh:
        confidence = 1
    else:
        confidence = 0

    #病院名称以降にocr結果をパースして返せるようにする
    if len(l_split_key)>0:
        key_use = l_split_key[-1].split(' ')[0] ##PATCH
        return_list_input = word_check_list([input_],key_use)
        return_list_input = return_list_input[0]
        hospital_not_found = False
    else:
        return_list_input = copy.deepcopy(input_)
        hospital_not_found = True

    return dict_hospital, return_list_input, confidence, hospital_not_found


def integrate_hospital_symspell(str_,l_hospital_headers=l_hospital_headers,min_len=5,leven_thresh=5,l_header_additional = ['法人','社団']):
    '''生の文字列を受け、それに似ている病院名称及びその生文字列との編集距離・病院名所の長さ、
    を返す処理'''

    #短縮された病院名称も取得する ... 処方箋では正式名称, 厚労省DBでは略称のケースに対応
    l_hospital_headers_comp = l_hospital_headers[:]
    l_hospital_headers.extend(l_header_additional)

    ##まずは素直に外部DBのheaderを検索・削除
    l_strs = [str_[:]]
    for head in l_hospital_headers:
        if head in str_:
            str_ = re.sub(head,'',str_)
    l_strs.append(str_)

    #厚労省DB上は存在しない~~会がある模様なので、そこを落とす
    if '会' in str_[:3]:
        str_ = ''.join(str_.split('会')[1:])
    l_strs.append(str_)

    l_strs = list(set(l_strs))

    #conduct symspell
    l_symspell_result,l_leven,l_len = [],[],[]
    for str_ in l_strs:
        if len(str_)>=min_len:
            str_nospace = re.sub(' ','',str_)
            symspell_results,_ = symspell_hospital(str_nospace)
            for result in symspell_results:
                for hospital_nospace in l_hospital_nospace:
                    if result in hospital_nospace:
                        distance = L.distance(str_nospace,hospital_nospace)
                        if distance<=leven_thresh:
                            l_symspell_result.append(hospital_nospace)
                            l_leven.append(distance)
                            l_len.append(len(hospital_nospace))

    return l_symspell_result[:],l_leven[:],l_len[:]


def symspell_hospital(_query,_max_edit_distance_lookup=max_edit_distance_lookup,sym_spell_hospital=sym_spell_hospital,head_str_num=_head_str_num):
    answer=[]
    answer_distance=[]
    input_term =_query if len(_query)<=head_str_num else _query[:head_str_num]
    _max_edit_distance_lookup = _max_edit_distance_lookup
    suggestion_verbosity = Verbosity.CLOSEST  # TOP, CLOSEST, ALL
    
    suggestions = sym_spell_hospital.lookup(input_term, suggestion_verbosity,
                               _max_edit_distance_lookup)
    for suggestion in suggestions:
        answer.append(suggestion.term)
        answer_distance.append(suggestion.distance)
    return(answer,answer_distance)

#-----------------------------------------------------
#元号, 年月日関連処理群
def get_dates(l_inputs, key_now,l_birthday_keys=['生年'], l_koufunen_keys=['交付']):
    '''対象とするOCR結果のlistを受け、searchの起点となるkeyをもとに、患者誕生日・交付年月日を
    searchして返す処理'''
    
    #input_strを展開する
    input_str = ''
    for input_ in l_inputs:
        for list_ in input_:
            for val in list_:
                input_str+=val
            input_str+='\n'
    input_str = input_str[:-1]
    raw_str = input_str.splitlines()

    #initialize
    _13_patient_birthday,_51_prescription_date = 'XXX','XXX'
    _13_patient_birthday_visible, _51_prescription_date_visible = 'XXX','XXX'
    _13_found, _51_found = False, False
    prescription_in_time = None
    confidence = 0

    for num in range(len(raw_str)):
        val = raw_str[num]
        if _13_found==False and key_now=='_13_':
            for birth_key in l_birthday_keys:
                if birth_key in val:
                    _13_patient_birthday, _13_patient_birthday_visible,_13_found, is_seireki, confidence = search_YMD(raw_str,num,key_now=key_now)

                    #未来の日付を取得してしまっていた場合は、re-initialize
                    is_past = check_is_past(_13_patient_birthday,is_seireki)
                    if is_past is None:
                        print('birthday YMD was not acquired') ##DEBUG PRINT
                        pass
                    elif check_is_past(_13_patient_birthday,is_seireki)==False:
                        print('obtained future birthday') ##DEBUG PRINT
                        _13_patient_birthday,_13_patient_birthday_visible, _13_found = 'XXX','XXX',False

        if _51_found==False and key_now=='_51_':
            for koufu_key in l_koufunen_keys:
                if koufu_key in val:
                    _51_prescription_date, _51_prescription_date_visible,_51_found, is_seireki, confidence = search_YMD(raw_str,num,key_now=key_now)

                    #未来の日付を取得してしまっていた場合は、re-initialize
                    is_past = check_is_past(_51_prescription_date,is_seireki)
                    if is_past is None:
                        print('koufu-day YMD was not acquired') ##DEBUG PRINT
                        pass
                    elif check_is_past(_13_patient_birthday,is_seireki)==False:
                        print('obtained future koufu-day') ##DEBUG PRINT
                        _51_prescription_date, _51_prescription_date_visible, _51_found = 'XXX','XXX',False

                    #最後に処方箋の期限切れを判定する
                    if _51_found:
                        prescription_in_time = check_prescription_expiration(_51_prescription_date,is_seireki)

                    ##DEBUG PRINTS
                    if prescription_in_time is None:
                        print('koufu YMD was not acquired')
                    elif prescription_in_time==False:
                        print('prescription is Expired',_51_prescription_date)

        
    return _13_patient_birthday,_13_patient_birthday_visible,_51_prescription_date,_51_prescription_date_visible, prescription_in_time, confidence

def search_YMD(raw_str,num, key_now,search_limit=10, dict_gengou_ids=_dict_gengou_ids):
    '''行ごとにsplitlineされたraw_str, search起点となるindex, を受け, 直近の
    元号・年月日をsearchして返す処理'''
    
    def estimate_gengou(year_str, threshold_year=15):
        '''患者の生年を入力とし、その元号を推定する処理'''
        #現状は昭和15年以前生まれの人は十分に少ないという前提のもと、15年を閾値に設定
        #memo: 西暦での処方箋にも念の為対応しておくと吉

        year_int = int(year_str.strip('年').strip('/'))
        if year_int<threshold_year:
            return '平成'
        else:
            return '昭和'

    def search_initial(search_key,val_input):
        '''search_keyにて特徴づけられる正規表現で日付をsearchし、その結果更新されるval_nxtを
        返す処理'''

        found = False
        search_result = re.search(r'([0-9, ]+)'+search_key,val_input)
        if search_result is not None:
            val_input = val_input.split(search_result.group())[1]
            found = True
        return search_result, val_input, found

    def check_date_existence(year_re,month_re,date_re,l_nishimuku_months=[2,4,6,9,11]):
        '''YMDが実在する日付かを判定する処理'''
        #年については、本来は元号から判別すべきだが、そこは未対応
        
        l_dates = [year_re.group(), month_re.group(), date_re.group()]
        year_int, month_int, date_int = [int(re.sub('[年|月|日|/]','',i)) for i in l_dates]
        
        if month_int in l_nishimuku_months:
            if month_int==2:
                if date_int>29:
                    return False
            else:
                if date_int>30:
                    return False
        else:
            if date_int>31:
                return False

        return True

    #元号のlistを取得
    l_gengou = list(dict_gengou_ids.keys())

    #year, month, dateの検索結果格納変数・検索行数count変数の定義
    target_year,target_month,target_date,cnt = None,None,None,0
    gengou_found = False    
    confidence = 1
    
    #year,month,dateすべてが検索完了 or countが一定数overまで検索を行う
    while ((target_year is None) or (target_month is None) or (target_date is None)) and cnt<search_limit:

        #indexがoverflowの場合はbreakする
        if num+cnt>=(len(raw_str)):
            break
        
        val_nxt = raw_str[num+cnt]

        #元号の文字列をsearchする
        if gengou_found==False:
            for gengou_candidate in l_gengou:
                if gengou_candidate in val_nxt:
                    gengou = gengou_candidate
                    gengou_found = True

        #まず、年>月>日の順で取得精度が高いという前提のもと、正規表現にて年月日を取得する
        year_found_now, month_found_now, date_found_now = False, False, False
        if target_year is None:
            target_year, val_nxt, year_found_now = search_initial(r'(年|/)',val_nxt)
        if target_month is None:
            target_month, val_nxt, month_found_now = search_initial(r'(月|/)',val_nxt)
        if target_date is None:
            target_date, val_nxt, date_found_now = search_initial(r'(日|/)',val_nxt)

        #次に、年月日のうち2つの値が見つかった場合、val_nxt内の残りの数値をあてがう
        l_founds, num_found = [year_found_now, month_found_now, date_found_now], False
        if len([i for i in l_founds if i==True])==2:
            target_num, _, num_found = search_initial('', val_nxt)
            confidence = 0

        #見つかった数値にて定義される日付が実在するかを、チェックしつつ、日付を更新する
        if num_found:
            if target_year is None:
                print('target year was acquired but not compatible now')
                ''' #元号からの年月日存在判定をしないと潜在エラーなため、ここはいったんコメントアウト
                if check_date_existence(target_num, target_month, target_date):
                    target_year = target_num
                '''
                pass
            elif target_month is None:
                if check_date_existence(target_year, target_num, target_date):
                    target_month = target_num
            elif target_date is None:
                if check_date_existence(target_year, target_month, target_num):
                    target_date = target_num            

        cnt+=1

    if (target_year is None) or (target_month is None) or (target_date is None):
        print(target_year,target_month,target_date,'YMD is XXX')
        return 'XXX','XXX',False,False,0
    else:
        y,m,d = target_year.group(),target_month.group(),target_date.group()
        y,m,d = re.sub(' ','',y),re.sub(' ','',m),re.sub(' ','',d)
        if gengou_found==False:
            confidence = 0
            if key_now=='_13_':
                gengou = estimate_gengou(y)
            elif key_now=='_51_':
                gengou = '令和'
            else:
                gengou = '昭和'
                print('UNEXPECTED KEY to gengou estimation')

    year_str, is_seireki = assert_digit_nums(y)
    month_str, _ = assert_digit_nums(m)
    day_str, _ = assert_digit_nums(d)
    if is_seireki:
        gengou_str = ''
    else:
        gengou_str = dict_gengou_ids[gengou]
    JAHIS_YMD = gengou_str+year_str+month_str+day_str

    visible_YMD = year_str+'年'+ month_str + '月' + day_str + '日'
    if not is_seireki:
        visible_YMD = gengou + visible_YMD

    return JAHIS_YMD, visible_YMD,True,is_seireki, confidence

def assert_digit_nums(num_txt):
    '''数値のstringを受け、それが2桁 or 4桁になるように変換して返す処理'''
    
    num_txt = re.sub('[年|月|日|/]','',num_txt)
    if len(num_txt)==1:
        return '0'+num_txt,False
    elif len(num_txt)==4:
        return num_txt, True
    else:
        return num_txt, False

def check_prescription_expiration(JAHIS_YMD, is_seireki,expiration_days=4):
    '''処方箋が使用期限内か否かを判定する処理'''
    #2020年10月24日現在のリサーチでは、処方箋の使用期限は交付されたその日を含め4日
        
    if JAHIS_YMD == 'XXX':
        return None
    deadline_date =  convert_JAHIS_to_datetime(JAHIS_YMD,is_seireki)+ dt.timedelta(days=(expiration_days-1))
    return dt.date.today()<=deadline_date

def check_is_past(JAHIS_YMD,is_seireki):
    '''JAHIS文字列で定義された日付が過去のものであることを確認する処理'''

    if JAHIS_YMD == 'XXX':
        return None
    return convert_JAHIS_to_datetime(JAHIS_YMD,is_seireki)<=dt.date.today()

def convert_JAHIS_to_datetime(JAHIS_YMD,is_seireki,dict_gengou_ids=_dict_gengou_ids, dict_era_start=_dict_era_start):
    '''JAHIS規格で定義された日付文字列を、datetime.date()形式に変換する処理'''
                
    def inverse_lookup(d, x):
        '''辞書の値からkeyを取得する処理'''
        for k,v in d.items():
            if x == v:
                return k

    if is_seireki:
        year_info,month_info,date_info = JAHIS_YMD[:4], JAHIS_YMD[4:6], JAHIS_YMD[6:8]
        year_int = int(year_info)

    else:
        gengou,year_info,month_info,date_info = JAHIS_YMD[:1],JAHIS_YMD[1:3],JAHIS_YMD[3:5],JAHIS_YMD[5:7]
        year_int = dict_era_start[inverse_lookup(dict_gengou_ids, gengou)] + int(year_info) - 1

    month_int = int(month_info)
    date_int = int(date_info)
    
    return dt.date(year_int,month_int,date_int)
