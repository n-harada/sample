#symspellが自己回帰できない場合に用いる情報 ... 現在は自己回帰issueはクリアなため、使用しない
'''
__dictionary_errors_long = 'medicine_errors_7_8.pickle'
__dictionary_errors_short = 'medicine_errors_1_5.pickle'
__l_ambiguous_medicine = 'l_ambiguous_medicine.pickle' #symspellに入れても, なんか変な挙動を返す医薬品list
__l_wrong_medicine_in = 'l_wrong_medicine_in.pickle' #名寄せの結果を間違う医薬品list
__l_wrong_medicine_out = 'l_wrong_medicine_out.pickle' #名寄せの結果を間違った結果の医薬品list
'''

##symspellが自己回帰できない場合に用いる情報の用意 ... 現在は自己回帰issueはクリアなため、使用しない
'''
with open(__dictionary_errors_long,'rb') as f:
    dictionary_errors_long = pickle.load(f)

with open(__dictionary_errors_short,'rb') as f:
    dictionary_errors_short = pickle.load(f)

with open(__l_ambiguous_medicine,'rb') as f:
    l_meds_ambiguous = pickle.load(f)

with open(__l_wrong_medicine_out,'rb') as f:
    l_wrong_medicine_out = pickle.load(f)
    
'''

'''l_meds_ambiguous_head = list(set([i[:3] for i in l_meds_ambiguous]))'''

def use_symspell_scratch():
      '''symspell scratchを使用する際の処理フローを格納した関数
      以下のみでは、変数設定など不十分であることに留意'''

    #scratch symspellに回す必要があるかを判定する
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
