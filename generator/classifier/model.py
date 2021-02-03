import sys
import os
from skimage import io
import classifier.Validator as val #the validator
import classifier.Map.Map as map #lib to read the osm file
import classifier.Renderer.Renderer as renderer #lib to render to image


def load_model(model_filename="classifier/weight_tsukuba.hdf5"):
    model = val.createModel(model_filename)
    return model

def accuracy(image_filename, model):
    mymap =  map.readFile(image_filename)

    imageName = "temp"
    renderer.render(mymap)
    renderer.osmToImage(imageName)
    imageName = imageName + ".png"

    test = io.imread(imageName)
    splittedImage = val.imageSplitter(test)
    value = val.validate(model, splittedImage)

    averageValue = sum(value)/len(value)
    return averageValue
