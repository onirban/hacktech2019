import logging
from typing import List, Dict
from tensorflow.keras.utils import Sequence
import numpy as np
from core.dataset.preprocessing import ECGRecordTicket, ECGDataset
from core.augmenters import AWGNAugmenter, RndInvertAugmenter, RndScaleAugmenter, RndDCAugmenter
from core.util.logger import LoggerFactory


class BatchGenerator(Sequence):
    awgn_augmenter = None
    rndinv_augmenter = None
    rndscale_augmenter = None
    rnddc_augmenter = None

    def make_record_dict(self) -> Dict:
        rec_dict = {}
        for i in range(len(self.batch_numbers)):
            rec_dict.update({k + sum(self.batch_numbers[:i]): (k, self.dataset.tickets[i]) for k in
                             range(self.batch_numbers[i])})
        return rec_dict

    def __init__(self, dataset: ECGDataset, config, enable_augmentation=False, logger=None):
        """

        :param tickets: A list holding the recordnames of each record
        :param num_segments: A list holding total number segments from each record
        :param batch_size:
        """
        self.config = config
        self.logger = LoggerFactory(config).get_logger(logger_name=logger)

        self.dataset = dataset
        self.segment_length = config["preprocessing"].getint("sequence_length")
        self.logger.log(logging.INFO, "Sequence length is %d" % self.segment_length)

        self.batch_size = config["preprocessing"].getint("batch_size")
        self.logger.log(logging.INFO, "Batch size is %d" % self.batch_size)

        self.batch_length = self.batch_size * self.segment_length
        self.batch_numbers = np.ceil(self.dataset.record_len / self.segment_length / self.batch_size).astype(int)
        self.logger.log(logging.INFO, "Number of batches from each record are %d" % self.batch_numbers)
        self.logger.log(logging.INFO, "Total # batches %d", sum(self.batch_numbers))

        self.record_dict = self.make_record_dict()
        self.logger.log(logging.INFO, "Record dictionary: ")
        for k, v in self.record_dict.items():
            self.logger.log(logging.INFO, "%s : %s" % (k, v))

        if enable_augmentation and self.config["preprocessing"].getboolean("enable_awgn"):
            self.awgn_augmenter = AWGNAugmenter(self.config["preprocessing"].getfloat("rms_noise_power_percent"))
            self.logger.log(logging.DEBUG, "AWGN augmenter enabled")
            self.logger.log(logging.DEBUG, self.awgn_augmenter)

        if enable_augmentation and self.config["preprocessing"].getboolean("enable_rndinvert"):
            self.rndinv_augmenter = RndInvertAugmenter(self.config["preprocessing"].getfloat("rndinvert_prob"))
            self.logger.log(logging.DEBUG, "Random inversion augmenter enabled")
            self.logger.log(logging.DEBUG, self.rndinv_augmenter)

        if enable_augmentation and self.config["preprocessing"].getboolean("enable_rndscale"):
            self.rndscale_augmenter = RndScaleAugmenter(self.config["preprocessing"].getfloat("scale"),
                                                        self.config["preprocessing"].getfloat("scale_prob"))
            self.logger.log(logging.DEBUG, "Random scaling augmenter enabled")
            self.logger.log(logging.DEBUG, self.rndscale_augmenter)

        if enable_augmentation and self.config["preprocessing"].getboolean("enable_rnddc"):
            self.rnddc_augmenter = RndDCAugmenter(self.config["preprocessing"].getfloat("dc"),
                                                  self.config["preprocessing"].getfloat("dc_prob"))
            self.logger.log(logging.DEBUG, "Random Dc augmenter enabled")
            self.logger.log(logging.DEBUG, self.rnddc_augmenter)

    def __len__(self):
        return sum(self.batch_numbers)

    def dump_labels(self):
        labels = []
        for _, record_batch in self.record_dict.items():
            local_batch_index, record_ticket = record_batch  # type: int, ECGRecordTicket
            max_starting_idx = record_ticket.siglen - self.segment_length
            starting_idx = min(max_starting_idx, local_batch_index * self.batch_length)
            ending_idx = min(record_ticket.siglen, starting_idx + self.segment_length * self.batch_size)
            max_starting_idx = record_ticket.siglen - self.segment_length
            real_batch_size = np.ceil((ending_idx - starting_idx) / self.segment_length).astype(int)
            for b in range(real_batch_size):
                b_start_idx = min(max_starting_idx, starting_idx + b * self.segment_length)
                b_ending_idx = min(record_ticket.siglen, b_start_idx + self.segment_length)
                segment, label = record_ticket.hea_loader.get_record_segment(record_ticket.record_name, b_start_idx,
                                                                             b_ending_idx)
                labels.append(label)
        return np.array(labels)

    def __getitem__(self, idx):
        local_batch_index, record_ticket = self.record_dict[idx]  # type: int, ECGRecordTicket
        max_starting_idx = record_ticket.siglen - self.segment_length
        starting_idx = min(max_starting_idx, local_batch_index * self.batch_length)
        ending_idx = min(record_ticket.siglen, starting_idx + self.segment_length * self.batch_size)
        real_batch_size = np.ceil((ending_idx - starting_idx) / self.segment_length).astype(int)
        batch_x = []
        labels = []
        for b in range(real_batch_size):
            b_start_idx = min(max_starting_idx, starting_idx + b * self.segment_length)
            b_ending_idx = min(record_ticket.siglen, b_start_idx + self.segment_length)
            segment, label = record_ticket.hea_loader.get_record_segment(record_ticket.record_name, b_start_idx,
                                                                         b_ending_idx)
            batch_x.append(segment)
            labels.append(label)

        batch_x = np.array(batch_x)
        labels = np.array(labels)
        if self.awgn_augmenter is not None:
            batch_x = self.awgn_augmenter.augment(batch_x)

        if self.rndinv_augmenter is not None:
            batch_x = self.rndinv_augmenter.augment(batch_x)

        if self.rndscale_augmenter is not None:
            batch_x = self.rndscale_augmenter.augment(batch_x)

        if self.rnddc_augmenter is not None:
            batch_x = self.rnddc_augmenter.augment(batch_x)
        return batch_x, labels
