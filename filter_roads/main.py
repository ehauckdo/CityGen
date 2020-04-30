import os, sys
from Map import MapReader,MapWriter

def remove_roads(input, output):
    reader = MapReader()
    reader.apply_file(input)
    print(reader.bounds)

    try:
        os.remove(output) #clean file if exists
    except: pass

    osmium_writer = osmium.SimpleWriter(output)
    writer = MapWriter(reader.highway_nodes, osmium_writer)
    writer.apply_file(input)
    osmium_writer.close()

if __name__ == '__main__':

    if len(sys.argv) > 1:
        input = sys.argv[1]
    else:
        input = "sample_data.osm"
    print(input)
