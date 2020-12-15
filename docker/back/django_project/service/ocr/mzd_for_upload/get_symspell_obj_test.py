from symspellpy.symspellpy import SymSpell, Verbosity
import jaconv
import re

def get_symspell_obj_simple(max_edit_distance_dictionary,prefix_length,l_med_raw,txt_name):
    l = [jaconv.normalize(i) for i in l_med_raw]
    
    '''
    #2行に対応できる文字列を追加
    l_company_removed = list(set([i.split('「')[0] for i in l]))
    l_company_removed = list(set([i.split('(')[0] for i in l_company_removed]))
    
    l_company_numbers_removed = [re.sub('[0-9]+','___',i) for i in l_company_removed]
    l_company_numbers_removed = list(set([i.split('___')[0] for i in l_company_numbers_removed]))
    
    l.extend(l_company_numbers_removed[:])
    '''
    
    l_re_re = l[:]
        
    #l_re_reリストの中身をsymspellの求める形の文字列にする。
    maped_list = map(str, l_re_re) #格納される数値を文字列にする
    mojiretsu = ' 1\n'.join(maped_list)

    with open(txt_name, mode="w") as f:
        f.write(mojiretsu)
        
    ## できた辞書を元にindexを作る。ここはかなり時間かかる。
    # create object
    sym_spell = SymSpell(max_edit_distance_dictionary, prefix_length)
    # load dictionary
    # dictionary_path = pkg_resources.resource_filename(
    #     "symspellpy", "frequency_dictionary_en_82_765.txt")
    dictionary_path =txt_name
    sym_spell.load_dictionary(dictionary_path, term_index=0,count_index=1)
    
    return sym_spell

def get_symspell_obj_full(max_edit_distance_dictionary,prefix_length,l_med_raw,txt_name):
    l = [jaconv.normalize(i) for i in l_med_raw]
    
    
    #2行に対応できる文字列を追加
    l_company_removed = list(set([i.split('「')[0] for i in l]))
    l_company_removed = list(set([i.split('(')[0] for i in l_company_removed]))
    
    l_company_numbers_removed = [re.sub('[0-9]+','___',i) for i in l_company_removed]
    l_company_numbers_removed = list(set([i.split('___')[0] for i in l_company_numbers_removed]))
    
    l.extend(l_company_numbers_removed[:])
    
    l_re_re = l[:]
        
    #l_re_reリストの中身をsymspellの求める形の文字列にする。
    maped_list = map(str, l_re_re) #格納される数値を文字列にする
    mojiretsu = ' 1\n'.join(maped_list)

    with open(txt_name, mode="w") as f:
        f.write(mojiretsu)
        
    ## できた辞書を元にindexを作る。ここはかなり時間かかる。
    # create object
    sym_spell = SymSpell(max_edit_distance_dictionary, prefix_length)
    # load dictionary
    # dictionary_path = pkg_resources.resource_filename(
    #     "symspellpy", "frequency_dictionary_en_82_765.txt")
    dictionary_path =txt_name
    sym_spell.load_dictionary(dictionary_path, term_index=0,count_index=1)
    
    return sym_spell