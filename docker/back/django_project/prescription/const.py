QR_image_base_url = 'images/QR_image/'
Pescription_image_base_url = 'images/prescription_image/'

OCR_ERROR_LABEL_TYPE = (
    ("name", "名前"),
    ("kana", "かな"),
    ("birth", "誕生日"),
    ("num", "数字"),
    ("kigo", "記号"),
    ("hakkobi", "発行日"),
    ("gender", "性別"),
    ("iryokikan", "医療機関"),
    ("iyaku", "医療区"),
    ("yoho", "用法"),
    ("no-qr", "読み取りエラー"),
)

OCR_ERROR_LABEL_TYPE_LIST = list(map(lambda x:x[0], OCR_ERROR_LABEL_TYPE))
