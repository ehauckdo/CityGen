import sys
import os
from skimage import io
import classifier.Validator as val #the validator
import classifier.Map.Map as map #lib to read the osm file
import classifier.Renderer.Renderer as renderer #lib to render to image


def load_model(model_filename="classifier/weight_tsukuba.hdf5"):
    model = val.createModel(model_filename)
    return model

def clean_files(filename):
    if os.path.exists("{}.png".format(filename)):
        os.remove("{}.png".format(filename))
    if os.path.exists("{}.eps".format(filename)):
        os.remove("{}.eps".format(filename))

def accuracy(image_filename, model):
    mymap =  map.readFile(image_filename)

    imageName = "temp"
    renderer.render(mymap)
    renderer.osmToImage(imageName)

    test = io.imread(imageName + ".png")
    splittedImage = val.imageSplitter(test)
    value = val.validate(model, splittedImage)

    clean_files(imageName)

    averageValue = sum(value)/len(value)
    return averageValue

def evaluate(image_filename, model_filename="classifier/weight_tsukuba.hdf5"):
    model = val.createModel(model_filename)
    mymap =  map.readFile(image_filename)

    imageName = "temp" #do not use file type Already provided by the lib just
                       # use the name, path is allowed
    renderer.render(mymap)
    renderer.osmToImage(imageName)

    test = io.imread(imageName + ".png")

    splittedImage = val.imageSplitter(test)

    value = val.validate(model, splittedImage)

    clean_files(imageName)

    averageValue = sum(value)/len(value)
    return averageValue
