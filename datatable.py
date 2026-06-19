class DataTable(dict):
    '''
        Table-like data structure
    '''


    def __init__(self, col_names, col_dtypes):
        '''
            Constructor
        '''
        self.col_names = col_names
        self.col_dtypes = col_dtypes
        self.col_width = max([len(n) for n in col_names]) + 1
        
    def __repr__(self):
        result = ''
        for hdg in self.col_names:
            result += ('{:^' + str(self.col_width) + '} ').format(hdg.title())
        result += '\n'
        for hdg in self.col_names:
            result += ('{:^' + str(self.col_width) + '} ').format('=' * self.col_width)
        result += '\n'
        for row_key in self:
            row_data = self[row_key]
            for i, hdg in enumerate(self.col_names):
            # for cell_data_key in row_data:
                if hdg in row_data:
                    dtype = self.col_dtypes[i]
                    try:
                        cell_data = dtype(row_data[hdg])
                    except:
                        cell_data = row_data[hdg]
                    if isinstance(cell_data, bool):
                        result += ('{:^' + str(self.col_width) + '} ').format('True' if cell_data else 'False')
                    elif isinstance(cell_data, int) or isinstance(cell_data, float):
                        result += ('{:>' + str(self.col_width) + '} ').format(cell_data)
                    else:
                        truncate_data = len(cell_data) > self.col_width
                        if truncate_data:
                            disp_cell_data = cell_data[:self.col_width - 3] + '...'
                        else:
                            disp_cell_data = cell_data
                        result += ('{:<' + str(self.col_width) + '} ').format(disp_cell_data)
                else:
                    # print('No data in row {} keyed on {}'.format(row_key, hdg))
                    pass
            result += '\n'
             
        return result