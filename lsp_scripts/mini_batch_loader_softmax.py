#!/usr/bin/env python2.7
# coding:utf-8
 
import os
import sys
import numpy as np
import cv2
import cPickle
import math
import time
from scipy import misc,ndimage
 
class MiniBatchLoader(object):
    LABEL_COUNT = 15
 
    def __init__(self, image_dir_path, batch_size, in_size):
 
        # load data paths
        self.data_dir = image_dir_path
        self.batch_size = batch_size
 
        # load a mean image
        self.mean = np.array([113.970, 110.130, 103.804]) 
        #self.mean = np.array([103.939, 116.779, 123.68])
        

        self.in_size = in_size
        self.shift = 5
 
    # test ok
    def load_data(self, lines):
        mini_batch_size = self.batch_size
        in_channels = 3
        xs = np.zeros((mini_batch_size, in_channels,  self.in_size, self.in_size)).astype(np.float32)
        ys = np.zeros((mini_batch_size, self.in_size, self.in_size)).astype(np.int32)
 
        for i, line in enumerate(lines):
            datum = line.split(',')
            img_fn = '%s%s' % (self.data_dir, datum[0])
            
            #_/_/_/ xs: read image & joint _/_/_/  
            img = cv2.imread(img_fn)
            joints = np.asarray([int(float(p)) for p in datum[1:]])         


            joints = joints.reshape((len(joints) / 2, 2))

            

            #_/_/_/ flip _/_/_/
            if np.random.randint(2) == 1:
                datum[0] = 'flip'+datum[0]
                img = np.fliplr(img)
                joints[:,0] = img.shape[1] - joints[:,0]
                joints = list(zip(joints[:,0], joints[:,1]))

                joints[0], joints[5] = joints[5], joints[0] #ankle
                joints[1], joints[4] = joints[4], joints[1] #knee
                joints[2], joints[3] = joints[3], joints[2] #hip
                joints[6], joints[11] = joints[11], joints[6] #wrist
                joints[7], joints[10] = joints[10], joints[7] #elbow
                joints[8], joints[9] = joints[9], joints[8] #shoulder

            joints = np.array(joints).flatten()
            joints = joints.reshape((len(joints) / 2, 2))

            delete = []
            for v in range(len(joints)):
	            if  joints[v,0] < 0 or joints[v,1] < 0 or \
                    joints[v,0] > img.shape[1] or joints[v,1] > img.shape[0]:
		        delete.append(v)

            #_/_/_/ rotate _/_/_/
            if np.random.randint(2) != 3:
                datum[0] = 'rot'+datum[0]
                angle = np.random.randint(-180,180)
                h = img.shape[0]
                w = img.shape[1]
                
                theta = np.radians(angle)
                c, s = np.cos(theta), np.sin(theta)
                R = np.asarray([[c,-s],[s,c]])
                joints[:,0] = joints[:,0]-w/2
                joints[:,1] = joints[:,1]-h/2
                joints = np.dot(joints,R)
                joints[:,0] = joints[:,0]+w/2
                joints[:,1] = joints[:,1]+h/2
                
                img = ndimage.rotate(img, angle, reshape=True)
                joints[:,0] = joints[:,0]+(img.shape[1]-w)/2
                joints[:,1] = joints[:,1]+(img.shape[0]-h)/2

            #_/_/_/ image cropping _/_/_/
            visible_joints = joints.copy()
            visible_joints = np.delete(visible_joints, (delete), axis=0)
            visible_joints = visible_joints.astype(np.int32)
            x, y, w, h = cv2.boundingRect(np.asarray([visible_joints.tolist()]))

            inf, sup = 1.5, 2.0
            r = sup - inf
            pad_w_r = np.random.rand() * r + inf  # inf~sup
            pad_h_r = np.random.rand() * r + inf  # inf~sup
            x -= (w * pad_w_r - w) / 2
            y -= (h * pad_h_r - h) / 2
            w *= pad_w_r
            h *= pad_h_r

            #_/_/_/ shifting _/_/_/
            x += np.random.rand() * self.shift * 2 - self.shift
            y += np.random.rand() * self.shift * 2 - self.shift

            x, y, w, h = [int(z) for z in [x, y, w, h]]
            x = np.clip(x, 0, img.shape[1] - 1)
            y = np.clip(y, 0, img.shape[0] - 1)
            w = np.clip(w, 1, img.shape[1] - (x + 1))
            h = np.clip(h, 1, img.shape[0] - (y + 1))
            img = img[y:y + h, x:x + w]   

            joints = np.asarray([(j[0] - x, j[1] - y) for j in joints])


            #_/_/_/ resize _/_/_/
            orig_h, orig_w, _ = img.shape
            joints[:,0] = joints[:,0] / float(orig_w) * 224
            joints[:,1] = joints[:,1] / float(orig_h) * 224
            img = cv2.resize(img, (224, 224),interpolation=cv2.INTER_NEAREST)
            xs[i, :, :, :] = ((img - self.mean)/255).transpose(2, 0, 1)


            #_/_/_/ heatmap _/_/_/
            h, w, c = img.shape
            heatmap = np.zeros((h,w))
            csize = 21
            ori = (csize - 1)/2
            cc = self.circle((csize,csize))

            for j in range(len(joints)):
                if joints[j,0]<0 or joints[j,1]<0 or \
                   joints[j,0] > img.shape[1] or joints[j,1] > img.shape[0]:
                    continue
                cir = cc*(j+1)
                x = int(joints[j,0])-(csize-1)/2
                xp = int(joints[j,0])+(csize+1)/2
                y = int(joints[j,1])-(csize-1)/2
                yp = int(joints[j,1])+(csize+1)/2
                l = np.clip(x, 0, img.shape[0])
                r = np.clip(xp, 0, img.shape[0])
                u = np.clip(y, 0, img.shape[1])
                d = np.clip(yp, 0, img.shape[1])
                clipped = cir[u-y:csize-(yp-d), l-x:csize-(xp-r)]
                heatmap[u:d,l:r] = clipped
                
            ys[i, :, :] = heatmap

            # test
            #joints[:,[0,1]] = joints[:,[1,0]]

            '''joints = joints.astype(np.int32)
            
            joints = [tuple(p) for p in joints]
            for j, joint in enumerate(joints):
                cv2.circle(img, joint, 5, (0, 0, 255), -1)
                cv2.putText(img, '%d' % j, joint, cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                       (255, 255, 255))
            cv2.imwrite('map/'+datum[0],img)'''

        return xs, ys

    def circle(self,shape=(3,3)):
        h = np.zeros(shape)
        ori = (shape[0] - 1)/2
        for i in range(shape[0]):
            for j in range(shape[1]):
                if math.sqrt((i-ori)*(i-ori) + (j-ori)*(j-ori)) < ori:
                    h[i,j]=1;

        return h

