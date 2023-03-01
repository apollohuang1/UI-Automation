import openai
from GUI import GUI


class Automator:
    def __init__(self, gui, task=''):
        self.gui = gui
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
    def get_textual_gui_elements(self):
        '''
        Get all the gui element in textual, including text elements and textual Compo labels
        '''
        for ele in self.gui.elements_leaves:
            if 'text' in ele and ele['text'] != '':
                text = ele['text']
                if 'content-desc' in ele and ele['content-desc'] != '':
                    text += ' / ' + ele['content-desc']
                    self.textual_elements.append(text)
                else:
                    self.textual_elements.append(ele['text'])
            else:
                if 'content-desc' in ele and ele['content-desc'] != '':
                    self.textual_elements.append(ele['content-desc'])
                # else:
                #     self.textual_elements.append(ele['caption'])
    '''
    ******************
    *** OpenAI LLM ***
    ******************
    '''
    def assemble_prompt(self):
        pre_prompt = 'I will give you several UI components on a UI page, which one of them is more related to the task "' + self.task + '"?'
        post_prompt = 'Components:[' + ';'.join(self.textual_elements) + ';'
        self.prompt = pre_prompt + post_prompt + ']'

    def ask_openai(self, task=None):
        self.task = task
        self.assemble_prompt()
        print('*** Asking ***\n', self.prompt)
        self.openai_resp = openai.Completion.create(
            model="text-davinci-003",
            prompt=self.prompt,
            max_tokens=7,
            temperature=0
        )
        self.openai_answer = self.openai_resp['choices'][0]['text']
        print('*** Answer ***\n', self.openai_answer)


if __name__ == '__main__':
    automator = Automator('data/input/2.jpg')
    automator.get_textual_gui_elements()
    automator.task = "Contact Lelya"
    automator.ask_openai()
