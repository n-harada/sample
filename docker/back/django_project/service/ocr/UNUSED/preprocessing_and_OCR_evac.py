    #保険者番号の枠を切り取り、h-concatしていく処理
    ##以下PHCverのパラメータ       
    img_list=[]
    for i in range(8):
        n=i
        height1=largey-smally
        width1=int(round((largex-smallx)/8))
        difference=int(round((height1-width1)/3))
        difference2=width1//7

        if n<4:
            img3=img_hokensha_nums[smally-height1+3*difference:largey-height1-difference,(smallx+width1*n)+0*difference2:smallx+width1*(n+1)-2*difference2]

        else:
            img3=img_hokensha_nums[smally-height1+3*difference:largey-height1-difference,(largex-width1*(8-n))+0*difference2:largex-width1*(7-n)-2*difference2]
        img_list.append(img3)

    im_h = cv2.hconcat(img_list)

    ##以下矢澤先生verのパラメータ
    img_list2=[]
    for i in range(8):
        n=i
        height1=largey-smally
        width1=int(round((largex-smallx)/8))
        difference=int(round((height1-width1)/3))
        difference2=width1//7

        if n<4:
            img3=img_hokensha_nums[smally-height1+1*difference:largey-height1-difference,(smallx+width1*n)+1*difference2:smallx+width1*(n+1)-0*difference2]

        else:
            img3=img_hokensha_nums[smally-height1+1*difference:largey-height1-difference,(largex-width1*(8-n))+1*difference2:largex-width1*(7-n)-0*difference2]
        img_list2.append(img3)

    im_h2 = cv2.hconcat(img_list2)
