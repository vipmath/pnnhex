from __future__ import print_function
from __future__ import division
from __future__ import absolute_import



BOARD_SIZE = 13
BATCH_SIZE = 128
PADDINGS = 2
INPUT_WIDTH=BOARD_SIZE + 2*PADDINGS
INPUT_DEPTH = 9

EVAL_BATCH_SIZE=440