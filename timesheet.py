import sys
import time


class Timesheet():
    '''
        Represents an ordered set of absolute times
        Used to measure apportionment of time through a process
    '''

    def __init__(self, setname=None):
        '''
            Capture start time
        '''
        self.setname = setname
        if self.setname is not None:
            self.checkpoints = {}
            self.start_time = time.time()

    def add(self, name):
        '''
            add an entry
        '''
        if self.setname is not None:
            self.checkpoints[name] = time.time()

    def __repr__(self):
        if self.setname is None:
            result = 'Empty Timesheet'
        else:
            '''
                Add printed entry and...
                loop through entries calculating relative time cost
            '''
            self.add('self.printed')
            tmplt = '{0}: {1:.3f}s {2:>3.0f}%\n'
            extra_chars = 14
            total = list(self.checkpoints.values())[-1] - self.start_time
            widest = max([len(k) for k in self.checkpoints])
            result = '\n' + (widest + extra_chars) * '-'
            result += '\n' + self.setname.center(widest + extra_chars, ' ')
            result += '\n' + (widest + extra_chars) * '-' + '\n'
            for i, (k, v) in enumerate(self.checkpoints.items()):
                if i == 0:
                    elapsed = v - self.start_time
                else:
                    elapsed = v - list(self.checkpoints.values())[i - 1]
                result += tmplt.format(k.rjust(widest, ' '),
                                       elapsed, 100 * elapsed / (total + 0.000001))

            result += (widest + extra_chars) * '=' + '\n'
            result += tmplt.format('Total'.rjust(widest, ' '), total, 100)

        return result


class Timesheet2():
    '''
        Represents an ordered set of absolute times
        Used to measure apportionment of time through a process, or loop
    '''

    def __init__(self, setname=None):
        '''
            Capture start time
        '''
        self.setname = setname
        if self.setname is not None:
            self.checkpoints = {}
            self.start_times = [time.time()]

    def restart(self):
        '''
            add new start time
        '''
        if len(self.checkpoints) == 0:
            self.start_times[0] = time.time()  # just refresh
        else:
            self.start_times.append(time.time())

    def add(self, name):
        '''
            add an entry
        '''
        if self.setname is not None:
            if name in self.checkpoints:
                self.checkpoints[name].append(time.time())
                # if this is the first entry, and we haven't restarted, auto-restart
                if (list(self.checkpoints.keys()).index(name) == 0 and
                        len(self.start_times) < len(self.checkpoints[name])):
                    self.restart()
            else:
                self.checkpoints[name] = [time.time()]

    def __repr__(self):
        if self.setname is None or len(self.checkpoints) == 0:
            result = 'Empty Timesheet'
        else:
            '''
                Add printed entry and...
                loop through entries calculating relative time cost
            '''
            result = ''
            try:
                tmplt = '{0}: {1:.3f}s {2:>3.0f}%\n'
                extra_chars = 14
                self.finishes = [cpl for cpl in list(
                    self.checkpoints.values())[-1]]
                self.totals = [f - self.start_times[i]
                               for i, f in enumerate(self.finishes)]
                total = sum(self.totals)
                widest = max([len(k) for k in self.checkpoints])
                result = '\n' + (widest + extra_chars) * '-'
                result += '\n' + self.setname.center(widest + extra_chars, ' ')
                result += '\n' + (widest + extra_chars) * '-' + '\n'
                for i, (k, v) in enumerate(self.checkpoints.items()):
                    if i == 0:
                        elapseds = [v[j] - self.start_times[j]
                                    for j in range(len(v))]
                        elapsed = sum(elapseds)
                    else:
                        elapseds = [
                            v[j] - list(self.checkpoints.values())[i - 1][j] for j in range(len(v))]
                        elapsed = sum(elapseds)
                    result += tmplt.format(k.rjust(widest, ' '),
                                           elapsed, 100 * elapsed / (total + 0.000001))

                result += (widest + extra_chars) * '=' + '\n'
                result += tmplt.format(((str(len(self.start_times)) if len(
                    self.start_times) > 1 else '') + ' totals').rjust(widest, ' '), total, 100)

            except Exception as e:
                err_line = sys.exc_info()[-1].tb_lineno
                err_msg = 'Error in Timesheet2 __repr__: ' + \
                    str(e) + ' on line ' + str(err_line)
                result = err_msg

        return result
