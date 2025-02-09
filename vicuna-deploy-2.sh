#!/bin/bash
apt update
apt install -y build-essential
apt install -y language-pack-es
apt install -y language-pack-ca
apt install -y unzip
pip install -r requirements.txt -q
pip install -i https://test.pypi.org/simple/ bitsandbytes-cuda113 -q
python download-model.py TheBloke/vicuna-13B-1.1-GPTQ-4bit-128g
cd repositories/ 
cd GPTQ-for-LLaMa
pip install -r requirements.txt -q
cd ../..
pip install --upgrade pymupdf -q
python server.py --model TheBloke_vicuna-13B-1.1-GPTQ-4bit-128g --wbits 4 --groupsize 128 --model_type LlaMa --listen --no-stream &
