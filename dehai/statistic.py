import os
import cv2
import json
import imutils
from glob import glob
import matplotlib.pyplot as plt
from graphviz import Digraph


data_dir = '/home/xiaofan/Project/data/Rico/combined'

class GUIData:
  def __init__(self, gui_file):
    self.image_file = gui_file
    self.layout_file = gui_file.replace('.jpg', '.json')
    self.save_dir = self.get_save_dir()
    self.image = cv2.resize(cv2.imread(gui_file), (1440, 2560))
    self.element_id = 0
    self.elements = []
    self.edges = []
    
  def get_save_dir(self):
    spath = os.path.join('/home/xiaofan/Project/ICSE2023/GUI-Semantics/data-processing/Tree_visualize', os.path.basename(self.image_file).replace('.jpg', ''))
    if not os.path.exists(spath):
      os.mkdir(spath)
      os.mkdir(os.path.join(spath, 'components'))
    return spath
    
  def valid_element(self, element):
    if element.get('bounds')[3] - element.get('bounds')[1] <= 0 or element.get('bounds')[2] - element.get('bounds')[0] <= 0:
      return False
    return True
    
  def resize_component(self, image):
    if image.shape[0] > image.shape[1]:
      return imutils.resize(image, height = 600)
    else:
      return imutils.resize(image, width = 600)
      
  def get_center(self, bounds):
    return (int((bounds[2] + bounds[0])/2), int((bounds[3] + bounds[1])/2))
     
  def get_label(self, element):
    text = 'class:' + element.get('class') + '\n' +  \
           'visible-to-user:' + str(element.get('visible-to-user')) + '\n' +  \
           'visibility:' + element.get('visibility')
    return text
    
  def filter_element(self):
    for edge in self.edges[:]:
      if len(list(filter(lambda element: element.get('id') == edge[1], self.elements))) == 0:
        self.edges.remove(edge)
    i = 0
    while i < len(self.edges):
      if list(filter(lambda element: element.get('id') == self.edges[i][0], self.elements))[0].get('bounds') == list(filter(lambda element: element.get('id') == self.edges[i][1], self.elements))[0].get('bounds'):
        for edge in enumerate(self.edges[:]):
          if edge[1][0] == self.edges[i][1]:
            self.edges[edge[0]] = (self.edges[i][0], edge[1][1])
        self.elements.remove(list(filter(lambda element: element.get('id') == self.edges[i][1], self.elements))[0])
        self.edges.remove(self.edges[i])
      else:
          i += 1

  def draw_graph(self):
    gra = Digraph()
    for element in self.elements:
      label_text = self.get_label(element)
      gra.node(name = str(element.get('id')), label = label_text, labelloc='b', fontsize = '40', image = os.path.join(self.save_dir, 'components', str(element.get('id')) + '.jpg'), width = '8pt', height = '18pt', shape = 'rectangle')
    gra.edges(self.edges)
    gra.render(os.path.join(self.save_dir, 'tree'))
    
  def draw_relation(self):
    image = self.image[:]
    print (len(self.elements))
    for element in self.elements:
      cv2.circle(image, self.get_center(element.get('bounds')), 4, (0, 255, 0), 4)
    for edge in self.edges:
      point1 = self.get_center(list(filter(lambda element: element.get('id') == edge[0], self.elements))[0].get('bounds'))
      point2 = self.get_center(list(filter(lambda element: element.get('id') == edge[1], self.elements))[0].get('bounds'))
      cv2.line(image, point1, point2, (0, 0, 255), 3)
    cv2.imwrite(os.path.join(self.save_dir, 'relation.jpg'), image)
  
  def extract_children_element(self, element, parent_id = 0):
    if sum(element.get('bounds')) == 0:
      return
    element['id'] = str(self.element_id)
    if self.valid_element(element):
      self.elements.append(element)
      component_crop = self.image[element.get('bounds')[1]:element.get('bounds')[3], element.get('bounds')[0]:element.get('bounds')[2]]
      cv2.imwrite(os.path.join(self.save_dir, 'components', str(self.element_id) + '.jpg'), self.resize_component(component_crop))
      if 'children' in element:
        for child in element.get('children'):
          self.element_id += 1
          self.edges.append((str(parent_id), str(self.element_id)))
          self.extract_children_element(child, self.element_id)
    
  def get_element(self):
    layout = json.load(open(self.layout_file, 'r'))
    element_root = layout.get('activity').get('root')
    self.extract_children_element(element_root)
    
  
def main():
  gui_file = '/home/xiaofan/Project/data/Rico/combined/120.jpg'
  gui = GUIData(gui_file)
  gui.get_element()
  gui.filter_element()
  gui.draw_graph()
  gui.draw_relation()

if __name__== '__main__':
  main()

