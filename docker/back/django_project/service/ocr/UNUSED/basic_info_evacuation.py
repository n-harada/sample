def insurance_num(text_list):
    
    text=""
    for i in text_list:
        text=text+"".join(i)
        text=re.sub(r'\D', '', text)
        if len(text)>8:
            num=len(text)-8
            text=text[:3]+text[3:].replace("1","",num)
        if len(text)==7:
            text=text[:3]+text[3:].replace("1","",1)
    return text

def symbol_number(text_list,num):
    '''
    記号番号を取得する関数
    input:リスト内包リスト,num（保険者番号）より後ろを取得
    output:記号・番号,記号,番号
    '''
    text_list=[text_list]
    text_list=word_check_list_before(text_list,"所在地")
    text_list=word_check_list_before(text_list,"電話番号")
    text_list=word_check_list_before(text_list,"保険医療")
    text_list=word_check_list_before(text_list,"医療機")
    text_list=word_check_list_before(text_list,"〒")
    text_list=word_check_list_before(text_list,"東京都")
    text_list=word_check_list_before(text_list,"町")
    text_list=word_check_list_before(text_list,"区")
    text_list=word_check_list(text_list,"険者番号")
    text_list=word_check_list2(text_list,"被保険")

    #info_list=[]
    sum_=0
    for i in text_list:
        #print(i)
        word_list=["-".join(s) for s in i]#.replace("・","-").replace(".","-")
        word_list2=("-".join(word_list))
        word_list3=word_list2.replace("・","-").replace(".","-").replace("•","-")
        word_list4=word_list3.split("-")
        word_list5=[]
        for word in word_list4:
            if word.count(' ')==1:
                word_list5.append(word.split(" ")[0])
                word_list5.append(word.split(" ")[1])
            else:
                word_list5.append(word)
        #print(word_list5)
        sum_+=1
    #     for word in word_list5:
            
    #         print(re.sub('[^0-9]','',word))
        word_list6 = [re.sub('[^0-9]', '', word) for word in word_list5]
        try:
            answer = re.sub('-+', '-', "-".join(word_list6).strip("-")).split(num)[1]
        except:
            answer = re.sub('-+', '-', "-".join(word_list6).strip("-"))
        
        return answer,symbol_number_split(answer)[0],symbol_number_split(answer)[1]

def symbol_number_split(text):
    '''
    記号番号を-で分割する。
    input:text
    ooutput:記号,番号
    '''
    if len(text.split("-"))>2:
        _23_insurance_card_id="".join(text.split("-")[:2])
        _23_insurance_card_num="".join(text.split("-")[2:])
        
    if len(text.split("-"))==2:
        _23_insurance_card_id=text.split("-")[0]
        _23_insurance_card_num=text.split("-")[1]
    
    if len(text.split("-"))==1:
        try:
            _23_insurance_card_id=text[:4]
            _23_insurance_card_num=text[4:]
        except:
            _23_insurance_card_id = text
    return _23_insurance_card_id,_23_insurance_card_num


def hospital_name(text_list):
    '''
    医療機関名称を取得する
    input:リスト内包リスト
    output:text
    '''
    text_list=[text_list]
    text_list=word_check_list_before(text_list,"話番号")
    text_list=word_check_list2(text_list,"所在地")
    text_list=word_check_list2(text_list,"及び名称")
    text_list=word_check_list(text_list,"記号・番号")
    text_list=word_check_list_before(text_list,"都道府県")
    text_list=word_check_list_before(text_list,"保険医氏名")
    hos_list=[]
    for text in text_list:
        t_list=[]
        for t in text:
            t_list.extend(t)
            #print(t)
        #print(t_list)
        hos_list.append(t_list)

    for word_list in hos_list:
        result=[]
        #print(word)
        for word in word_list:
            #print("[処理前]")
            #print(word)
            word=text_replace(word)
            if not_hospital(word.replace(" ",""))==True:
                if len(word)>3:
                    #print("[--処理後--]")
                    #print(word)
                    result.append(word)
    answer=""
    for r in result:
        if ("クリニック" in r) or ("病院" in r)or("診療所" in r)or (r[-1]=="科"):
            answer=r
    if answer!="":
        return answer
    else:
        if len(result)==0:
            return ""
        else:
            return result[-1]


def hos_name_search(text):
    '''
    医療機関名を元にDBを検索
    input:text
    output:{"name":text,"code_list":""}
    '''
    #DBになかった時用の値
    code_initial = ['1', '', '13']
    name_initial = text
    #辞書を定義
    hospital_dic={"name":name_initial,"code_list":code_initial}
    if text != "":
        for i in list(dict_hospitalInfo_base.keys()):
            if text in i.replace(" ", ""):
                hospital_dic["name"] = i
                hospital_dic["code_list"] = dict_hospitalInfo_base[i]
    return hospital_dic

def not_hospital(text):
    '''
    医療機関っぽくない単語かどうかを判定する
    input:text
    output:医療機関っぽくない場合はFalseを返す、その他はTrue
    '''
    raw_abc = r'[ぁ-んｦ-ﾟァ-ン0-9Ａ-ＺA-Zａ-ｚa-zàä]+'
    raw_abc2 = r'大?昭?平?令?[0-9]+才'
    matchobj = re.fullmatch(raw_abc, text.replace(" ",""))
    matchobj2 = re.fullmatch(raw_abc2, text.replace(" ",""))
    try:
        answer=matchobj.group()
    except:
        answer=False
        
    try:
        answer2=matchobj2.group()
    except:
        answer2=False
    
    if answer==False and answer2==False:
        return True
    else:
        return False


def text_replace(text):
    '''
    医療機関名称に関係なさそうな文字を削除
    input:text
    output:text
    '''
    text=text.replace(" ","")
    text = text.replace('及び','')
    text = text.replace('名称','')
    text = text.replace('所在地','')
    text = text.replace('関の','')
    text = text.replace('保険医師','')
    text=re.sub('\W+','', text)

    return text