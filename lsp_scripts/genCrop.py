import collections
import os
import numpy as np
import cv2
import cPickle
import scipy.io as sio

test_fn = "data/LSP/train_joints.csv"
test_dl = np.array([l.strip() for l in open(test_fn).readlines()])
data_dir = "data/LSP/images/"

crop = np.zeros((1000, 4)).astype(np.float32)
trainGT = np.zeros((14,2,11000)).astype(np.float32)

for i, line in enumerate(test_dl):
            datum = line.split(',')
            img_fn = '%s%s' % (data_dir, datum[0])
            
            #_/_/_/ xs: read image & joint _/_/_/  
            img = cv2.imread(img_fn)
            joints = np.asarray([int(float(p)) for p in datum[1:]])         

            joints = joints.reshape((len(joints) / 2, 2))
            
            delete = []
            for v in range(len(joints)):
	            if  joints[v,0] < 0 or joints[v,1] < 0 or \
                    joints[v,0] > img.shape[1] or joints[v,1] > img.shape[0]:
		        delete.append(v)

            #_/_/_/ image cropping _/_/_/
            visible_joints = joints.copy()
            visible_joints = np.delete(visible_joints, (delete), axis=0)
            visible_joints = visible_joints.astype(np.int32)
            x, y, w, h = cv2.boundingRect(np.asarray([visible_joints.tolist()]))

            pad_w_r = 1.7
            pad_h_r = 1.7
            x -= (w * pad_w_r - w) / 2
            y -= (h * pad_h_r - h) / 2
            w *= pad_w_r
            h *= pad_h_r

            x, y, w, h = [int(z) for z in [x, y, w, h]]
            x = np.clip(x, 0, img.shape[1] - 1)
            y = np.clip(y, 0, img.shape[0] - 1)
            w = np.clip(w, 1, img.shape[1] - (x + 1))
            h = np.clip(h, 1, img.shape[0] - (y + 1))
            img = img[y:y + h, x:x + w]   

            joints = np.asarray([(j[0] - x, j[1] - y) for j in joints])
            joints = joints.flatten()

            #crop[i,:] = [x,y,w,h]

            #_/_/_/ resize _/_/_/
            orig_h, orig_w, _ = img.shape
            joints[0::2] = joints[0::2] / float(orig_w) * 224
            joints[1::2] = joints[1::2] / float(orig_h) * 224
            '''img = cv2.resize(img, (224, 224),interpolation=cv2.INTER_NEAREST)
            cv2.imwrite('lsptraincrop/'+str(i+1).zfill(4)+'.jpg',img)'''

            joints = joints.reshape((len(joints) / 2, 2))
            trainGT[:,:,i] = joints

sio.savemat('trainGT.mat', {'trainGT':trainGT})
#sio.savemat('crop.mat', {'crop':crop})
