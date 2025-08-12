import time
import socket
import virtual.vmotion_lib
from virtual.vmotion_lib import init, likely
import virtual.vlogs
from virtual.vlogs import trace_virtual

COMMS_REALISM_ENABLED = False  # True | False
COMMS_FAIL_LIKELIHOOD_PC = 0  # 100 = certainty, 0 = never, 2 = reasonable
COMMS_FAIL_DURATION_SECS = 30  # typically 30


def log(msg):
    trace_virtual(msg)


def process_cmd(multi_cmd):
    result = ''
    try:
        cmds = multi_cmd.split('!')
        for cmd in cmds:
            res = process(cmd)
            result += str(res) + '!'
    except Exception as e:
        result = str(e)
    return result.rstrip('!')


def process(cmd):
    # determine instruction and make call
    msg = 'Processing: ' + cmd
    log(msg)
    cmd_parts = cmd.split('(')
    if (len(cmd_parts) == 1):
        log('Error in cmd: ' + cmd)
    else:
        instr = cmd_parts[0]
        log('Instruction: ' + instr)
        param_str = cmd_parts[1][:-1]
        log('Parameters: ' + param_str)
        params = []
        if param_str != '':
            if ',' not in param_str:
                log('Single parameter: ' + param_str)
                params = [param_str]
            else:
                log('Splitting Multiple parameters...')
                params = [float(x) for x in param_str.split(',')]
        else:
            log('No parameters...')

        result = getattr(virtual.vmotion_lib, instr)(*params)
        log('Result: ' + str(result))
    return result


def main(work_folder_path):

    # initialise log
    virtual.vlogs.init(work_folder_path)

    # initialise motion lib
    init()

    # initialise socket
    HOST = '0.0.0.0'  # Standard loopback interface address (localhost)
    PORT = 5005        # Port to listen on (non-privileged ports are > 1023)
    ACK = 'ACK'

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setblocking(True)
    s.bind((HOST, PORT))
    log('listening on UDP Host {0}:{1}'.format(HOST, PORT))
    comms_went_offline = -1
    keep_going = True
    while keep_going:
        try:
            log('awaiting connection...')
            line, addr = s.recvfrom(1024)
            if line:
                cmd = line.decode("utf-8").strip()
                # Comms realism
                if comms_went_offline > 0:
                    # back online?
                    if time.time() - comms_went_offline > COMMS_FAIL_DURATION_SECS:
                        comms_went_offline = -1
                else:
                    comms_fail_likely = likely(COMMS_FAIL_LIKELIHOOD_PC)
                    if comms_fail_likely:
                        comms_went_offline = time.time()

                if cmd[0] == '>':
                    # Synchronous Request - process before replying
                    if COMMS_REALISM_ENABLED and comms_went_offline > 0 and cmd != '>get_pose()':
                        msg = '*** Realism - Synchronous Comms Failed'
                        log('\t' + msg)
                    else:
                        cmd = cmd[1:]
                        log('Incoming synchronous request: ' + cmd)
                        result = process_cmd(cmd)
                        log('Processed result: ' + str(result))
                        response = str(result).encode()
                        log('Sending response...')
                        s.sendto(response, addr)
                        log('Sent response: ' + str(result))
                else:
                    # ASynchronous Request - process after replying ack
                    # Comms realism
                    if COMMS_REALISM_ENABLED and comms_went_offline > 0 and not cmd.startswith('set_pose('):
                        msg = '*** Realism - Asynchronous Comms Failed'
                        log('\t' + msg)
                    else:
                        log('Incoming asynchronous request: ' +
                            cmd + ' from ' + str(addr))
                        log('Sending acknowledgement...')
                        sent_bytes = s.sendto(ACK.encode(), addr)
                        log('Sent acknowledgement: {}'.format(sent_bytes))
                        result = process_cmd(cmd)
                        log('Processed result: ' + str(result))
            else:
                log('Incoming request breaking!')
                break
        except Exception as e:
            print(e)


if __name__ == "__main__":
    main()
