# High Performance Machine Learning Project

**Author:** Chu Qin(cq2238), Ziyu Liu(zl3220)

## Project Description

This project involves a model optimization task using DeepLabV3 ResNet101 model as the backbone for a transfer learning segmentation task. We utilize PyTorch and other libraries to create and train a segmentation model. The project's primary focus is on enhancing performance and efficiency of the model.

We digged through in total of four optimization techniques including:
- Opmized number of dataloaders
- Pinned memory
- Torch Script for the model
- Distributed training

## Features

- **Data Loading and Processing:** Defines custom functions for loading and preprocessing images and segmentation masks.
- **Model Customization:** Utilizes a pre-trained DeepLabV3 ResNet101 model with a customized classifier layer.
- **Performance Optimization:** Includes features like multi-processing data loading, CUDA support, pinned memory for data transfer, TorchScript conversion for enhanced performance, and distributed training over multiple GPUs.
- **Visualization:** Defines functions to visualize training and validation results, including segmentation masks.
- **Evaluation Metrics:** Defines functions to visualize Intersection over Union (IoU) for model evaluation.
- **Profiling:** Integrates cProfile for performance profiling of training runs.

## Outline of respository

- Root
    - `main.py`: The main script to run the project.
    - `config.py`: The parameter configurations needed for the model.
    - `prepare.sh`: The shell script preparing the Oxford animal dataset for the project, which includes removing erroneous data.
    - `run.sh`: The shell script that starts a dry run of the model.

## Example commands

- Dry run: 
    - ./run.sh
    - python main.py
- Run with different arguments:
    - python main.py --num_workers=8 --pin_memory --torch_script --data_parallel

## Results

- Model Inference:
    ![](result1.png)
    ![](result2.png)
    ![](result3.png)
    ![](result4.png)

- Model Performance:
    - Benchmark -- original
        ![](result6.png)
    - With Num-workers (optimized = 8)
        ![](result7.png)
    - With Num-workers and Pinned-memory
        ![](result8.png)
    - With Num-workers, Pinned-memory and Torch Script
        ![](result9.png)
    - With Num-workers, Pinned-memory, Torch Script and Data Parallel
        ![](result10.png)
    - With Num-workers, Pinned-memory, Torch Script and Distributed Data Parallel
        ![](result13.png)
