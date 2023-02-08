import cv2


class ElementAttributes:
    def __init__(self):
        # for non-text
        self.element_class = None   # ['Compo', 'Text']
        self.compo_class = None     # ['Text Button', 'Input', 'Switch', 'Image', 'Icon', 'Checkbox']
        self.icon_class = None      # [99 classes]
        self.image_class = None     # [imageNet 1k classes]
        self.clickable = False      # Boolean
        # for text
        self.text_content = None    # Text content
        self.text_ner = None        # NER ['Name', 'Date', 'Time', 'Location']
        self.text_bold = False      # Boolean


class BoundingBox:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.width = right - left
        self.height = bottom - top
        self.area = self.width * self.height


class Element:
    def __init__(self, id, left, top, right, bottom):
        self.id = id
        self.attributes = ElementAttributes()
        self.bounding = BoundingBox(left, top, right, bottom)
        self.clip = None

    def get_clip(self, img):
        self.clip = img[self.bounding.top: self.bounding.bottom, self.bounding.left: self.bounding.right]

    def draw_element(self, img, color, text=None, show=False):
        cv2.rectangle(img, (self.bounding.left, self.bounding.top), (self.bounding.right, self.bounding.bottom), color, 2)
        if text is not None:
            cv2.putText(img, text, (self.bounding.left+5, self.bounding.top+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        if show:
            cv2.imshow('element', img)
            cv2.waitKey()
            cv2.destroyWindow('element')
