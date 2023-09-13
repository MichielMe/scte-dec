import os
import glob
import logging
import logging.handlers
import time
import datetime

LOG_FILENAME = 'myapp_%s.log'

dateTag = datetime.datetime.now().strftime("%Y-%b-%d_%H-%M-%S")
logging.basicConfig(filename="myapp_%s.log" % dateTag, level=logging.DEBUG)

# Set up a specific logger with our desired output level
my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.DEBUG)
'''
# Check if log exists and should therefore be rolled
needRoll = os.path.isfile(LOG_FILENAME)

# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, backupCount=5)

my_logger.addHandler(handler)

# This is a stale log, so roll it
if needRoll:    
    # Add timestamp
    my_logger.debug('\n---------\nLog closed on %s.\n---------\n' % time.asctime())

    # Roll over on application start
    my_logger.handlers[0].doRollover()

# Add timestamp
my_logger.debug('\n---------\nLog started on %s.\n---------\n' % time.asctime())
'''
# Log some messages
for i in range(20):
    my_logger.debug('i = %d' % i)

# See what files are created
logfiles = glob.glob('%s*' % LOG_FILENAME)

print ('\n'.join(logfiles))