#import numpy as np
#import glob
#import configparser as cp
#from shutil import copyfile
#import os
#import logging
#from core.dataset.qtdb import load_dat, split_dataset
#from core.models.rnn import get_model
#from core.util.experiments import setup_experiment
#
#from keras.callbacks import ReduceLROnPlateau, EarlyStopping, TensorBoard, CSVLogger, ModelCheckpoint

import wfdb
from os import listdir
from os.path import isfile,join,splitext

#logger = logging.getLogger('main')
#logger.setLevel(logging.DEBUG)
#config = cp.ConfigParser()
#config.read("config.ini")
#try:
#    os.makedirs(config["logging"].get("logdir"))
#except FileExistsError:
#    pass
#fh = logging.FileHandler(os.path.join(config["logging"].get("logdir"), "main.log"), mode="w+")
#fh.setLevel(logging.DEBUG)
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#fh.setFormatter(formatter)
#logger.addHandler(fh)

"""
class ECGMockSequence(Sequence):

    def __init__(self, x_set, y_set, batch_size):
        self.x, self.y = x_set, y_set
        self.batch_size = batch_size

    def __len__(self):
        return int(np.ceil(len(self.x) / float(self.batch_size)))

    def __getitem__(self, idx):
        batch_x = self.x[idx * self.batch_size:(idx + 1) * self.batch_size]
        batch_y = self.y[idx * self.batch_size:(idx + 1) * self.batch_size]

        return np.random((32, 1024, 2)), np.random()
"""

class ECGDataset:
  path = None
  dataset = []
  # currently, only takes directory path as input
  def __init__(self, path):
      if path != None:
          files = [splitext(f)[0] for f in listdir(path) if isfile(join(path,f))]
          files = list(set(files))
          files.sort()

          for f in files:
              print (f)
              try:
                  self.dataset.append(wfdb.rdrecord(join(path,f)))
              except FileNotFoundError:
                  print(join(path,f) + " is not a record")

          self.path = path

  def __add__(self, object):
      newECG = ECGDataset()
      newECG.dataset = self.dataset + object.dataset
      return newECG

  def __getitem__(self, object):
      pass
  def __len__(self):
      return len(self.dataset)
  
"""
  def create_generator()
    return ECGSequence() #
"""

if __name__ == "__main__":
    mitdb = ECGDataset("../mitdb")
    print(len(mitdb))
    #nsr2db = ECGDataset("../nsr2db")
    #print(len(nsr2db))
    nsrdb = ECGDataset("../nsr2db")
    print(len(nsrdb))
    #mitdb = wfdb.rdrecord("../mitdb/100")
    #print (mitdb.p_signal.shape)

    #mixture_db = mitdb + nsrdb  
    #mixture_db[0] # get a single record from our datset #<wfdb.io.record.Record object>

    #training_samples = 0.8 * len(mixture_db)
    #devining_samples = 0.1 * len(mixture_db)

    #  TODO: shuffle mixture_db first.
    #train_set = mixture_db[:training_samples]
    #dev_set = 
    #test_set =

    #train_generator = train_set.create_generator()

    # finish everything above by some deadline
    #model = RNN()
    #model.fit_generator(train_generator)

    """
    configuration_file = "config.ini"
    np.random.seed(0)
    config = cp.ConfigParser()
    config.read(configuration_file)
    output_dir, tag = setup_experiment(config["DEFAULT"].get("experiments_dir"))
    copyfile(configuration_file, os.path.join(output_dir, configuration_file))
    REJECTED_TAGS = tuple(config["qtdb"].get("reject_tags").split(","))
    VALID_SEGMTS = tuple(config["qtdb"].get("valid_segments").split(","))
    CATEGORIES = tuple([int(i) for i in config["qtdb"].get("category").split(",")])

    qtdbpath = config["qtdb"].get("dataset_path")
    print(f"Using qtdb dataset from {qtdbpath}")
    perct = config["qtdb"].getfloat("training_percent")
    percv = config["qtdb"].getfloat("validation_percent")

    exclude = set()
    exclude.update(config["qtdb"].get("excluded_records").split(","))

    initial_weights = config["RNN-train"].get("initial_weights")
    model_output = config["RNN-train"].get("model_output")
    epochs = config["RNN-train"].getint("epochs")
    tagged_data = load_dat(glob.glob(qtdbpath + "*.dat"), VALID_SEGMTS, CATEGORIES, exclude, REJECTED_TAGS)
    train_set, dev_set, test_set = split_dataset(tagged_data, config["qtdb"].getint("training_percent"),
                                                 config["qtdb"].getint("validation_percent"),
                                                 config["qtdb"].getint("testing_percent"))
    train_set.save(output_dir), dev_set.save(output_dir), test_set.save(output_dir)
    generator_args = {"sequence_length": config["RNN-train"].getint("sequence_length"),
                      "overlap_percent": config["RNN-train"].getfloat("overlap_percent"),
                      "batch_size": config["RNN-train"].getint("batch_size")}
    if config["qtdb"].getboolean("augmentation"):
        logger.log(logging.INFO, f"Data augmentation enabled")
        trn_generator_args = {"sequence_length": config["RNN-train"].getint("sequence_length"),
                              "random_time_scale_percent": config["qtdb"].getfloat("random_time_scale_percent"),
                              "dilation_factor": config["qtdb"].getfloat("dilation_factor"),
                              "batch_size": config["RNN-train"].getint("batch_size"),
                              "awgn_rms_percent": config["qtdb"].getfloat("awgn_rms_percent")}
        logger.log(logging.INFO, f"generator_args = {trn_generator_args}")
        train_generator = train_set.to_sequence_generator_augmented(**trn_generator_args)
    else:
        logger.log(logging.INFO, f"Data augmentation disabled")
        logger.log(logging.INFO, f"generator_args = {generator_args}")
        train_generator = train_set.to_sequence_generator(**generator_args)

    dev_generator = dev_set.to_sequence_generator(**generator_args)
    model = get_model(config["RNN-train"].getint("sequence_length"), train_set.features, len(set(CATEGORIES)), config)

    with open(os.path.join(output_dir, "model.json"), "w") as f:
        f.write(model.to_json())

    callbacks = [ModelCheckpoint(os.path.join(output_dir, "weights.{epoch:02d}.h5"), monitor='val_loss', verbose=0,
                                 save_best_only=False, save_weights_only=False, mode='auto', period=1),
                 CSVLogger(os.path.join(output_dir, f"training.csv"), separator=',', append=False),
                 ReduceLROnPlateau(monitor='val_loss', factor=0.1,
                                   patience=config["RNN-train"].getint("patientce_reduce_lr"),
                                   verbose=config["RNN-train"].getint("verbosity"), mode='min', min_delta=1e-6,
                                   cooldown=0, min_lr=1e-12),
                 TensorBoard(log_dir=os.path.join(config["RNN-train"].get("tensorboard_dir"), tag), histogram_freq=0,
                             batch_size=32, write_graph=True, write_grads=True, write_images=True, embeddings_freq=0,
                             embeddings_layer_names=None, embeddings_metadata=None, embeddings_data=None,
                             update_freq='epoch')]
    if config["RNN-train"].getboolean("early_stop"):
        logger.log(logging.INFO, f"Early Stop enabled")
        callbacks.append(
            EarlyStopping(monitor='val_loss', min_delta=1e-8, patience=5, verbose=1, mode='min',
                          baseline=None, restore_best_weights=False))
    else:
        logger.log(logging.INFO, f"Early Stop disabled")
    model.fit_generator(train_generator, steps_per_epoch=None, epochs=config["RNN-train"].getint("epochs"), verbose=1,
                        callbacks=callbacks, validation_data=dev_generator, max_queue_size=10, workers=4,
                        use_multiprocessing=False, shuffle=True)
    model.save(os.path.join(output_dir, "final_weights.h5"))
    """
