import cv2
from os.path import join as pjoin
import xmltodict
import json

class Device:
    def __init__(self, adb_device, file_save_dir='/home/ml/Code/github/UI-Automation/vh/data'):
        self.adb_device = adb_device  # ppadb device
        self.name = self.adb_device.get_serial_no()

        self.file_save_dir = file_save_dir
        self.screenshot_path = pjoin(file_save_dir, str(self.name) + '.png')
        self.vh_xml_path = pjoin(file_save_dir, str(self.name) + '.xml')
        self.vh_json_path = pjoin(file_save_dir, str(self.name) + '.json')

        self.screenshot = None  # cv2 image
        self.vh = None          # dict

    def get_devices_info(self):
        print("Device Name:%s Resolution:%s" % (self.name, self.adb_device.wm_size()))

    def cap_screenshot(self, recur_time=0):
        screen = self.adb_device.screencap()
        with open(self.screenshot_path, "wb") as fp:
            fp.write(screen)
        self.screenshot = cv2.imread(self.screenshot_path)
        # recurrently load to avoid failure
        if recur_time < 3 and self.screenshot is None:
            self.cap_screenshot(recur_time+1)
        return self.screenshot

    def cap_vh(self, dump_to_json=True):
        self.adb_device.shell('uiautomator dump')
        self.adb_device.pull('/sdcard/window_dump.xml', self.vh_xml_path)
        self.vh = xmltodict.parse(open(self.vh_xml_path, 'r').read())
        if dump_to_json:
            json.dump(self.vh, open(self.vh_json_path, 'w'), indent=4)


if __name__ == '__main__':
    from ppadb.client import Client as AdbClient
    client = AdbClient(host="127.0.0.1", port=5037)
    device = Device(client.devices()[0])
