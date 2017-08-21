# Find our relay_web processes (might be multiple under GUnicorn)
# and send them SIGTERM so they can clean up gracefully, which is
# very important on Raspberry Pi

from os import popen, kill, system
from signal import SIGTERM
import platform  # name conflict between os.system and platform.system
from time import sleep

if __name__ == '__main__':
    proc_table = popen('ps ax | sed 1d').read().split('\n')  # sed gets rid of the table headers
    for proc_row in proc_table:
        if 'relay_app' in proc_row:
            pid = int(proc_row.strip().split()[0])  # strip gets rid of leading spaces
            print 'Killing %d' % pid
            kill(pid, SIGTERM)
    if platform.system() != 'Darwin':  # aka macOS
        sleep(5)  # long enough?
        # print 'System shutdown'
        # system("sudo shutdown -h now")
