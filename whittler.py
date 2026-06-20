import os
import sys
from pathlib import Path
import importlib.util
import numpy as np
from math import floor, ceil

from dupe_key_dict import DupeKeyDict
from datatable import DataTable
import utilities as ut
from timesheet import Timesheet2

class Whittler(object):
    '''
        whittles the number of contours hopefully down to one 
    '''

    @classmethod
    def init(cls, logger, short_circuit=False):
        cls.logger = logger
        cls.short_circuit = short_circuit
        cls.stock_cols = ['Thumbnail', 'Ident', 'Accept']
        cls.stock_types = [str, str, bool]
        
        # mine contour_assessments folder for plug-in assessments
        cur_script_fldr = Path(__file__).parent
        rel_path = 'contour_assessments'
        cls.abs_path = (cur_script_fldr / rel_path).resolve()
        
        if logger:
            logger.info('absolute assessments path: {}'.format(cls.abs_path))            

        # cache modules
        cls.mod_cache = Whittler.get_modules(Whittler)
        
        # cache process order
        cls._proc_order = Whittler.get_process_order(Whittler)
        
        if logger:
            logger.debug('module cache: {}'.format(cls.mod_cache))
            logger.debug('module process order: {}'.format(cls._proc_order))

    @classmethod
    def assessment_module_names(cls):
        return [os.path.basename(x)[0:-3]
                        for x in cls.abs_path.glob('*.py')]
        
    @classmethod
    def assessment_names(cls, ordered=False):
        names = [' '.join(word.title() for word in name.split(
            '_')) for name in cls.assessment_module_names()]
        if 'Template' in names: names.remove('Template')
        if ordered:
            result = [n for _, n in sorted(zip(cls._proc_order, names))]
        else: 
            result = names
        return result
    
    def get_modules(self):
        mod_dict = {}
        for i, rel_mod_name in enumerate(self.assessment_module_names()):    
            try:
                file_path = os.path.join(
                    self.abs_path, rel_mod_name) + '.py'
                module_name = rel_mod_name
                spec = importlib.util.spec_from_file_location(
                    module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                mod_dict[self.assessment_names()[i]] = module
            except Exception as e1:
                err_line = sys.exc_info()[-1].tb_lineno
                err_msg = 'Error loading plug-in: ' + str(e1) + ' on line ' + str(err_line)
                if self.logger:
                    self.logger.error(err_msg)
                else:
                    print(err_msg)
        return mod_dict
    
    def get_process_order(self):
        assessment_order = []
        for assmt_name in self.assessment_names():
            module = self.mod_cache[assmt_name]
            try:
                proc_order = module.process_order
            except:
                proc_order = -1
            assessment_order.append(proc_order)
        return assessment_order
    
    def __init__(self):
        '''
            Constructor
        '''
        # create datatable
        col_names = list(self.stock_cols)
        col_dtypes = list(self.stock_types)
        for n in self.assessment_names(True):
            col_names.append(n)
            col_dtypes.append(float)
            col_names.append(n + '_tt')
            col_dtypes.append(str)
            col_names.append(n + '_acc')
            col_dtypes.append(bool)
        self.dt = DataTable(col_names, col_dtypes)
    
    @property
    def accepted_states(self):
        result = []
        for row_dict in self.dt.values():
            result.append(bool(row_dict['Accept']))
        return result
    
    @property
    def acceptance_order_index(self):
        try:
            result = np.argsort(~np.array(self.accepted_states)).tolist()
        except:
            result = []
        return result
    
    @property
    def accepted_index(self):
        try:
            result = [i for i, x in enumerate(self.accepted_states) if x]
        except:
            result = []
        return result

    @property
    def num_accepted(self):
        return int(np.count_nonzero(self.accepted_states))
    
    def process(self, contours, img_arr):
        # perform assessment on each contour and add results to datatable
        try:
            self.timesheet = Timesheet2('Whittler Assessments')
            for i, contour in enumerate(contours):
                self.timesheet.restart()
                # convert the global contour to a local one with origin (r0, c0)
                min_y, min_x = np.min(contour, axis=0)
                max_y, max_x = np.max(contour, axis=0)
                local_contour = contour - (min_y, min_x)
                
                # obtain the image array around local contour
                top_y = floor(min_y)
                left_x = floor(min_x)
                bottom_y = ceil(max_y)
                right_x = ceil(max_x)
                local_sub_array = img_arr[top_y: bottom_y, left_x: right_x]
                
                # save img array as base64 string
                thumbnail = ut.convert_array_to_base64(local_sub_array, (24, 24))
                
                row = {"Thumbnail": thumbnail, "Ident": i, "Accept": True, }
                self.timesheet.add('preparation')
                acceptance = True
                for assmt_name in self.assessment_names(True): # ordered
                    if acceptance or self.short_circuit is False:
                        module = self.mod_cache[assmt_name]
                        measure, tooltip, acceptance = module.assess(local_contour, local_sub_array, (top_y, left_x))
                    else:
                        measure, tooltip, acceptance = '', '{} not processed'.format(assmt_name), False
                    if 'float' in type(measure).__name__:
                        row[assmt_name] = round(measure, 2)
                    else:
                        row[assmt_name] = str(measure)
                    row[assmt_name + '_acc'] = bool(acceptance)
                    row[assmt_name + '_tt'] = tooltip
                    row['Accept'] = row['Accept'] and acceptance
                    self.timesheet.add(assmt_name)
        
                self.dt[i] = row
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            err_msg = 'Error processing plug-in assessment modules: ' + str(e) + ' on line ' + str(err_line)
            if self.logger:
                self.logger.error(err_msg)
            else:
                print(err_msg)
                
    def render(self, ss_index):
        row_list = []
        try:
            for contour_idx in self.acceptance_order_index:
                try:
                    contour_row = self.dt[list(self.dt.keys())[contour_idx]]
                    row_list.append(list(self.render_row(contour_row, ss_index, contour_idx).values()))
                except Exception as e:
                    err_line = sys.exc_info()[-1].tb_lineno
                    self.logger.warning('render key missing ' +
                                   str(e) + ' on line ' + str(err_line))
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.logger.error('Error in render: ' +
                           str(e) + ' on line ' + str(err_line))
        return row_list

    def render_row(self, contour_row, ss_index=0, row_index=0):
        debug = False
        # set empty to show all columns for debugging
        hidden_col_prefix = '' if debug else '_'
        _variant = self.__class__.__name__

        # conditional inclusion not permitted - a column must be populated
        row_attributes = {}
        
        row_class = 'whittler-row row-rejected'
        if 'Accept' in contour_row and contour_row['Accept']:
            row_class = 'whittler-row row-accepted'
                
        advice = 'hover over to highlight {}-{} in Contour View and Freeze...'.format(ss_index, row_index)
                
        row_attributes[hidden_col_prefix + '@row_class'] = row_class
        row_attributes[hidden_col_prefix + '@row_title'] = advice
        row_attributes[hidden_col_prefix + '@row_onmouseover'] = "highlight({})".format(row_index)
        row_attributes[hidden_col_prefix + '@row_onmouseout'] = "unhighlight({})".format(row_index)

        # merge extra items and row attributes into new dict
        dkdict = DupeKeyDict(row_attributes)
        if 'Thumbnail' in contour_row:
            thumb_tmplt = '''
                <div style="text-align: center;">
                    <img src="data:image/jpeg;charset=utf-8;base64,{}" alt="Thumbnail" />
                </div>'''            
            dkdict['Thumbnail'] = thumb_tmplt.format(contour_row['Thumbnail']) 
        else:
            dkdict['Thumbnail'] = ''
        dkdict['Ident'] = '{}-{}'.format(ss_index, row_index)
        for col_name in self.assessment_names(True):
            dkdict[col_name] = contour_row[col_name]
            acc_col_name = col_name + '_acc'
            if acc_col_name in contour_row and contour_row[acc_col_name]:
                dkdict[hidden_col_prefix + '@cell_class'] = 'cell-accepted'                    
            else:
                dkdict[hidden_col_prefix + '@cell_class'] = 'cell-rejected'
            ttip_col_name = col_name + '_tt'
            if ttip_col_name in contour_row:
                ttip = contour_row[ttip_col_name]
                dkdict[hidden_col_prefix + '@cell_title'] = ttip
            else:
                dkdict[hidden_col_prefix + '@cell_title'] = ''
            
        return dkdict
    
    def __repr__(self):
        result = str(self.dt)
        result += 'accepted states: {}\n'.format(self.accepted_states)
        result += 'acceptance order index: {}\n'.format(self.acceptance_order_index)
        result += 'acceptance index: {}\n'.format(self.accepted_index)
        result += str(self.timesheet)
        return result