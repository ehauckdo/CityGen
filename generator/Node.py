class Node():
    def __init__(self, osmnode=None):
        if osmnode != None:
            self.id = osmnode.id
            self.location = osmnode.location
        self.type = {}
        self.color = "black"

    def __repr__(self):
        return "{}, {}".format(self.id, self.location)

    def apply_tag(self, tags):
        # if "highway" in tags.keys():
        #     self.type["highway"] = tags["highway"]
        # if "building" in tags.keys():
        #     self.type["building"] = tags["building"]
        self.tags = tags
        if "building" in tags.keys():
            self.color = "red"
