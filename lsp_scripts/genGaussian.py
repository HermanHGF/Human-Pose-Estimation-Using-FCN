#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
import sys
import math
import time
import numpy as np
import scipy.io as sio
import cv2

def gauss2D(shape=(3,3),sigma=0.5):
    m,n = [(ss-1.)/2. for ss in shape]
    y,x = np.ogrid[-m:m+1,-n:n+1]
    h = np.exp( -(x*x + y*y) / (2.*sigma*sigma) )
    h[ h < np.finfo(h.dtype).eps*h.max() ] = 0
    sumh = h.sum()
    if sumh != 0:
        h /= sumh
    return h

if __name__ == '__main__':

    test_fn = "data/LSP/train_joints.csv" #
    test_dl = np.array([l.strip() for l in open(test_fn).readlines()])

    sum_accuracy = 0
    sum_loss     = 0
    test_data_size = 11000  #
    train = np.zeros((224,224,test_data_size)).astype(np.float32)
    ksize = 35

    for i, line in enumerate(test_dl):
        datum = line.split(',')
        img_fn = 'data/LSP/images/%s' % (datum[0])
        img = cv2.imread(img_fn)
        joints = np.asarray([int(float(p)) for p in datum[1:]])
        joints = joints.reshape((len(joints) / 2, 2))



        delete = []
        for v in range(len(joints)):
            if  joints[v,0] <= 0 or joints[v,1] <= 0 or joints[v,0] > img.shape[1] or joints[v,1] > img.shape[0]:
                delete.append(v)

        #_/_/_/ image cropping _/_/_/
        visible_joints = joints.copy()
        visible_joints = np.delete(visible_joints, (delete), axis=0)
        visible_joints = visible_joints.astype(np.int32)
        x, y, w, h = cv2.boundingRect(np.asarray([visible_joints.tolist()]))

        inf, sup = 1.5, 2.0
        r = sup - inf
        pad_w_r = 1.7#np.random.rand() * r + inf  # inf~sup
        pad_h_r = 1.7#np.random.rand() * r + inf  # inf~sup
        x -= (w * pad_w_r - w) / 2
        y -= (h * pad_h_r - h) / 2
        w *= pad_w_r
        h *= pad_h_r

        x, y, w, h = [int(z) for z in [x, y, w, h]]
        x = np.clip(x, 0, img.shape[1] - 1)
        y = np.clip(y, 0, img.shape[0] - 1)
        w = np.clip(w, 1, img.shape[1] - (x + 1))
        h = np.clip(h, 1, img.shape[0] - (y + 1))

        joints = np.asarray([(j[0] - x, j[1] - y) for j in joints])


        #_/_/_/ resize _/_/_/
        joints[:,0] = joints[:,0] / float(w) * 224
        joints[:,1] = joints[:,1] / float(h) * 224




        heatmap = np.zeros((224,224))
        gaussian = gauss2D((ksize,ksize), 6)*233
        for j in range(len(joints)):
            if joints[j,0]<0 or joints[j,1]<0 or joints[j,0] > 224 or joints[j,1] > 224:
                 continue
            x = joints[j,0]-ksize/2
            xp = joints[j,0]+ksize/2+1
            y = joints[j,1]-ksize/2
            yp = joints[j,1]+ksize/2+1
            l = np.clip(x, 0, 224)
            r = np.clip(xp, 0, 224)
            u = np.clip(y, 0, 224)
            d = np.clip(yp, 0, 224)

            clipped = gaussian[u-y:ksize-(yp-d), l-x:ksize-(xp-r)]
            heatmap[u:d,l:r] = clipped + heatmap[u:d,l:r]

        heatmap = 1-heatmap
        heatmap[heatmap<0] = 0
        train[:,:,i] = heatmap

        #cv2.imwrite('GaussianTrainMap/'+str(i).zfill(4)+'.jpg',heatmap*255)

    sio.savemat('GaussianTrain.mat', {'GaussianTrain':train})
