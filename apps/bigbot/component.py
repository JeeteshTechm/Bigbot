from contrib.application import Descriptor
from contrib.application import BaseBuilderBlock

class TerminalBlock(BaseBuilderBlock):

    def __init__(self, source):
        descriptor = Descriptor('Terminal')
        descriptor.summary = "For starting and ending of workflow."
        descriptor.category = "default"
        super().__init__(source, descriptor)

    def load_template(self, loader):
        return loader.from_file('res/xml/terminal_block.xml')

    def load_connections(self, properties=[]):
        for item in properties:
            if item['name'] == 'type':
                if item['value'] == 'end':
                    return []
        return super().load_connections(properties)

class PromptText(BaseBuilderBlock):

    def __init__(self, source):
        descriptor = Descriptor('Plain Text')
        descriptor.summary = "For showing text input."
        descriptor.category = "prompt"
        super().__init__(source, descriptor)

    def load_template(self, loader):
        return loader.from_file('res/xml/prompt_text.xml')

    def load_connections(self, properties=[]):
        return super().load_connections(properties)

class PromptURLImage(BaseBuilderBlock):

    def __init__(self, source):
        descriptor = Descriptor('URL Image')
        descriptor.summary = "For showing image from url."
        descriptor.category = "prompt"
        super().__init__(source, descriptor)

    def load_template(self, loader):
        return loader.from_file('res/xml/prompt_url_image.xml')

    def load_connections(self, properties=[]):
        return super().load_connections(properties)

class InputText(BaseBuilderBlock):

    def __init__(self, source):
        descriptor = Descriptor('Text Input')
        descriptor.summary = "Take text like input from user."
        descriptor.category = "input"
        super().__init__(source, descriptor)

    def load_template(self, loader):
        return loader.from_file('res/xml/input_text.xml')

    def load_connections(self, properties=[]):
        return super().load_connections(properties)

class InputDate(BaseBuilderBlock):

    def __init__(self, source):
        descriptor = Descriptor('Date Input')
        descriptor.summary = "Take date input from user."
        descriptor.category = "input"
        super().__init__(source, descriptor)

    def load_template(self, loader):
        return loader.from_file('res/xml/input_date.xml')

    def load_connections(self, properties=[]):
        return super().load_connections(properties)

class InputDateTime(BaseBuilderBlock):

    def __init__(self, source):
        descriptor = Descriptor('Datetime Input')
        descriptor.summary = "Take date and time input from user."
        descriptor.category = "input"
        super().__init__(source, descriptor)

    def load_template(self, loader):
        return loader.from_file('res/xml/input_datetime.xml')

    def load_connections(self, properties=[]):
        return super().load_connections(properties)

class InputDuration(BaseBuilderBlock):

    def __init__(self, source):
        descriptor = Descriptor('Duration Input')
        descriptor.summary = "Take duration input from user."
        descriptor.category = "input"
        super().__init__(source, descriptor)

    def load_template(self, loader):
        return loader.from_file('res/xml/input_duration.xml')

    def load_connections(self, properties=[]):
        return super().load_connections(properties)

class InputSelection(BaseBuilderBlock):

    def __init__(self, source):
        descriptor = Descriptor('Input Selection')
        descriptor.summary = "Force user to choose input from."
        descriptor.category = "input"
        super().__init__(source, descriptor)

    def load_template(self, loader):
        return loader.from_file('res/xml/input_selection.xml')

    def load_connections(self, properties=[]):
        connect = super().load_connections(properties)
        for item in properties:
            if item['type'] == 'selections':
                for selection_item in item['value']:
                    connect.append([selection_item['key'],selection_item['value']])
        return connect

class InputSearchable(BaseBuilderBlock):

    def __init__(self, source):
        descriptor = Descriptor('Input Search')
        descriptor.summary = "From searchable result."
        descriptor.category = "input"
        super().__init__(source, descriptor)

    def load_template(self, loader):
        return loader.from_file('res/xml/input_searchable.xml')

    def load_connections(self, properties=[]):
        connect = super().load_connections(properties)
        for item in properties:
            if item['type'] == 'multiple':
                if item['value'] == True:
                    connect.append(["select","on select"])
                    connect.append(["submit","on submit"])
        return connect