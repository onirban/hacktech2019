from .augmenter import Augmenter

import numpy as np

import random


class RndScaleAugmenter(Augmenter):
    def __init__(self, scale = 1.2, scale_prob = 0.5):
        self.scale = scale

        self.scale_prob = scale_prob

    def augment(self, batch_x: np.ndarray):

        batch_aug = random.choice([batch_x, batch_x*self.scale])

        return batch_aug
