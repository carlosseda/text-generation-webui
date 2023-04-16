#!/bin/bash
apt update
apt install -y build-essential
apt install -y language-pack-es
apt install -y language-pack-ca
apt install -y unzip
pip install -r requirements.txt -q
python download-model.py TheBloke/vicuna-13B-1.1-GPTQ-4bit-128g
cd repositories/ 
cd GPTQ-for-LLaMa
pip install -r requirements.txt -q
cd ../..
pip install --upgrade pymupdf -q
