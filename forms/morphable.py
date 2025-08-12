import logging
import json
import lxml.etree as ET
import re
import sys
import os
import importlib
from pathlib import Path
from typing import get_args

from setting import BaseSetting
from html_tool_pane import HtmlToolPane
import tool_pane_tool


class Morphable():
    '''

    '''

    pk_att_name = 'name'
    _logger = logging.getLogger('settings')

    def __repr__(self):
        return str(self.__dict__)

    @classmethod
    def siblings(cls):
        '''The siblings property'''

        parent_classes = cls.__bases__  # may be multiple inheritance
        siblings = []
        if len(parent_classes) > 0:
            parent_class = parent_classes[-1]
            siblings = parent_class.__subclasses__()
            siblings.remove(cls)
        return siblings

    @classmethod
    def variable_name(cls):

        '''The variable_name property'''
        klass_name = cls.__name__
        return klass_name[0].lower() + klass_name[1:]

    @classmethod
    def get_klass_from_element(cls, elem, klassname):
        '''
            identify class from element
            obtain module name from parent element, if available
        '''
        try:
            is_extensible = 'extensible' in elem.attrib and elem.attrib['extensible'] == 'true'
            module_name = elem.tag.lower()  # default module name
            if not is_extensible:
                # at child level - module attributed to parent container
                elem = elem.getparent()
            if klassname is None:
                klassname = module_name.title()
                if klassname.endswith('s'):
                    klassname = klassname[:-1]

            if 'module' in elem.attrib:
                module_name = elem.attrib['module']

            try:
                cur_script_fldr = Path(__file__).parent
                file_path = os.path.join(cur_script_fldr, module_name) + '.py'
                spec = importlib.util.spec_from_file_location(
                    module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as e1:
                err_line = sys.exc_info()[-1].tb_lineno
                cls._logger.error(
                    'Morphable Error loading form: ' + str(e1) + ' on line ' + str(err_line))

            if klassname in vars(module):
                klass = getattr(module, klassname)
            elif module_name.title() in vars(module):
                klass = getattr(module, module_name.title())
        except Exception as e:
            print(e)
            klass = None
        return klass

    @classmethod
    def get_klass(cls, pname):
        # identify class from pointer name
        try:
            klass_name = pname[0].upper() + pname[1:]
            module_name = Morphable.modname_from_klassname(
                klass_name)  # handles special settings classes
            try:
                cur_script_fldr = Path(__file__).parent
                file_path = os.path.join(cur_script_fldr, module_name) + '.py'
                spec = importlib.util.spec_from_file_location(
                    module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as e1:
                err_line = sys.exc_info()[-1].tb_lineno
                cls._logger.error(
                    'Morphable get_klass Error: ' + str(e1) + ' on line ' + str(err_line))

            klass = getattr(module, klass_name)
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            cls._logger.error(
                'Morphable get_klass Error: ' + str(e) + ' on line ' + str(err_line))
            klass = None
        return klass

    @classmethod
    def modname_from_klassname(cls, klassname):
        '''The modname property'''
        if klassname.lower().endswith('settings'):
            mod_name = 'settings'
        else:
            mod_name = re.sub(r'(?<!^)(?=[A-Z])', '_', klassname).lower()
        return mod_name

    @classmethod
    def from_json_str(cls, json_str):
        '''
            Construct from json string
        '''
        json_dict = json.loads(json_str)
        inst = cls()
        inst = cls.from_json_dict(inst, json_dict)
        return inst

    @classmethod
    def from_json_dict(cls, inst, json_dict):
        '''
            Construct from json dictionary
        '''
        for k, v in json_dict.items():
            if type(v) is dict:
                cls._logger.debug(
                    'populate sub object {0} with {1}'.format(k, v))
                sub_inst = getattr(inst, k)
                cls.from_json_dict(sub_inst, v)
            else:
                setattr(inst, k, v)
        return inst

    @classmethod
    def typed_xml_att_str(cls, att_str, disable_typing=False):
        # convert string to fundamental type
        if disable_typing:
            typed_var = att_str
        elif att_str is None or att_str == '' or att_str == 'null':
            # none, empty or null
            typed_var = None
        elif att_str.lower() == 'true':
            # boolean true
            typed_var = True
        elif att_str.lower() == 'false':
            # boolean false
            typed_var = False
        elif re.match('^[0-9]+$', att_str):
            # int
            typed_var = int(att_str)
        elif re.match('^[+-]?([0-9]*[.])?[0-9]+$', att_str):
            # float
            typed_var = float(att_str)
        else:
            typed_var = att_str.strip()  # string
        return typed_var

    @classmethod
    def from_xml(cls, node):
        '''
            Construct from xml node
        '''
        try:
            disable_typing = False
            inst = cls()
            data_dict = node.attrib
            for k, v in data_dict.items():
                typed_var = Morphable.typed_xml_att_str(v, disable_typing)
                setattr(inst, k, typed_var)
            for child_elem in node:
                var_name = child_elem.tag
                if child_elem.tag is not ET.Comment:
                    if not ('formable' in child_elem.attrib and child_elem.attrib['formable'] == 'false'):
                        if len(child_elem.attrib) == 0:
                            # if child element has no attributes it is a pseudo-attribute requiring cdata
                            typed_var = Morphable.typed_xml_att_str(
                                child_elem.text, disable_typing)
                            setattr(inst, var_name, typed_var)
                        elif child_elem.text is None or child_elem.text.strip() == '':
                            # nested attributed element e.g. profile > lawn
                            try:
                                klass = cls.get_klass(var_name)
                                child_obj = klass.from_xml(child_elem)
                                setattr(inst, var_name, child_obj)
                            except Exception:
                                cls._logger.error(
                                    'morphable.from_xml No klass obtainable {0} in forms'.format(var_name))
                    else:
                        cls._logger.debug(
                            'morphable.from_xml element not formable {0}'.format(var_name))
                else:
                    cls._logger.debug(
                        'morphable.from_xml comment not formable')
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            cls._logger.error('Error in from_xml: ' +
                              str(e) + ' on line ' + str(err_line))

        return inst

    def as_xml_node(self, pk_value=None):
        node = ET.Element(self.__class__.__name__.lower())
        for k, v in vars(self).items():
            if not k.startswith('_'):
                fld_type = type(v)
                self._logger.debug(
                    'xml attribute creation: {0} {1} {2}'.format(k, v, fld_type))
                if isinstance(v, Morphable):
                    self._logger.debug(k + ' is a morphable dataclass!')
                    child_node = v.as_xml_node()
                    # xml element must be named after the field-name, not the class-name
                    child_node.tag = k
                    node.append(child_node)
                elif v == []:
                    self._logger.debug(
                        'xml attribute creation: new child element: ' + k)
                    child_node = ET.Element(k)
                    child_node.set('class', get_args(
                        fld_type)[0].__name__.lower())
                    child_node.set('updatable', 'true')
                    child_node.set('extensible', 'true')
                    child_node.set('deletable', 'true')
                    node.append(child_node)
                else:
                    if k == self.pk_att_name and pk_value is not None:
                        v = pk_value
                    node.set(k, str(v))
            else:
                self._logger.debug(
                    'as_xml_node skipping private variable: ' + k)
        return node

    def as_xpath_filter(self):
        pk_name = self.pk_att_name
        pk_val = self.__dict__[pk_name]
        entity = self.__class__.__name__.lower()
        tmplt = '{0}[@{1}={2}]' if re.match('^[0-9]+$',
                                            str(pk_val)) else '{0}[@{1}="{2}"]'
        return tmplt.format(entity, pk_name, pk_val)

    def get_tool(self, fld_name, fld_type, value, pmin, pmax, pstep, read_only):

        dtype = fld_type.__name__.lower()
        enabled = not (read_only or fld_name in self._readonlys)
        label, _unit_name, unit_str = self.get_label_and_units(fld_name)
        label = label.replace('_', ' ').title()
        form_value = '' if value is None else value
        if dtype == 'bool':
            tool = tool_pane_tool.ToolPaneCheck(
                fld_name, None, label, form_value, None, enabled, {}, form_value)
        elif dtype == 'dropdown':
            tool = tool_pane_tool.ToolPaneDropdown(fld_name, None, label, form_value, "", enabled, {
                                                   'class': 'string-tool'}, [], form_value, {})
        elif dtype == 'int':
            tool = tool_pane_tool.ToolPaneNumber(fld_name, None, label, unit_str, form_value, "", "", enabled, {
                                                 "style": "text-align: right"}, pmin, pmax, pstep, form_value)
        elif dtype == 'float':
            tool = tool_pane_tool.ToolPaneNumber(fld_name, None, label, unit_str, form_value, "", "", enabled, {
                                                 "style": "text-align: right"}, pmin, pmax, pstep, form_value)
        elif dtype == 'str':
            tool = tool_pane_tool.ToolPaneString(fld_name, None, label, unit_str, form_value, "", enabled, {
                                                 'class': 'string-tool'}, form_value)

        return tool

    def as_complex_toolpane_form(self, tp_id, tp_class, var_name, mode):
        tp_config = self.as_nested_toolpane_form(var_name, mode)
        toolpane = HtmlToolPane(tp_id, tp_class, tp_config)
        return toolpane

    def as_nested_toolpane_form(self, var_name, mode, depth=0):
        this_class = self.__class__
        this_class_name = this_class.__name__
        # legend => toollist
        tp_config = {var_name + "|" + this_class_name: []}
        for fld_name, value in vars(self).items():
            try:
                private = fld_name.startswith('_')
                if not private:
                    if isinstance(value, Morphable):  # anywhere below morphable
                        child_config = value.as_nested_toolpane_form(
                            fld_name, mode, depth=depth + 1)
                        tp_config[var_name + "|" +
                                  this_class_name].append(child_config)
                    # not all properties of a class have a setting
                    elif hasattr(this_class, fld_name):
                        stg = getattr(this_class, fld_name)
                        if isinstance(stg, BaseSetting):
                            # enable non-pk widgets if not read-only
                            is_pk_widget = getattr(this_class, 'pk_att_name') == fld_name if 'pk_att_name' in vars(
                                this_class) else False
                            is_ro = fld_name in getattr(
                                this_class, '_readonlys') if '_readonlys' in vars(this_class) else False
                            enab = mode != 'view' and (
                                mode in ['create', 'duplicate'] or not is_pk_widget) and not is_ro
                            tool = stg.get_tool(fld_name, value, enab)
                            tp_config[var_name + "|" +
                                      this_class_name].append(tool)

            except Exception as e:
                err_line = sys.exc_info()[-1].tb_lineno
                err_msg = 'Error in as_nested_toolpane_form: ' + \
                    str(e) + ' on line ' + str(err_line)
                self._logger.error(err_msg)

        return tp_config

    def get_label_and_units(self, fieldname):
        # try to identify and strip units
        label = fieldname
        unit_name = 'none'
        unit_str = ''
        if fieldname.endswith('_m'):
            unit_name = 'metres'
            unit_str = 'm'
            label = fieldname[:-2]
        elif fieldname.endswith('_v'):
            unit_name = 'volts'
            unit_str = 'v'
            label = fieldname[:-2]
        elif fieldname.endswith('_mm'):
            unit_name = 'millimetres'
            unit_str = 'mm'
            label = fieldname[:-3]
        elif fieldname.endswith('_ms'):
            unit_name = 'milliseconds'
            unit_str = 'ms'
            label = fieldname[:-3]
        elif fieldname.endswith('_pc'):
            unit_name = 'percentage'
            unit_str = '%'
            label = fieldname[:-3]
        elif fieldname.endswith('_rpm'):
            unit_name = 'revs per minute'
            unit_str = 'rpm'
            label = fieldname[:-4]
        elif fieldname.endswith('_percent'):
            unit_name = 'percentage'
            unit_str = '%'
            label = fieldname[:-8]

        return label, unit_name, unit_str
