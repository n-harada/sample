#coding:utf-8
import base64
import os
import zipfile
import cv2
import numpy as np
from django.core.files.base import ContentFile
from config.custom_storages import TemporaryStorage


# harada
def recieve_and_save_file_storage(file_, save_file_name, upload_dir='./uploads/prescription_images'):
    '''フロントよりfile_storage形式の入力を受け取り, それをupload_dirに保存しつつ、
    画像をnp.arrayにて読み込む処理'''

    filename = save_file_name + ".jpeg"
    save_dir = os.path.join('images/prescription_images', filename)
    storage = TemporaryStorage()
    image_path = storage.save(save_dir, ContentFile(file_.read()))
    image = path_to_array(image_path)
    storage.delete(image_path)  # cv2で読み取ったらすぐ削除
    return image


def unzip_folder(folder, out_dir):
    '''zip形式のfolderのディレクトリを受け、out_dirの中にその解凍結果を
    保存する処理'''

    with zipfile.ZipFile(folder) as existing_zip:
        existing_zip.extractall(out_dir)    

    return True


def decode_image_from_base64txt(target_file,save_image=False,upload_dir='None',save_image_name='None'):
    '''base64情報のうち、純粋な画像情報の部分をtxt化したfile dirを受け
    それをBGRのnp.arrayの形にdecodeして返す処理'''

    #read file
    with open(target_file, 'rb') as f:
        img_base64 = f.read()
    
    #バイナリデータ <- base64でエンコードされたデータ
    img_binary = base64.b64decode(img_base64)
    jpg=np.frombuffer(img_binary,dtype=np.uint8)

    #raw image <- jpg
    img = cv2.imdecode(jpg, cv2.IMREAD_COLOR)

    #画像を保存する場合
    if save_image:
        save_dir = os.path.join(upload_dir,save_image_name)
        cv2.imwrite(save_dir,img)

    return img

def path_to_array(img_path):
    '''画像pathを画像arrayに変換する処理'''
    
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img
