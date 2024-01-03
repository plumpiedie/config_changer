import sys
import yaml
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QApplication
from yaml import SafeDumper
import json
from mainwindow import *

SafeDumper.add_representer(type(None),
                           lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:null', ''))


class MainWindow(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.resize(500, 500)
        self.setWindowTitle('Config_editor')
        self.ui.lineEdit_2.setDisabled(True)
        self.ui.checkBox.stateChanged.connect(self.state_changed)
        self.ui.pushButton.clicked.connect(self.edit_conf_button)
        self.delete_keys = []  # если есть значения, используется только <new_conf>
        self.change_only = []
        self.delete = False

    def state_changed(self, state):
        if state == 2:
            self.ui.plainTextEdit.setDisabled(True)
            self.ui.lineEdit.setDisabled(True)
            self.ui.lineEdit_2.setEnabled(True)
            self.delete = True
        else:
            self.ui.plainTextEdit.setEnabled(True)
            self.ui.lineEdit.setEnabled(True)
            self.ui.lineEdit_2.setDisabled(True)
            self.delete = False

    def edit_conf_button(self):
        key_words = self.ui.lineEdit.text().replace(' ', '')
        if key_words:
            self.change_only = key_words.split(',')

        old_conf_text = self.ui.plainTextEdit.toPlainText()
        new_conf_text = self.ui.plainTextEdit_2.toPlainText()
        try:
            if self.ui.radioButton.isChecked():
                new_config = json.loads(new_conf_text)
                if self.delete is False:
                    old_config = json.loads(old_conf_text)
            elif self.ui.radioButton_2.isChecked():
                new_config = yaml.safe_load(new_conf_text)
                if self.delete is False:
                    old_config = yaml.safe_load(old_conf_text)
            if self.delete is False:
                if old_config is None or new_config is None:
                    QMessageBox.warning(self, 'Ошибка', 'Конфиг пуст')
                    return
            else:
                if new_config is None:
                    QMessageBox.warning(self, 'Ошибка', 'Конфиг пуст')
                    return
        except json.decoder.JSONDecodeError as exc:
            QMessageBox.critical(self, 'Ошибка', f'Проблема с форматом json конфига \n{exc}')
            return
        except yaml.parser.ParserError as exc:
            QMessageBox.critical(self, 'Ошибка', f'Проблема с форматом yaml конфига \n{exc}')
            return
        self.new_conf = new_config
        if self.delete is False:
            self.old_conf = old_config
        self.delete_keys = []
        if self.delete:
            if self.ui.lineEdit_2.text().replace(' ', '') == '':
                return
            self.delete_keys = self.ui.lineEdit_2.text().replace(' ', '').split(',')
            if len(self.delete_keys) == 0:
                return
            self.change_only = None
        self.ui.plainTextEdit_3.setPlainText('')

        self.parser(self.new_conf)

        if self.ui.radioButton.isChecked():
            new_conf_text = json.dumps(self.new_conf, sort_keys=False,
                                       indent=1, ensure_ascii=False, separators=(',', ': '))
        elif self.ui.radioButton_2.isChecked():
            new_conf_text = yaml.safe_dump(self.new_conf, sort_keys=False, default_flow_style=False, width=10000)

        self.ui.plainTextEdit_2.setPlainText(new_conf_text)

    def change_value(self, val_dict, value_list, value, list_index=None):
        if list_index is None:
            list_index = {}
        for level, i in enumerate(value_list):
            if level in list_index:
                val_dict = val_dict[i]
                for lst_lvl in sorted(list(list_index[level].keys())):
                    next_level = val_dict[list_index[level][lst_lvl]]
                    elem_type = type(next_level)
                    if elem_type is not dict and elem_type is not list:
                        if next_level != value:
                            self.ui.plainTextEdit_3.appendPlainText(
                                f'Значение <{next_level}> замещается <{value}>, ключи: {value_list}')
                        val_dict[list_index[level][lst_lvl]] = value
                    else:
                        val_dict = val_dict[list_index[level][lst_lvl]]
            else:
                if level != len(value_list) - 1:
                    val_dict = val_dict[i]
                else:
                    if val_dict[i] != value:
                        self.ui.plainTextEdit_3.appendPlainText(
                            f'Значение <{val_dict[i]}> замещается <{value}>, ключи: {value_list}')
                    val_dict[i] = value

    def find_old(self, val_dict, value_list, list_index=None, is_str=None):
        try:
            if self.change_only and value_list[-1] not in self.change_only:
                return
            level = None
            for dict_index, i in enumerate(value_list):
                if type(val_dict) == list:
                    level = dict_index - 1
                    for key in sorted(list(list_index[level].keys())):
                        val_dict = val_dict[list_index[level][key]]
                    val_dict = val_dict[i]
                elif type(val_dict) == dict:
                    val_dict = val_dict[i]
                    if is_str:
                        if dict_index in list_index:
                            for indx in sorted(list(list_index[dict_index].keys())):
                                val_dict = val_dict[list_index[dict_index][indx]]
            if list_index and level is not None:
                correct_list_index = {}
                for indx in list(list_index.keys()):
                    if indx <= level:
                        correct_list_index[indx] = list_index[indx]
                list_index = correct_list_index

            self.change_value(self.new_conf, value_list, val_dict, list_index)
        except KeyError as exc:
            self.ui.plainTextEdit_3.appendPlainText(
                f'{exc} нет в старой конфигурации. Ключи: {value_list}')
        except IndexError as exc:
            self.ui.plainTextEdit_3.appendPlainText(
                f'{exc} - нет элемента списка в старом конфиге. Список: {value_list}')

    def list_handle(self, pars_list, value_list, dict_level, list_index=None):
        if list_index is None:
            list_index = {}
        if dict_level not in list_index:
            list_level = 0
            list_index[dict_level] = {}
        else:
            try:
                list_level = int(max(list(list_index[dict_level].keys()))) + 1
            except ValueError as exc:
                self.ui.plainTextEdit_3.appendPlainText(
                    f'{list_index}, {exc}')
                return
        for index, list_item in enumerate(pars_list):
            list_index[dict_level][list_level] = index
            if type(list_item) == dict:
                self.parser(list_item, value_list, list_index, level=dict_level + 1)
            elif type(list_item) == list:
                self.list_handle(list_item, value_list, dict_level, list_index)
            else:
                if self.delete:
                    return
                else:
                    self.find_old(self.old_conf, value_list, list_index, is_str=True)

    def parser(self, parse_dict, value_list=None, list_index=None, level=0):
        if value_list is None:
            value_list = []
        for item in parse_dict:
            value_list = value_list[:level]
            value_list.append(item)
            next_val = parse_dict[item]
            if type(next_val) is dict:
                self.parser(next_val, value_list, list_index, level=level + 1)
            elif type(next_val) is list:
                self.list_handle(next_val, value_list, level, list_index)
            else:
                if self.delete_keys:
                    if value_list[-1] in self.delete_keys:
                        self.change_value(self.new_conf, value_list, None, list_index)
                else:
                    self.find_old(self.old_conf, value_list, list_index)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dlgMain = MainWindow()
    dlgMain.show()
    sys.exit(app.exec_())
