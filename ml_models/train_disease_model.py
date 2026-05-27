# ml_models/train_disease_model.py
import tensorflow as tf
import numpy as np
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--data_dir", type=str, required=True)
parser.add_argument("--out", type=str, default="ml_models/disease_model.h5")
parser.add_argument("--epochs", type=int, default=10)
parser.add_argument("--batch", type=int, default=16)
args = parser.parse_args()

DATA_DIR = args.data_dir
OUT_PATH = args.out
EPOCHS = args.epochs
BATCH = args.batch

print("Loading dataset from:", DATA_DIR)

train_dir = os.path.join(DATA_DIR, "train")
valid_dir = os.path.join(DATA_DIR, "valid")
test_dir = os.path.join(DATA_DIR, "test")

if not os.path.isdir(train_dir):
    raise RuntimeError(f"Train directory not found: {train_dir}")
if not os.path.isdir(valid_dir):
    raise RuntimeError(f"Valid directory not found: {valid_dir}")

train_ds = tf.keras.utils.image_dataset_from_directory(
    train_dir, image_size=(224, 224), batch_size=BATCH, label_mode='int'
)
val_ds = tf.keras.utils.image_dataset_from_directory(
    valid_dir, image_size=(224, 224), batch_size=BATCH, label_mode='int'
)

# attempt to load test if exists
test_ds = None
if os.path.isdir(test_dir):
    try:
        test_ds = tf.keras.utils.image_dataset_from_directory(
            test_dir, image_size=(224, 224), batch_size=BATCH, label_mode='int'
        )
        print("Test dataset loaded.")
    except ValueError as e:
        print("Warning: test directory found but no images or error reading it:", e)
        test_ds = None
else:
    print("No test/ directory found — continuing without test evaluation.")

class_names = train_ds.class_names
print("Classes (train):", class_names)

# Save class→index mapping
mapping_path = os.path.join("ml_models", "disease_class_indices.npy")
os.makedirs("ml_models", exist_ok=True)
np.save(mapping_path, {name: i for i, name in enumerate(class_names)})
print("Saved mapping:", mapping_path)

# Prefetch
train_ds = train_ds.prefetch(buffer_size=tf.data.AUTOTUNE)
val_ds = val_ds.prefetch(buffer_size=tf.data.AUTOTUNE)
if test_ds is not None:
    test_ds = test_ds.prefetch(buffer_size=tf.data.AUTOTUNE)

# Model: MobileNetV2 transfer learning
base = tf.keras.applications.MobileNetV2(input_shape=(224,224,3), include_top=False, weights="imagenet")
base.trainable = False

model = tf.keras.Sequential([
    base,
    tf.keras.layers.GlobalAveragePooling2D(),
    tf.keras.layers.Dense(256, activation="relu"),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.Dense(len(class_names), activation="softmax")
])

model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])

print("Starting training...")
history = model.fit(train_ds, epochs=EPOCHS, validation_data=val_ds)

if test_ds is not None:
    print("Evaluating on test set...")
    test_res = model.evaluate(test_ds)
    print("Test results:", test_res)

model.save(OUT_PATH)
print("Model saved to", OUT_PATH)
