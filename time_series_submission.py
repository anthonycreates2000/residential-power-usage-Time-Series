# -*- coding: utf-8 -*-
"""Time Series Submission.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/139ODZCPZrBAaURv956sFfiHYFoxF2moh
"""

import numpy as np
import pandas as pd
import shutil
import os
import zipfile
import matplotlib.pyplot as plt
import tensorflow as tf
from google.colab import files
from keras.layers import Dense, LSTM
from sklearn.model_selection import train_test_split

print("Please put your kaggle.json file here... (filename must be kaggle.json)")
kaggle_json_file = files.upload()

destination_directory = "/root/.kaggle"
prev_kaggle_filepath = "/content/kaggle.json"
kaggle_json_destination_path = destination_directory + "/kaggle.json"

try:
  os.mkdir(destination_directory)
except FileExistsError as e:
  print("Kaggle Directory: ", e)

shutil.copyfile(prev_kaggle_filepath, kaggle_json_destination_path)
! chmod 600 /root/.kaggle/kaggle.json

os.remove(prev_kaggle_filepath)
print("kaggle.json is ready to be served!")

! pip install -q kaggle
! kaggle datasets download -d srinuti/residential-power-usage-3years-data-timeseries

zip_path = "/content/residential-power-usage-3years-data-timeseries.zip"
dataset_directory = "/tmp/dataset/"
dataset_name = "power_usage_2016_to_2020.csv"
new_dataset_name = "dataset.csv"

dataset_zipfile = zipfile.ZipFile(zip_path, "r")
dataset_zipfile.extract(dataset_name, dataset_directory)
os.rename(dataset_directory + dataset_name, dataset_directory + new_dataset_name)
print(new_dataset_name + " has been successfully created!")

dataset = dataset_directory + new_dataset_name
csv_dataset = pd.read_csv(dataset)
simplified_csv_data = csv_dataset.iloc[::2]
simplified_csv_data = simplified_csv_data.drop(["day_of_week", "notes"], axis=1)
dates = simplified_csv_data["StartDate"].values
value = simplified_csv_data["Value (kWh)"].values
simplified_csv_data

print("Data Properties ({} data): ".format(len(simplified_csv_data)))
print(simplified_csv_data.isnull().sum())

minimum_value = min(simplified_csv_data["Value (kWh)"].values)
maximum_value = max(simplified_csv_data["Value (kWh)"].values)
print("\nMin Value: ", minimum_value)
print("Max Value: ", maximum_value)
scale_data = 0.1 * (maximum_value - minimum_value)
print("Maximum Error: ", scale_data)

plt.figure(figsize=(50,5))
plt.plot(dates, value)
plt.title("Residential Power Usage for 3 Years")

class FitCallback(tf.keras.callbacks.Callback):
  def on_train_begin(self, logs=None):
    print("Training has been started!")
  def on_train_end(self, logs=None):
    print("Training has ended!")
  def on_epoch_end(self, batch, logs=None):
    maximum_error = self.maximum_error
    if (logs["mae"] <= maximum_error and logs["val_mae"] <= maximum_error):
      print("\nMae and val_mae has reached below " + str(maximum_error) + ". Good Job!")      


def windowed_dataset(series, window_size, batch_size, shuffle_buffer):
  series = tf.expand_dims(series, axis=-1)
  ds = tf.data.Dataset.from_tensor_slices(series)
  ds = ds.window(window_size + 1, shift=1, drop_remainder=True)
  ds = ds.flat_map(lambda w: w.batch(window_size + 1))
  ds = ds.shuffle(shuffle_buffer)
  ds = ds.map(lambda w: (w[:-1], w[-1:]))
  return ds.batch(batch_size).prefetch(1)

def get_dense_layer(value):
  return tf.keras.layers.Dense(value, activation="relu")

def get_output_dense_layer():
  return tf.keras.layers.Dense(1)


train_date, test_date, train_value, test_value = train_test_split(dates, value, test_size=0.2)
# 12 hours x 30 days
window_size = 360
train_value = windowed_dataset(train_value, window_size=window_size, batch_size=128, shuffle_buffer=1000)
test_value = windowed_dataset(test_value, window_size=window_size, batch_size=128, shuffle_buffer=1000)

model = tf.keras.models.Sequential([tf.keras.layers.LSTM(window_size, return_sequences=True),
                                    tf.keras.layers.LSTM(window_size),
                                    get_dense_layer(30),
                                    get_dense_layer(10),
                                    get_output_dense_layer()])

optimizer = tf.keras.optimizers.SGD(lr=1.0000e-04, momentum=0.5)

model.compile(loss=tf.keras.losses.Huber(),
              optimizer=optimizer,
              metrics=["mae"])

fit_callback = FitCallback()
fit_callback.model = model
fit_callback.maximum_error = scale_data

history = model.fit(train_value,
                    batch_size=128,
                    callbacks=[fit_callback],
                    validation_data=test_value,
                    epochs=11)

def plot_data(history_keyword):
  plt.plot(history.history[history_keyword])
  plt.title(history_keyword)
  plt.ylabel(history_keyword)
  plt.xlabel("Epochs")
  plt.legend(["Train"], loc="upper right")
  plt.show()

parameters = ["loss", "val_loss", "mae", "val_mae"]
for parameter in parameters:
  plot_data(parameter)