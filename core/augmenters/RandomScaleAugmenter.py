from .augmenter import Augmenter

import numpy as np

import random

class RandomScaleAugmenter(Augmenter):
    def __init__(self):
        #self.seed =

    def augment(self, batch: np.ndarray):
        return np.array([])