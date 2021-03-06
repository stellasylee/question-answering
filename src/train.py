import sys
import os
import pickle
import time
import numpy as np

import tensorflow as tf
from tensorflow.keras.optimizers import Adam, RMSprop
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau, CSVLogger, \
    LearningRateScheduler, TensorBoard, RemoteMonitor, History, ModelCheckpoint
from tensorflow.keras import backend as K
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import to_categorical

from model.DMN import *
from model.AttentionModel.model import *
from model.AttentionModel.model2 import *
from preprocessing.preprocessing import transform

os.environ['KMP_DUPLICATE_LIB_OK']='True'

# fix "Fail to find the dnn implementation"
config = tf.compat.v1.ConfigProto()
config.gpu_options.allow_growth = True
session = tf.compat.v1.Session(config=config)

##################################
#           Hyper params         #
##################################

MASK_ZERO = True
LEARNING_RATE = 0.00001
OPTIMIZER = 'adam'
BATCH_SIZE = 32
NUM_EPOCHS = 5
MAX_CONTEXT = 50
MAX_QUESTION = 30

###################################
#       Loading dataset           #
###################################
data_path = os.path.join(os.getcwd(), '../data/merged')
# Get tokenizer
with open(os.path.join(os.getcwd(), '../data/merged/special/tokenizer.p'), 'rb') as f:
    tokenizer = pickle.load(f)

with open(os.path.join(os.getcwd(), '../data/merged/special/embedding_matrix.npy'), 'rb') as f:
    embeddings = np.load(f, allow_pickle=True)

with open(os.path.join(data_path, '../merged10/Context_Train_2.txt'), 'r') as f:
    context = f.read().strip().split('\n')
with open(os.path.join(data_path, '../merged10/Question_Train_2.txt'), 'r') as f:
    question = f.read().strip().split('\n')
with open(os.path.join(data_path, '../merged10/Answer_Train_2.txt'), 'r') as f:
    answer = f.read().strip().split('\n')
# Get dictionary length
n_words = len(tokenizer.word_index)
print(n_words)
context = transform(context, max_len=MAX_CONTEXT, tokenizer=tokenizer)
question = transform(question, max_len=MAX_QUESTION, tokenizer=tokenizer)
answer = transform(answer, max_len=1, tokenizer=tokenizer)
answer = to_categorical(tf.squeeze(answer, axis=1), num_classes=n_words)
###################################
#          Model                  #
###################################

# model = DMN(n_words, embeddings, mask_zero=MASK_ZERO, trainable=True)
model = AttentionModel3(n_words, embeddings, mask_zero=MASK_ZERO, trainable=True)

if OPTIMIZER == 'rmsprop':
    op = RMSprop(learning_rate=LEARNING_RATE)
else:
    op = Adam(learning_rate=LEARNING_RATE)

print("Compiling the model ... ")

model.compile(optimizer=op, loss='categorical_crossentropy', metrics=['categorical_accuracy', 'mae'])

path = os.getcwd()
checkpoint_dir = os.path.join(path, 'checkpoints')
log_dir = os.path.join(path, 'logs')

if not os.path.isdir(checkpoint_dir):
    os.mkdir(checkpoint_dir)
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)

# Initialize Keras callbacks
checkpoints = ModelCheckpoint(filepath='weights.epoch{epoch:02d}-val_loss{val_loss:.2f}.hdf5',
                             monitor='val_loss',
                             verbose=1,
                             save_best_only=True,
                             save_weights_only=True,
                             mode='min',
                             period=1)

early_stopping = EarlyStopping(monitor='val_loss',
                               min_delta=0.0,
                               patience=30,
                               verbose=1)

csv_logger = CSVLogger(filename='training_log.csv',
                       separator=',',
                       append=True)

remote = RemoteMonitor()

tensorboard = TensorBoard(log_dir="{}/{}".format(log_dir, time.time()),
                          histogram_freq=0,
                          batch_size=BATCH_SIZE,
                          write_graph=True,
                          write_grads=True,
                          write_images=True,
                          update_freq='batch')

reduce_lr = ReduceLROnPlateau(monitor='val_loss',
                             factor=0.5,
                             patience=10,
                             min_lr=0.00005)

def scheduler(epoch):
    if epoch == 0:
        return LEARNING_RATE
    else:
            return LEARNING_RATE * np.power(0.5, np.floor(epoch/25, dtype=np.float32), dtype=np.float32)

lr_scheduler = tf.keras.callbacks.LearningRateScheduler(scheduler)

callbacks = [lr_scheduler,
            csv_logger,
            tensorboard,
             checkpoints
            ]

validation_split = 0.2
# model.summary()
history = model.fit(x=[context, question],
                    y=answer,
                    batch_size=BATCH_SIZE,
                    epochs=NUM_EPOCHS,
                    verbose=1,
                    callbacks=callbacks,
                    shuffle=True,
                    validation_split=validation_split)

model.save('train_model_sample.h5')
# NotImplementedError: Layers with arguments in `__init__` must override `get_config`.
