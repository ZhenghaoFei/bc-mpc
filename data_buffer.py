import numpy as np
import random
from collections import deque

class DataBuffer(object):
    def __init__(self):
        self.state_t = []
        self.action_t = []
        self.state_next_t = []
        self.size = 0

    def add(self, state_t, action_t, state_next_t):
        self.state_t.append(state_t)
        self.action_t.append(action_t)
        self.state_next_t.append(state_next_t)
        self.size = len(self.state_t)

    def sample(self, num):
        # Sample N
        assert (num <= self.size)
        sample_index = np.random.choice(self.size, num)
        sample_state = np.asarray([self.state_t[i] for i in sample_index])
        sample_action = np.asarray([self.action_t[i] for i in sample_index])
        sample_state_next_t = np.asarray([self.state_next_t[i] for i in sample_index])
        sample_state_delta = sample_state_next_t - sample_state
        return sample_state, sample_action, sample_state_next_t, sample_state_delta

class DataBuffer_withreward(object):
    def __init__(self):
        self.state_t = []
        self.action_t = []
        self.reward_t = []
        self.state_next_t = []
        self.size = 0

    def add(self, state_t, action_t, reward_t, state_next_t):
        self.state_t.append(state_t)
        self.action_t.append(action_t)
        self.reward_t.append(reward_t)
        self.state_next_t.append(state_next_t)
        self.size = len(self.state_t)

    def sample(self, num):
        # Sample N
        assert (num <= self.size)
        sample_index = np.random.choice(self.size, num)
        sample_state = np.asarray([self.state_t[i] for i in sample_index])
        sample_action = np.asarray([self.action_t[i] for i in sample_index])
        sample_reward = np.asarray([self.reward_t[i] for i in sample_index])
        sample_state_next_t = np.asarray([self.state_next_t[i] for i in sample_index])
        sample_state_delta = sample_state_next_t - sample_state
        return sample_state, sample_action, sample_reward, sample_state_next_t, sample_state_delta


class DataBuffer_SA(object):
    """docstring for ClassName"""
    def __init__(self, buffer_size):
        self.buffer = deque()
        self.size = 0
        self.buffer_size = buffer_size

    def add(self, state_t, action_t):
        sa = (state_t, action_t)
        if self.size <= self.buffer_size:
            self.buffer.append(sa)
            self.size += 1
        else:
            self.buffer.popleft()
            self.buffer.append(sa)

    def sample(self, batch_size):
        # Sample N
        batch = []

        if self.size < batch_size:
            batch = random.sample(self.buffer, self.size)
        else:
            batch = random.sample(self.buffer, batch_size)

        s_batch = np.array([_[0] for _ in batch])
        a_batch = np.array([_[1] for _ in batch])

        return s_batch, a_batch


    def clear(self):
        self.buffer.clear()
        self.size = 0
