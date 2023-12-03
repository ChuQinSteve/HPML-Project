import torch
import os

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

default_args = AttrDict()
args_dict = {
    "gpu": 'cuda' if torch.cuda.is_available() else 'cpu',
    "checkpoint_name": "finetune-segmentation",
    "learn_rate": 0.05,
    "batch_size": 64,
    "epochs": 10,
    "num_workers": 1,
    "loss": 'cross-entropy',
    "seed": 0,
    "plot": False,
    "experiment_name": "finetune-segmentation",
    "image_path": 'images',
    "mask_path": 'annotations/trimaps',
    "split_rate": 0.2,
}
default_args.update(args_dict)
