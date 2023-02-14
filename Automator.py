from GUI import GUI

class Automator:
    def __init__(self, cur_gui_img):
        self.GUI = GUI(cur_gui_img)
        self.textual_elements = []

    def detect_and_classify_gui_elements(self):
        # 1. element detection
        self.GUI.detect_element(show=False)
        # 2. classify non-text elements (Compos)
        self.GUI.classify_compo()

    def get_textual_gui_elements(self):
        '''
        Get all the gui element in textual, including text elements and textual Compo labels
        '''
        if len(self.GUI.elements) == 0:
            self.detect_and_classify_gui_elements()
        for ele in self.GUI.elements:
            if ele.attributes.element_class == 'Text':
                self.textual_elements.append(ele.attributes.text_content)
            elif ele.attributes.element_class == 'Compo':
                self.textual_elements.append(ele.attributes.compo_class)

    def show_gui_elements(self):
        self.GUI.show_element_detection()
        self.GUI.show_element_classes()