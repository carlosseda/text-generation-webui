#!/bin/bash

apt update
apt install -y build-essential
apt install -y language-pack-es
apt install -y language-pack-ca
pip install --upgrade pymupdf -q
apt install -y unzip
conda create -n textgen python=3.10.9
conda activate textgen
pip install -r requirements.txt -q
python download-model.py TheBloke/vicuna-13B-1.1-GPTQ-4bit-128g
cd repositories/ 
cd GPTQ-for-LLaMa
pip install -r requirements.txt -q
cd ../..

