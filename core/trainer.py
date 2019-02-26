from keras.models import Sequential
from keras.layers import LSTM, BatchNormalization, Dropout, Dense, Bidirectional
from keras import optimizers
import os
from core.action import Action
from core.models.callbacks import ROCAUCCallback
import logging
from core.util.logger import LoggerFactory
from keras.callbacks import ReduceLROnPlateau, EarlyStopping, TensorBoard, CSVLogger, ModelCheckpoint


class Trainer(Action):
    def __init__(self, config, experiment_env, logger=None):
        super(Trainer, self).__init__(config, experiment_env)
        self.logger = LoggerFactory(config).get_logger(logger_name=logger)

    def setup_optimizer(self, model):
        print(f"*** Adding optimizer to the model ***")
        adam = optimizers.adam(lr=self.config["RNN-train"].getfloat("initial_lr"))
        model.compile(loss='binary_crossentropy', optimizer=adam)

    def setup_model(self):
        print(f"*** Setting up deep learning model ***")
        input_shape = (self.config["preprocessing"].getint("sequence_length"), 2)
        model = Sequential()
        model.add(Bidirectional(LSTM(self.config["RNN-train"].getint("rnn_output_features")), input_shape=input_shape))
        model.add(Dropout(self.config["RNN-train"].getfloat("dropout")))
        self.logger.log(logging.INFO, f"Adding Dropout layer @dropout = {self.config['RNN-train'].getfloat('dropout')}")
        model.add(BatchNormalization())
        model.add(Dense(1024, activation='relu'))
        self.logger.log(logging.INFO, f"Adding Dense layer @ {1024} neurons")
        model.add(Dropout(self.config["RNN-train"].getfloat("dropout")))
        self.logger.log(logging.INFO, f"Adding Dropout layer @dropout = {self.config['RNN-train'].getfloat('dropout')}")
        model.add(BatchNormalization())
        model.add(Dense(1, activation='sigmoid'))
        model.summary()
        self.setup_optimizer(model)
        return model

    def setup_callbacks(self, training_set_generator, dev_set_generator):
        print(f"*** Setting up callbacks ***")
        callbacks = [
            ROCAUCCallback(training_set_generator, dev_set_generator),
            ModelCheckpoint(os.path.join(self.experiment_env.output_dir, "weights.{epoch:02d}.h5"), monitor='val_loss',
                            verbose=0, save_best_only=False, save_weights_only=False, mode='auto', period=1),
            CSVLogger(os.path.join(self.experiment_env.output_dir, f"training.csv"), separator=',', append=False),
            ReduceLROnPlateau(monitor='loss', factor=0.1,
                              patience=self.config["RNN-train"].getint("patientce_reduce_lr"),
                              verbose=self.config["RNN-train"].getint("verbosity"), mode='min',
                              cooldown=0, min_lr=1e-12),
            TensorBoard(log_dir=os.path.join(self.config["RNN-train"].get("tensorboard_dir"), self.experiment_env.tag))]
        if self.config["RNN-train"].getboolean("early_stop"):
            self.logger.log(logging.INFO, f"Early Stop enabled")
            callbacks.append(EarlyStopping(monitor='roc_auc_val', min_delta=1e-8, patience=5, verbose=1, mode='max'))
        else:
            self.logger.log(logging.INFO, f"Early Stop disabled")

        return callbacks

    def train(self, training_set_generator, dev_set_generator):
        model = self.setup_model()
        with open(os.path.join(self.experiment_env.output_dir, "model.json"), "w") as f:
            f.write(model.to_json())
        training_steps = self.config["RNN-train"].getint("train_steps")
        training_steps = None if training_steps == 0 else training_steps
        self.logger.log(logging.INFO, f"Training step = {training_steps}")
        model.fit_generator(generator=training_set_generator,
                            steps_per_epoch=training_steps,
                            validation_data=dev_set_generator,
                            epochs=self.config["RNN-train"].getint("epochs"), verbose=1,
                            callbacks=self.setup_callbacks(training_set_generator, dev_set_generator))
        final_weights = os.path.join(self.experiment_env.output_dir, "final_weights.h5")
        model.save(final_weights)
        self.logger.log(logging.INFO, f"Saving weights to {final_weights}")
        self.experiment_env.add_key(**{"final_weights": final_weights})