from Device import Device
from GUIData import GUIData
from AIChain import AIChain

import cv2


class Automator:
    def __init__(self, app_name, test_case_no):
        self.app_name = app_name
        self.test_case_no = test_case_no

        self.device = None

        self.trace_elements = []
        self.trace_guis = []
        self.incorrect_elements = []

    def load_device(self):
        from ppadb.client import Client as AdbClient
        from Device import Device
        client = AdbClient(host="127.0.0.1", port=5037)
        self.device = Device(client.devices()[0], app_name=self.app_name, test_case_no=self.test_case_no)
        print('=== Device Loaded ===')

    '''
    **********************************
    *** Auto the Task on a New GUI ***
    **********************************
    '''
    def auto_task_on_new_gui(self, task,
                             show_gui_ele=False, ai_chain_model='gpt-3.5-turbo', printlog=False, show_action=False):
        self.collect_gui_data()
        self.analyze_gui(show_gui_ele)
        self.execute_task_on_gui(task, self.trace_guis[-1], ai_chain_model, printlog, show_action)

    def collect_gui_data(self):
        '''
        collect the raw GUI data [raw xml, VH Json, Screenshot] on current screen and save to 'data/app_name/test_case_no/device'
        => ui_no.xml, ui_no.json, ui_no.png
        '''
        print('\n=== 1. Collect UI metadata from the device ===')
        self.device.cap_screenshot()
        self.device.cap_vh()
        self.device.reformat_vh_json()

    def analyze_gui(self, show=False):
        '''
        Clean up the VH tree and extract [elements, element_tree] and save to "data/app_name/test_case_no/guidata"
        => ui_no_elements.json, ui_no_tree.json
        '''
        print('\n=== 2. Extract and analyze UI info ===')
        gui = GUIData(gui_img_file=self.device.output_file_path_screenshot,
                      gui_json_file=self.device.output_file_path_json,
                      output_file_root=self.device.testcase_save_dir)
        gui.ui_info_extraction()
        gui.ui_analysis_elements_description()
        gui.ui_element_tree()
        if show:
            gui.show_all_elements(only_leaves=False)
        self.trace_guis.append(gui)

    def execute_task_on_gui(self, task, gui, model='gpt-3.5-turbo', printlog=False, show_action=False):
        '''
        Identify the target element and execute the task on the current GUI through AI chain
        '''
        print('\n=== 3. Check if the task can complete on the UI through AI chain ===')
        ai_chain = AIChain(gui, model, device=self.device)
        relation, target_element = ai_chain.ai_chain_automate_check_elements(task, printlog)

        if relation == 0:
            print('Unrelated')
        elif relation == 1:
            print('Task Complete')
        elif relation == 2:
            print('Execute Action')
            action = ['click', target_element]
            self.execute_action(action, self.trace_guis[-1], show_action)

        self.trace_elements.append(target_element)

    '''
    ******************************
    *** Conversation Operation ***
    ******************************
    '''
    def execute_action(self, action, gui, show=False):
        '''
        @action: (operation type, element id)
            => 'click', 'scroll'
        @device: ppadb device
        '''
        print('--- Execute the action on the GUI ---')
        op_type, ele_id = action
        ele = gui.elements[ele_id]
        bounds = ele['bounds']
        if op_type == 'click':
            centroid = ((bounds[2] + bounds[0]) // 2, (bounds[3] + bounds[1]) // 2)
            if show:
                board = gui.img.copy()
                cv2.circle(board, (centroid[0], centroid[1]), 20, (255, 0, 255), 8)
                cv2.imshow('click', cv2.resize(board, (board.shape[1] // 3, board.shape[0] // 3)))
                cv2.waitKey()
                cv2.destroyWindow('click')
            self.device.adb_device.input_tap(centroid[0], centroid[1])
        elif op_type == 'scroll':
            bias = 5
            if show:
                board = gui.img.copy()
                cv2.circle(board, (bounds[2]-bias, bounds[3]+bias), 20, (255, 0, 255), 8)
                cv2.circle(board, (bounds[0]-bias, bounds[1]+bias), 20, (255, 0, 255), 8)
                cv2.imshow('scroll', cv2.resize(board, (board.shape[1] // 3, board.shape[0] // 3)))
                cv2.waitKey()
                cv2.destroyWindow('scroll')
            self.device.adb_device.input_swipe(bounds[2]-bias, bounds[3]+bias, bounds[0]-bias, bounds[1]+bias, 500)
