import logging
from sys import platform
import re

import window
from core_interface import push_input_event

from PyQt5.QtCore import QEvent, Qt, QCoreApplication
from PyQt5.QtGui import QKeyEvent, QKeySequence
from PyQt5.QtWidgets import QWidget

# Used to detect if a keypress was just a modifier
MODIFIER_KEYS = {
    Qt.Key_Shift: "s",
    Qt.Key_Control: "C",
    Qt.Key_Alt: "M",
    Qt.Key_AltGr: "M",
    Qt.Key_Meta: "Meta",
    Qt.Key_Super_L: "S",
    Qt.Key_Super_R: "S"
}

# Special keys for Next
SPECIAL_KEYS = {
    Qt.Key_Backspace: "BACKSPACE",
    Qt.Key_Delete: "DELETE",
    Qt.Key_Escape: "ESCAPE",
    Qt.Key_hyphen: "HYPHEN",
    Qt.Key_Return: "RETURN",
    Qt.Key_Enter: "RETURN",
    Qt.Key_Space: "SPACE",
    Qt.Key_Tab: "TAB",
    Qt.Key_Left: "Left",
    Qt.Key_Right: "Right",
    Qt.Key_Up: "Up",
    Qt.Key_Down: "Down"
}

# Used for bitmasking to determine modifiers
MODIFIERS = {}
# Used for constructing a bitmasked modifier
REVERSE_MODIFIERS = {}

if platform == "linux" or platform == "linux2":
    tmp = {Qt.ShiftModifier: "s",
           Qt.ControlModifier: "C",
           Qt.AltModifier: "M",
           Qt.MetaModifier: "M"}
    MODIFIERS.update(tmp)
    tmp = {"s": Qt.ShiftModifier,
           "C": Qt.ControlModifier,
           "M": Qt.AltModifier,
           "M": Qt.MetaModifier}
    REVERSE_MODIFIERS.update(tmp)
elif platform == "darwin":
    tmp = {Qt.ShiftModifier: "s",
           Qt.ControlModifier: "S",
           Qt.AltModifier: "M",
           Qt.MetaModifier: "C"}
    MODIFIERS.update(tmp)
    tmp = {"s": Qt.ShiftModifier,
           "S": Qt.ControlModifier,
           "M": Qt.AltModifier,
           "C": Qt.MetaModifier}
    REVERSE_MODIFIERS.update(tmp)
elif platform == "win32" or platform == "win64":
    tmp = {Qt.ShiftModifier: "s",
           Qt.ControlModifier: "C",
           Qt.AltModifier: "M",
           Qt.MetaModifier: "M"}
    MODIFIERS.update(tmp)
    tmp = {"s": Qt.ShiftModifier,
           "C": Qt.ControlModifier,
           "M": Qt.AltModifier,
           "M": Qt.MetaModifier}
    REVERSE_MODIFIERS.update(tmp)


def create_modifiers_list(event_modifiers):
    modifiers = []
    for key, value in MODIFIERS.items():
        if (event_modifiers & key):
            modifiers.append(value)
    return modifiers or [""]


def create_key_string(event):
    text = ""
    if event.key() in SPECIAL_KEYS:
        text = SPECIAL_KEYS.get(event.key())
    elif event.text() and not is_control_sequence(event.text()):
        text = event.text()
    else:
        text = QKeySequence(event.key()).toString().lower()
    return text


def is_control_sequence(s):
    return re.match("/(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]/", s)


def create_modifiers_flag(modifiers):
    flag = Qt.KeyboardModifiers()
    for modifier in modifiers:
        if(REVERSE_MODIFIERS.get(modifier)):
            flag = flag | REVERSE_MODIFIERS.get(modifier)
    return flag


def is_modifier(key):
    return key in MODIFIER_KEYS.keys()


def generate_input_event(window_id, key_code, modifiers, low_level_data, x, y):
    """
    The Lisp core tells us to generate this key event.

    - window_id: str
    - key_code: int
    - modifiers: [str]
    - low_level_data: key code from Qt (int).
    - x, y: float
    """
    modifiers_flag = create_modifiers_flag(modifiers)
    logging.info("generate input, window: {} code: {}, modifiers {}, low_level_data {}".format(
        window_id, key_code, modifiers, low_level_data))
    #  Scan Code set to very high value not in system to distinguish
    #  it as an artifical key press, this avoids infinite propagation
    #  of key presses when it is caught by the event filter
    text = None
    if (low_level_data not in SPECIAL_KEYS):
        text = chr(low_level_data)
    event = QKeyEvent(QEvent.KeyPress, key_code, modifiers_flag,
                      10000, 10000, 10000, text=text)
    receiver = window.get_window(window_id).buffer.focusProxy()
    QCoreApplication.sendEvent(receiver, event)


class EventFilter(QWidget):
    def __init__(self, sender, parent=None):
        super(EventFilter, self).__init__(parent)
        self.sender = sender
        self.sender.installEventFilter(self)

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.KeyPress and not
            is_modifier(event.key()) and
                event.nativeScanCode() != 10000):
            modifiers = create_modifiers_list(event.modifiers())
            key_string = create_key_string(event)
            key_code = event.key()
            low_level_data = 0
            try:
                low_level_data = ord(key_string)
            except TypeError:
                low_level_data = key_code
            except ValueError:
                low_level_data = key_code
            logging.info("send code: {} string: {} modifiers: {} low_level_data: {}".format(
                key_code, key_string, modifiers, low_level_data))
            push_input_event(key_code,
                             key_string,
                             modifiers,
                             -1.0, -1.0, low_level_data,
                             window.active())
            return True
        return False
