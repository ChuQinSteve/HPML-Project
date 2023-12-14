# -*- coding: utf-8 -*-
"""HPML Project

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1R1vm4cj3p210hP2lHV4J-jsU1Zh5Ldt9
"""

import time
import os
import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import argparse
from random import shuffle
from PIL import Image
from scipy.io import loadmat
from torch.utils.data import DataLoader, Dataset, DistributedSampler
import torch.distributed as dist
import torch.multiprocessing as mp
from torch.nn.parallel import DistributedDataParallel as DDP
from torchvision import transforms
from config import default_args
import pickle
import cProfile


# Dataset helper function
def read_image(path):
    im = cv2.imread(str(path))
    if im is None:
        print(path)
        raise Exception("Could not read image: %s" % path)
    return cv2.cvtColor(im, cv2.COLOR_BGR2RGB)


def normalize(im):
    """Normalizes images with Imagenet stats."""
    imagenet_stats = np.array([[0.485, 0.456, 0.406], [0.229, 0.224, 0.225]])
    return (im / 255.0 - imagenet_stats[0]) / imagenet_stats[1]


def denormalize(img):
    imagenet_stats = np.array([[0.485, 0.456, 0.406], [0.229, 0.224, 0.225]])
    return img * imagenet_stats[1] + imagenet_stats[0]


# Partly imported from https://github.com/Kojec1/The-Oxford-IIIT-Pets-Segmentation/
class SegmentationDataset(Dataset):
    """A custom dataset class"""

    def __init__(self, images: list, masks: list):
        # Get paths to images and masks
        self.images = images
        self.masks = masks

    def __len__(self):
        # Return the number of images
        return len(self.images)

    def __getitem__(self, index):
        # Get image and mask paths
        image_path = self.images[index]
        mask_path = self.masks[index]

        # Load the image
        image = read_image(image_path)
        image = cv2.resize(image, (224, 224))
        image = normalize(image)
        image = np.rollaxis(image, 2)

        mask = read_image(mask_path)
        mask = cv2.resize(mask, (224, 224))
        m = np.all(mask == [2, 2, 2], axis=-1)

        # Apply the mask to set these pixels to black [0, 0, 0]
        mask[m] = [0, 0, 0]

        # Apply inverse of the mask to set all other pixels to red [128, 0, 0]
        mask[~m] = [128, 0, 0]

        return image, mask


def initialize_loader(args=default_args):
    # Create a list of image paths
    img_paths = sorted([
        os.path.join(default_args.image_path, name)
        for name in os.listdir(default_args.image_path)
        if name.endswith('.jpg')
    ])

    # Create a list of mask paths
    mask_paths = sorted([
        os.path.join(default_args.mask_path, name)
        for name in os.listdir(default_args.mask_path)
        if not name.startswith('.') and name.endswith('.png')
    ])

    # Shuffle images and masks
    tmp = list(zip(img_paths, mask_paths))
    shuffle(tmp)
    img_paths, mask_paths = zip(*tmp)
    img_paths, mask_paths = list(img_paths), list(mask_paths)

    # Split the data into train and test sets
    train_imgs = img_paths[int(args.split_rate * len(img_paths)):]
    train_masks = mask_paths[int(args.split_rate * len(mask_paths)):]
    test_imgs = img_paths[:int(args.split_rate * len(img_paths))]
    test_masks = mask_paths[:int(args.split_rate * len(mask_paths))]

    # Load the train and test datasets
    train_set = SegmentationDataset(train_imgs, train_masks)
    test_set = SegmentationDataset(test_imgs, test_masks)
    print('Train images: {}\n Test images: {}'.format(len(train_set), len(test_set)))

    if (args.distributed_data_parallel):
        # Create a distributed sampler and dataloader
        train_sampler = DistributedSampler(train_set, num_replicas=args.world_size, rank=args.rank)
        test_sampler = DistributedSampler(test_set, num_replicas=args.world_size, rank=args.rank)
        
        # Initiate the train and test loaders
        train_loader = DataLoader(train_set, batch_size=args.batch_size, pin_memory = args.pin_memory, num_workers = args.num_workers, sampler=train_sampler)
        test_loader = DataLoader(test_set, batch_size=args.batch_size, pin_memory = args.pin_memory, num_workers = args.num_workers, sampler=test_sampler)
    else:
        # Initiate the train and test loaders
        train_loader = DataLoader(train_set, batch_size=args.batch_size, pin_memory = args.pin_memory, num_workers = args.num_workers)
        test_loader = DataLoader(test_set, batch_size=args.batch_size, pin_memory = args.pin_memory, num_workers = args.num_workers)

    return train_loader, test_loader

def show_mask(mask):
    # Convert from tensor image
    mask = mask.numpy()
    plt.imshow(mask, cmap='gray')  # Use a grayscale colormap
    plt.show()

def visualize_dataset(dataloader):
    """Imshow for Tensor."""
    x, y = next(iter(dataloader))
    print(x.shape)
    print(y.shape)

    fig = plt.figure(figsize=(10, 5))
    for i in range(4):
        inp = x[i].numpy().transpose((1, 2, 0))
        inp = denormalize(inp)
        mask = y[i]

        ax = fig.add_subplot(2, 2, i + 1, xticks=[], yticks=[])
        plt.imshow(np.concatenate([inp, mask], axis=1))


def plot_prediction(args, model, is_train, index_list=[0], plotpath=None, title=None):

    train_loader, valid_loader = initialize_loader(args)
    loader = train_loader if is_train else valid_loader

    images, masks = next(iter(loader))
    images = images.float()
    if args.gpu:
        images = images.to(args.rank)
    else:
        images = images.cuda()

    with torch.no_grad():
        outputs = model(images)["out"]
    output_predictions = outputs.argmax(1)

    # create a color pallette, selecting a color for each class
    palette = torch.tensor([2 ** 25 - 1, 2 ** 15 - 1, 2 ** 21 - 1])
    colors = torch.as_tensor([i for i in range(21)])[:, None] * palette
    colors = (colors % 255).numpy().astype("uint8")
    colors = [i for color in colors for i in color]

    for index in index_list:

        r = Image.fromarray(output_predictions[index].byte().cpu().numpy())
        r.putpalette(colors)

        fig = plt.figure(figsize=(10, 5))
        if title:
            plt.title(title)

        ax = fig.add_subplot(1, 3, 1, xticks=[], yticks=[])
        plt.imshow(denormalize(images[index].cpu().numpy().transpose(1, 2, 0)))

        ax = fig.add_subplot(1, 3, 2, xticks=[], yticks=[])
        plt.imshow(r)

        ax = fig.add_subplot(1, 3, 3, xticks=[], yticks=[])
        plt.imshow(masks[index])

        if plotpath:
            plt.savefig(plotpath)
            plt.close()

def show_visualization():
    print("Showing visualization of dataset...")
    train_loader, valid_loader = initialize_loader()

    visualize_dataset(train_loader)


def compute_loss(pred, gt):
    loss = F.cross_entropy(pred, gt)
    return loss


# from https://www.kaggle.com/iezepov/fast-iou-scoring-metric-in-pytorch-and-numpy
def iou_pytorch(outputs, labels):

    SMOOTH = 1e-6
    # You can comment out this line if you are passing tensors of equal shape
    # But if you are passing output from UNet or something it will most probably
    # be with the BATCH x 1 x H x W shape
    outputs = torch.argmax(outputs, 1)
    outputs = outputs.squeeze(1)  # BATCH x 1 x H x W => BATCH x H x W

    intersection = (outputs & labels).float().sum((1, 2))  # Will be zero if Truth=0 or Prediction=0
    union = (outputs | labels).float().sum((1, 2))  # Will be zero if both are 0

    iou = (intersection + SMOOTH) / (union + SMOOTH)  # We smooth our devision to avoid 0/0

    thresholded = (
        torch.clamp(20 * (iou - 0.5), 0, 10).ceil() / 10
    )  # This is equal to comparing with thresolds

    return (
        thresholded.mean()
    )  # Or thresholded.mean() if you are interested in average across the batch

def convert_to_binary(masks, thres=0.1):
    binary_masks = (
        (masks[:, 0, :, :] == 128) & (masks[:, 1, :, :] == 0) & (masks[:, 2, :, :] == 0)
    ) + 0.0
    return binary_masks.long()

def run_validation_step(args, epoch, model, loader, plotpath=None):

    model.eval()  # Change model to 'eval' mode (BN uses moving mean/var).

    losses = []
    ious = []
    with torch.no_grad():
        for i, (images, masks) in enumerate(loader):
            permute_masks = masks.permute(0, 3, 1, 2)  # to match the input size: B, C, H, W
            binary_masks = convert_to_binary(permute_masks)
            if args.distributed_data_parallel:
                images = images.to(args.rank)
                binary_masks = binary_masks.to(args.rank)
            else:
                images = images.cuda()
                binary_masks = binary_masks.cuda()
            output = model(images.float())
            pred_seg_masks = output["out"]

            output_predictions = pred_seg_masks[0].argmax(0)
            if args.loss == 'cross-entropy':
                loss = compute_loss(pred_seg_masks, binary_masks)
            iou = iou_pytorch(pred_seg_masks, binary_masks)
            losses.append(loss.data.item())
            ious.append(iou.data.item())

        val_loss = np.mean(losses)
        val_iou = np.mean(ious)

    if plotpath:
        plot_prediction(
            args, model, False, index_list=[0], plotpath=plotpath, title="Val_%d" % epoch
        )

    return val_loss, val_iou

def main(rank, world_size, args):

    # Test data loader
    if args.test_dataloader == True:
        test_dataloader(args)
        return
    
    # For further details, please refer to: https://arxiv.org/pdf/1706.05587.pds
    # Pretrained deeplabv3 model
    model = torch.hub.load('pytorch/vision:v0.10.0', 'deeplabv3_resnet101', pretrained=True)

    # Truncate the last layer and replace it with the new one.
    # To avoid 'CUDA out of memory' error, we set requires_grad=False for prevous layers
    model.classifier[4] = nn.Conv2d(256, 2, 1)
    for param in model.named_parameters():
        if not param[0].startswith('classifier.4'):
            param[1].requires_grad = False

    learned_parameters = []
    # We only learn the last layer and freeze all the other weights
    for param in model.named_parameters():
        if (param[0].startswith("classifier.4")):
            learned_parameters.append(param[1])

    # Clear the cache in GPU
    torch.cuda.empty_cache()
    device = args.gpu
    model = model.to(device)

    if (args.torch_script):
        model = torch.jit.script(model, torch.rand(64, 3, 224, 224).to(device))

    if (args.data_parallel):
        model = nn.DataParallel(model)
    
    if (args.distributed_data_parallel):
        world_size = 2
        train_DDP(rank, world_size, args, model, learned_parameters)
    else:
        train(args, model, learned_parameters)

def train_DDP(rank, world_size, args, model, learned_parameters):
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12355'

    dist.init_process_group("nccl", rank=rank, world_size=world_size)

    # Create model and move it to GPU with id 'rank'
    model = model.to(rank)
    ddp_model = DDP(model, device_ids=[rank])

    print(type(args))
    args.rank = rank
    args.world_size = world_size
    train(args, ddp_model, learned_parameters)

    dist.destroy_process_group()


def train(args, model, learned_parameters):

    # Set the maximum number of threads to prevent crash in Teaching Labs
    torch.set_num_threads(5)
    # Numpy random seed
    np.random.seed(args.seed)

    # Save directory
    # Create the outputs folder if not created already
    save_dir = "outputs/" + args.experiment_name
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Adam only updates learned_parameters
    optimizer = torch.optim.Adam(learned_parameters, lr=args.learn_rate)

    train_loader, valid_loader = initialize_loader(args)

    print("Beginning training ...")

    start = time.time()
    trn_losses = []
    val_losses = []
    val_ious = []
    best_iou = 0

    for epoch in range(args.epochs):

        # Train the Model
        model.train()  # Change model to 'train' mode
        start_tr = time.time()

        losses = []
        for i, (images, masks) in enumerate(train_loader):
            permute_masks = masks.permute(0, 3, 1, 2)  # to match the input size: B, C, H, W
            binary_masks = convert_to_binary(permute_masks)  # B, H, W
            if args.distributed_data_parallel:
                images = images.to(args.rank)
                binary_masks = binary_masks.to(args.rank)
            else:
                images = images.cuda()
                binary_masks = binary_masks.cuda()

            # Forward + Backward + Optimize
            optimizer.zero_grad()
            output = model(images.float())
            pred_seg_masks = output["out"]

            _, pred_labels = torch.max(pred_seg_masks, 1, keepdim=True)
            if args.loss == 'cross-entropy':
                loss = compute_loss(pred_seg_masks, binary_masks)
            loss.backward()
            optimizer.step()
            losses.append(loss.data.item())

        # plot training images
        if args.plot:
            plot_prediction(
                args,
                model,
                True,
                index_list=[0],
                plotpath=save_dir + "/train_%d.png" % epoch,
                title="Train_%d" % epoch,
            )

        # plot training images
        trn_loss = np.mean(losses)
        trn_losses.append(trn_loss)
        time_elapsed = time.time() - start_tr
        print(
            "Epoch [%d/%d], Loss: %.4f, Time (s): %d"
                % (epoch + 1, args.epochs, trn_loss, time_elapsed)
        )

        # Evaluate the model
        start_val = time.time()
        val_loss, val_iou = run_validation_step(
            args, epoch, model, valid_loader, save_dir + "/val_%d.png" % epoch
        )

        if val_iou > best_iou:
            best_iou = val_iou
            torch.save(
                model.state_dict(), os.path.join(save_dir, args.checkpoint_name + "-best.ckpt")
            )

        time_elapsed = time.time() - start_val
        print(
            "Epoch [%d/%d], Loss: %.4f, mIOU: %.4f, Validation time (s): %d"
                % (epoch + 1, args.epochs, val_loss, val_iou, time_elapsed)
        )

        val_losses.append(val_loss)
        val_ious.append(val_iou)

    # Plot training curve
    plt.figure()
    plt.plot(trn_losses, "ro-", label="Train")
    plt.plot(val_losses, "go-", label="Validation")
    plt.legend()
    plt.title("Loss")
    plt.xlabel("Epochs")
    plt.savefig(save_dir + "/training_curve.png")

    # Plot validation iou curve
    plt.figure()
    plt.plot(val_ious, "ro-", label="mIOU")
    plt.legend()
    plt.title("mIOU")
    plt.xlabel("Epochs")
    plt.savefig(save_dir + "/val_iou_curve.png")

    print("Saving model...")
    torch.save(
        model.state_dict(),
        os.path.join(save_dir, args.checkpoint_name + "-{}-last.ckpt".format(args.epochs)),
    )

    print("Best model achieves mIOU: %.4f" % best_iou)

def test_dataloader(args):
    print("Test dataloader........")
    
    train_loader,valid_loader = initialize_loader(args)
    #warm up
    for _ in enumerate(train_loader):
        pass
    for i in range(11):
        args.num_workers = i
        train_loader,valid_loader = initialize_loader(args)
        before_loading = time.perf_counter() # Before data loading time
        for _ in enumerate(train_loader):
            pass
        after_loading = time.perf_counter()  # After data loading time
        print("Time for {} loaders: ".format(i),after_loading - before_loading,"seconds")


def show_result(args, model):
    plot_prediction(args, model, is_train=True, index_list=[0, 1, 2, 3])
    plot_prediction(args, model, is_train=False, index_list=[0, 1, 2, 3])

def parse_arguments():
    parser = argparse.ArgumentParser('deeplabv3-resnet101')
    parser.set_defaults(**default_args)
    parser.add_argument('--batch_size', type=int)
    parser.add_argument('--num_workers', type=int)
    parser.add_argument('--pin_memory', action='store_true')
    parser.add_argument('--torch_script', action='store_true')
    parser.add_argument('--data_parallel', action='store_true')
    parser.add_argument('--distributed_data_parallel', action='store_true')
    parser.add_argument('--epochs', type=int, default=default_args.epochs)
    parser.add_argument('--test_dataloader',action='store_true')
    # parser.add_argument('--profile', choices=['cprofile', 'torch'], default='cprofile')
    # parser.add_argument('--dry-run', action='store_true')
    # parser.add_argument('--cudnn-autotuner', action='store_true',
    #                     help='Apply cuDNN autotuner.')
    return parser.parse_args()

if __name__ == '__main__':
    mp.set_start_method('spawn')
    # parser
    os.makedirs("./profile", exist_ok=True)
    args = parse_arguments()
    
    if args.test_dataloader == True:
        test_dataloader(args)

    prof = cProfile.Profile()
    prof.enable()
    if (args.distributed_data_parallel):
        world_size = 2
        mp.spawn(main, args=(world_size, args), nprocs=world_size, join=True)
    else:
        main(0, 0, args)
    prof.disable()
    prof.dump_stats(f"./profile/train.profile")

