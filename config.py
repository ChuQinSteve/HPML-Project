import torch
import os

# Configs
# Device settings
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
KWARGS = {'pin_memory': True, 'num_workers': 4} if DEVICE == 'cude' else {}

# Data paths
IMAGE_PATH = 'images'
MASK_PATH = 'annotations/trimaps'

# Data attributes
IMAGE_SIZE = (256, 256)
N_CLASSES = 3
BATCH_SIZE = 64

# Model parameters
ENC_CHANNELS = (3, 64, 128, 256, 512)
DEC_CHANNELS = (512, 256, 128, 64)

# Train / test split rate
SPLIT_RATE = 0.2

# Learning parameters
LEARNING_RATE = 0.0001
EPOCHS = 10
