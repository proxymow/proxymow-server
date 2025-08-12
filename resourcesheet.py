import time

from utilities import get_mem_usage

class Timesheet():
    '''
        Represents an ordered set of absolute times
        Used to measure apportionment of time & memory through a process
    '''

    def __init__(self, setname=None):
        '''
            Capture start time, and used memory
        '''
        self.setname = setname
        if self.setname is not None:
            self.checkpoints = {}
            self.memcheckpoints = {}
            self.start_time = time.time()
            self.start_mem_mb, _ = get_mem_usage()

    def add(self, name):
        '''
            add an entry
        '''
        if self.setname is not None:
            self.checkpoints[name] = time.time()
            self.memcheckpoints[name], _ = get_mem_usage() 

    def __repr__(self):
        if self.setname is None:
            result = 'Empty Resourcesheet'
        else:
            '''
                Add printed entry and...
                loop through entries calculating relative time & memory cost
            '''
            self.add('self.printed')
            tmplt = '{}: {:.3f}s {:>3.0f}% {:>3.3f}Mb\n'
            extra_chars = 21
            total = list(self.checkpoints.values())[-1] - self.start_time
            total_mem = list(self.memcheckpoints.values())[-1] - self.start_mem_mb
            widest = max([len(k) for k in self.checkpoints])
            result = '\n' + (widest + extra_chars) * '-'
            result += '\n' + self.setname.center(widest + extra_chars, ' ')
            result += '\n' + (widest + extra_chars) * '-' + '\n'
            for i, (k, v) in enumerate(self.checkpoints.items()):
                if i == 0:
                    elapsed = v - self.start_time
                    used_mem = list(self.memcheckpoints.values())[i] - self.start_mem_mb
                else:
                    elapsed = v - list(self.checkpoints.values())[i - 1]
                    used_mem = list(self.memcheckpoints.values())[i] - list(self.memcheckpoints.values())[i-1]
                result += tmplt.format(k.rjust(widest, ' '),
                                       elapsed, 
                                       100 * elapsed / (total + 0.000001),
                                       used_mem
                                       )

            result += (widest + extra_chars) * '=' + '\n'
            result += tmplt.format('Total'.rjust(widest, ' '), total, 100, total_mem)

        return result