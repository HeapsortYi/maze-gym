from __future__ import division
from rl.policy import *

class BoltzmannQPolicy2(Policy):
    def __init__(self):
        super(BoltzmannQPolicy2, self).__init__()
        self.minq = 1e20
        self.maxq = -1e20

    def select_action(self, q_values):
        assert q_values.ndim == 1
        nb_actions = q_values.shape[0]
        q_values = q_values.astype('float64')
        if np.isnan(q_values).any():
            print q_values
        if self.minq > np.min(q_values):
            self.minq = np.min(q_values)
            print self.minq, self.maxq
        if self.maxq < np.max(q_values):
            self.maxq = np.max(q_values)
            print self.minq, self.maxq
        q_values -= np.max(q_values)
        exp_values = np.exp(q_values)
        probs = exp_values / np.sum(exp_values)
        action = np.random.choice(range(nb_actions), p=probs)
        return action

    def get_config(self):
        config = super(BoltzmannQPolicy2, self).get_config()
        return config

class EpsBoltzmannQPolicy2(Policy):
    def __init__(self, eps=.1):
        super(EpsBoltzmannQPolicy2, self).__init__()
        self.eps = eps

    def select_action(self, q_values):
        assert q_values.ndim == 1
        nb_actions = q_values.shape[0]
        if np.random.uniform() < self.eps:
            action = np.random.random_integers(0, nb_actions - 1)
        else:
            q_values = q_values.astype('float64')
            q_values -= np.max(q_values)
            exp_values = np.exp(q_values)
            probs = exp_values / np.sum(exp_values)
            action = np.random.choice(range(nb_actions), p=probs)
        return action

    def get_config(self):
        config = super(EpsBoltzmannQPolicy2, self).get_config()
        config['eps'] = self.eps
        return config

