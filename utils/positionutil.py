
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from six.moves import xrange

import numpy as np
import re
from zobrist.zobrist import *

BOARD_SIZE = 13
BATCH_SIZE = 64
INPUT_WIDTH=BOARD_SIZE + 2
INPUT_DEPTH = 5

EVAL_BATCH_SIZE=440

#5 channels:
# black stone chanes, white stone channels, black bridge, white bridge, empty position channels
class PositionUtilReward(object):
    def __init__(self, positiondata_filename, batch_size, forTest=False):
        self.data_file_name=positiondata_filename
        self.batch_size=batch_size
        self.reader=open(self.data_file_name, "r")
        self.batch_positions=np.ndarray(shape=(batch_size, INPUT_WIDTH, INPUT_WIDTH, INPUT_DEPTH), dtype=np.uint32)
        self.batch_labels=np.ndarray(shape=(batch_size,), dtype=np.uint16)
        self.currentLine=0
        self._board=np.ndarray(dtype=np.int32, shape=(INPUT_WIDTH, INPUT_WIDTH))

        self.forTest = forTest
        if forTest:
            self.batch_labelSet=np.ndarray(shape=(batch_size, ), dtype=object)
    def close_file(self):
        self.reader.close()

    def prepare_batch(self):
        self.batch_positions.fill(0)
        self.batch_labels.fill(0)
        nextEpoch=False
        for i in xrange(self.batch_size):
            line=self.reader.readline()
            line=line.strip()
            if len(line)==0:
                self.currentLine=0
                self.reader.seek(0)
                line=self.reader.readline()
                nextEpoch=True
            self._build_batch_at(i, line)
            self.currentLine +=1
        return nextEpoch

    def _build_batch_at(self, kth, line):
        nextMoveStartIndex=line.find("NextMove:")
        arr=line[:nextMoveStartIndex].strip().split()
        moveRewardStr=line[nextMoveStartIndex+len("NextMove:"):]
        #print(moveRewardStr)
        patternMoveReward=r'[B|W]\[[a-zA-Z][0-9]+\] -?[0|1]\.[0-9]+'
        RewardUnseenMove=-20.0
        tau=0.5
        result=re.findall(patternMoveReward, moveRewardStr)
        #assert(result)
        moveRewardLists=[]
        for ele in result:
            tmpArray=ele.strip().split()
            (x,y)=self._toIntPair(tmpArray[0])
            reward=float(tmpArray[1])
            moveRewardLists.append((x*BOARD_SIZE+y, reward))
            assert(-1-0.001<reward<1+0.001)

        if self.forTest:
            self.batch_labelSet[kth]=[i for i,j in moveRewardLists]

        raws = arr[0:]

        #self.batch_label_rewards[kth]=1
        #print(raws, "next:--", moveRewardStr)
        EmptyCells=[i for i in range(BOARD_SIZE**2)]
        for rawMove in raws:
            (x,y)=self._toIntPair(rawMove)
            EmptyCells.remove(x*BOARD_SIZE+y)
        for i,j in moveRewardLists:
            EmptyCells.remove(i)

        for cell in EmptyCells:
            moveRewardLists.append((cell,RewardUnseenMove))

        p=np.ndarray(shape=(len(moveRewardLists),), dtype=np.float32)
        a=np.ndarray(shape=(len(moveRewardLists),), dtype=np.float32)
        k=0
        for i,j in moveRewardLists:
            a[k]=i
            p[k]=np.exp(j/tau)
            k += 1
        p=p/np.sum(p)
        label=np.random.choice(a, 1, False, p)
        self.batch_labels[kth]=label
        #print("sampled label:", label, (chr(ord('a')+label//BOARD_SIZE), label%BOARD_SIZE+1))


        self.batch_positions[kth, 1:INPUT_WIDTH - 1, 1:INPUT_WIDTH - 1, INPUT_DEPTH - 1] = 1
        # black occupied
        self.batch_positions[kth, 0:INPUT_WIDTH, 0, 0] = 1
        self.batch_positions[kth, 0:INPUT_WIDTH, INPUT_WIDTH - 1, 0] = 1
        # white occupied
        self.batch_positions[kth, 0, 1:INPUT_WIDTH - 1, 1] = 1
        self.batch_positions[kth, INPUT_WIDTH - 1, 1:INPUT_WIDTH - 1, 1] = 1
        self._set_board(raws)
        turn = HexColor.BLACK
        for raw in raws:
            (x, y) = self._toIntPair(raw)
            x, y = x + 1, y + 1
            ind = 0 if turn == HexColor.BLACK else 1
            self.batch_positions[kth, x, y, ind] = 1
            self.batch_positions[kth, x, y, INPUT_DEPTH - 1] = 0
            turn = HexColor.EMPTY - turn

        ind_bridge_black=2
        ind_bridge_white=3
        for i in xrange(INPUT_WIDTH-1):
            for j in xrange(INPUT_WIDTH-1):
                p1=self._board[i,j], self._board[i+1,j], self._board[i,j+1], self._board[i+1,j+1]
                if p1[0]==HexColor.BLACK and p1[3]==HexColor.BLACK and p1[1]!=HexColor.WHITE and p1[2]!=HexColor.WHITE:
                    self.batch_positions[kth,i,j,ind_bridge_black]=1
                    self.batch_positions[kth,i+1,j+1, ind_bridge_black]=1
                if p1[0]==HexColor.WHITE and p1[3]==HexColor.WHITE and p1[1]!=HexColor.BLACK and p1[2]!=HexColor.BLACK:
                    self.batch_positions[kth,i,j,ind_bridge_white]=1
                    self.batch_positions[kth,i+1,j+1,ind_bridge_white]=1
                if j-1>=0:
                    p2=self._board[i,j], self._board[i+1,j-1], self._board[i+1,j], self._board[i,j+1]
                    if p2[1] == HexColor.BLACK and p2[3] == HexColor.BLACK and p2[0] != HexColor.WHITE and p2[2] != HexColor.WHITE:
                        self.batch_positions[kth, i+1, j-1, ind_bridge_black] = 1
                        self.batch_positions[kth, i, j+1, ind_bridge_black] = 1
                    if p2[1] == HexColor.WHITE and p2[3] == HexColor.WHITE and p2[0] != HexColor.BLACK and p2[2] != HexColor.BLACK:
                        self.batch_positions[kth, i+1, j-1, ind_bridge_white] = 1
                        self.batch_positions[kth, i, j+1, ind_bridge_white] = 1

    def _set_board(self, raws):
        self._board.fill(0)
        self._board[0:INPUT_WIDTH,0]=HexColor.BLACK
        self._board[0:INPUT_WIDTH,INPUT_WIDTH-1]=HexColor.BLACK
        self._board[0,1:INPUT_WIDTH-1]=HexColor.WHITE
        self._board[INPUT_WIDTH-1, 1:INPUT_WIDTH-1]=HexColor.WHITE
        turn=HexColor.BLACK
        for raw in raws:
            (x,y)=self._toIntPair(raw)
            x,y=x+1,y+1
            self._board[x,y]=turn
            turn=HexColor.EMPTY-turn


    #B[c3]=> c3 => ('c-'a')*boardsize+(3-1) , W[a11]=> a11
    def _toIntPair(self, raw):
        x=ord(raw[2].lower())-ord('a')
        y=int(raw[3:-1])-1
        return (x,y)

if __name__ == "__main__":
    datatest=PositionUtilReward(positiondata_filename="data/8x8/positions1.txt", batch_size=BATCH_SIZE)
    nextEpoch=False
    while nextEpoch==False:
        nextEpoch=datatest.prepare_batch()
        print("offset ", datatest.reader.tell(), "line:", datatest.currentLine)
