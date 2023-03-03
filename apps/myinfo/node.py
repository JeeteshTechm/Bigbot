from main.Node import BaseNode

class Expandable(BaseNode):
    def __init__(self, data, meta=None):
        super(Expandable, self).__init__("apps.myinfo.component.Expandable", data, meta)