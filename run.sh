#!/bin/bash

# check and download images.tar.gz
if [ ! -f "images.tar.gz" ]; then
    echo "Downloading The Oxford-IIIT Pet Dataset (images)..."
    wget https://thor.robots.ox.ac.uk/~vgg/data/pets/images.tar.gz
    tar xvzf images.tar.gz
else
    echo "images.tar.gz already exists."
fi

#check and download annotations.tar.gz
if [ ! -f "annotations.tar.gz" ]; then
    echo "Downloading The Oxford-IIIT Pet Dataset (annotations)..."
    wget https://thor.robots.ox.ac.uk/~vgg/data/pets/annotations.tar.gz
    tar xvzf annotations.tar.gz
else
    echo "annotations.tar.gz already exists."
fi

!rm images/Egyptian_Mau*.jpg
!rm annotations/trimaps/Egyptian_Mau*.png
!rm images/Abyssinian_*.jpg
!rm annotations/trimaps/Abyssinian_*.png

#run main.py Python script
echo "Running main.py..."
python main.py
