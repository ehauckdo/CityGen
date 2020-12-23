import numpy as np
import matplotlib.pyplot as plt
import datetime
#%matplotlib inline

import sys
import os
from keras.utils import to_categorical
from skimage import data,filters
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau,Callback
import pickle
import keras
from keras.layers import Dense, Activation,Flatten
from keras.optimizers import SGD, Adam

#create Model
def createModel(model_path):
    model = keras.applications.densenet.DenseNet121(include_top=True, weights=None, input_tensor=None, input_shape=(128,128,3), pooling=None, classes= 2)

    adam = Adam(lr=1e-3) # learning rate, momentum parameters for learning
    model.compile(loss='binary_crossentropy', optimizer=adam, metrics=["binary_accuracy"])
    #model.compile(loss='categorical_crossentropy', optimizer=adam, metrics=["accuracy"])
    #model.summary()
    if (os.path.isfile(model_path)):
        #print("Weight Loaded")
        model.load_weights(model_path)
    return model

def imageSplitter(data, size= (128,128,3)):
    temp = np.ndarray(data.shape)
    temp = np.ndarray((0,size[0],size[1],size[2]))
    #print(temp.size)
    horizontalSplit = data.shape[1]/size[1]
    result = []
    if( data.shape[1]%size[1]>0):
        horizontalSplit += 1
    horizontalSplit = int(horizontalSplit)
    verticalSplit = data.shape[0]/size[0]
    if( data.shape[0]%size[0]>0):
        verticalSplit += 1
    verticalSplit = int(verticalSplit)
    for i in range(0,horizontalSplit):
        xStart = i *size[1]
        xEnd = xStart + size[1]
        if (xEnd > data.shape[1]):
            xEnd = data.shape[1]-1
            xStart = xEnd - size[1]
        for i in range(0,verticalSplit):
            yStart = i *size[0]
            yEnd = yStart + size[0]
            if (yEnd > data.shape[0]):
                yEnd = data.shape[0]-1
                yStart = yEnd - size[0]
            temporary = data[yStart:yEnd,xStart:xEnd]
            #print(temp.shape)
            #print(temporary.shape)
            temp = np.append(temp,temporary[np.newaxis,:,:,:], axis = 0)

    return temp

def validate(model, images):
    result = model.predict(images)
    result2 = []
    for x in result:
        result2.append((x[1]+(1.0-x[0]))/2.0)
    return result2
