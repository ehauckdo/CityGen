import sys
import optparse
from classifier.Renderer.Renderer import render
from classifier.Map.Map import readFile

def parse_args(args):
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-i', action="store", type="string", dest="filename",
	   help="OSM input file", default="data/sumidaku.osm")
    return parser.parse_args()

def main():
    opt, args = parse_args(sys.argv[1:])
    input = opt.filename
    map = readFile(input)
    render(map, script_run=True)

if __name__ == '__main__':
    main()
