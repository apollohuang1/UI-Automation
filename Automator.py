import openai
from GUI import GUI

class Automator:
    def __init__(self, cur_gui_img, task=''):
        self.GUI = GUI(cur_gui_img)
        self.textual_elements = []

        openai.api_key = open('openaikey.txt', 'r').readline()
        self.task = task            # string, a NL sentence to describe the task, e.g. "Turn on voice"
        self.prompt = None          # string, prompt including the task and textual_element as options sent to the LLM
        self.openai_resp = None     # the response from openai asked the prompt
        self.openai_answer = None   # the text answer in the openai_resp

    '''
    *********************************
    *** GUI Element Understanding ***
    *********************************
    '''
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
            if ele.attributes.element_class == 'Text' and len(ele.attributes.text_content) < 25:
                self.textual_elements.append(ele.attributes.text_content)
            elif ele.attributes.element_class == 'Compo' and ele.attributes.element_class != 'other':
                self.textual_elements.append(ele.attributes.compo_class)

    def show_gui_elements(self):
        self.GUI.show_element_detection()
        self.GUI.show_element_classes()

    '''
    ******************
    *** OpenAI LLM ***
    ******************
    '''
    def assemble_prompt(self):
        pre_prompt = 'Which UI component is more related to the task "' + self.task + '"?'
        post_prompt = 'Options:' + ';'.join(self.textual_elements) + ';'
        self.prompt = pre_prompt + post_prompt

    def ask_openai(self, prompt=None):
        self.assemble_prompt()
        prompt = self.prompt if prompt is None else prompt
        print('*** Asking ***\n', prompt)
        self.openai_resp = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=7,
            temperature=0
        )
        self.openai_answer = self.openai_resp['choices'][0]['text']
        print('*** Answer ***\n', self.openai_answer)
