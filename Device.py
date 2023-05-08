import os

import cv2
from os.path import join as pjoin
import xmltodict
import json


class Device:
    def __init__(self, adb_device, app_name='twitter', test_case_no=1, output_file_root='data', gui_no=0):
        self.adb_device = adb_device  # ppadb device
        self.device_name = self.adb_device.get_serial_no()

        self.app_name = app_name
        self.test_case_no = test_case_no
        self.gui_no = gui_no

        self.screenshot = None  # cv2 image
        self.vh = None          # dict

        # output file paths
        self.testcase_save_dir = pjoin(output_file_root, app_name, 'testcase' + str(test_case_no))
        self.device_save_dir = pjoin(self.testcase_save_dir, 'device')
        os.makedirs(self.testcase_save_dir, exist_ok=True)
        os.makedirs(self.device_save_dir, exist_ok=True)
        # print('*** Save data to dir', self.device_save_dir, '***')
        self.output_file_path_screenshot = pjoin(self.device_save_dir, str(self.gui_no) + '.png')
        self.output_file_path_xml = pjoin(self.device_save_dir, str(self.gui_no) + '.xml')
        self.output_file_path_json = pjoin(self.device_save_dir, str(self.gui_no) + '.json')

    def init_file_path_by_gui_no(self, gui_no):
        self.output_file_path_screenshot = pjoin(self.device_save_dir, str(gui_no) + '.png')
        self.output_file_path_xml = pjoin(self.device_save_dir, str(gui_no) + '.xml')
        self.output_file_path_json = pjoin(self.device_save_dir, str(gui_no) + '.json')

    def get_devices_info(self):
        print("Device Name:%s Resolution:%s" % (self.device_name, self.adb_device.wm_size()))

    def cap_screenshot(self, recur_time=0):
        print('--- Take screenshot ---')
        screen = self.adb_device.screencap()
        with open(self.output_file_path_screenshot, "wb") as fp:
            fp.write(screen)
        self.screenshot = cv2.imread(self.output_file_path_screenshot)
        # print('Save screenshot to', self.output_file_path_screenshot)
        # recurrently load to avoid failure
        if recur_time < 3 and self.screenshot is None:
            self.cap_screenshot(recur_time+1)

    def cap_vh(self):
        print('--- Collect XML ---')
        self.adb_device.shell('uiautomator dump')
        self.adb_device.pull('/sdcard/window_dump.xml', self.output_file_path_xml)
        # print('Save xml to', self.output_file_path_xml)
        self.vh = xmltodict.parse(open(self.output_file_path_xml, 'r', encoding='utf-8').read())
        json.dump(self.vh, open(self.output_file_path_json, 'w', encoding='utf-8'), indent=4)
        # print('Save view hierarchy to', self.output_file_path_json)

    '''
    ********************************************
    *** Convert the VH format to Rico format ***
    ********************************************
    '''
    def reformat_node(self, node):
        node_new = {}
        for key in node.keys():
            if node[key] == 'true':
                node[key] = True
            elif node[key] == 'false':
                node[key] = False

            if key == 'node':
                node_new['children'] = node['node']
            elif key == '@bounds':
                node_new['bounds'] = eval(node['@bounds'].replace('][', ','))
            elif key == '@index':
                continue
            else:
                node_new[key.replace('@', '')] = node[key]
        return node_new

    def cvt_node_to_rico_format(self, node):
        node = self.reformat_node(node)
        if 'children' in node:
            if type(node['children']) == list:
                new_children = []
                for child in node['children']:
                    new_children.append(self.cvt_node_to_rico_format(child))
                node['children'] = new_children
            else:
                node['children'] = [self.cvt_node_to_rico_format(node['children'])]
        return node

    def reformat_vh_json(self):
        print('--- Tidy up View Hierarchy ---')
        self.vh = {'activity': {'root': self.cvt_node_to_rico_format(self.vh['hierarchy']['node'])}}
        json.dump(self.vh, open(self.output_file_path_json, 'w', encoding='utf-8'), indent=4)
        # print('Save view hierarchy to', self.output_file_path_json)


if __name__ == '__main__':
    # start emulator in Android studio first and run to capture screenshot and view hierarchy
    # save vh xml, json and screenshot image to 'data/app_name/test_case_no/device'
    from ppadb.client import Client as AdbClient
    client = AdbClient(host="127.0.0.1", port=5037)

    device = Device(client.devices()[0], app_name='twitter', test_case_no=1)
    device.cap_screenshot()
    device.cap_vh()
    device.reformat_vh_json()
