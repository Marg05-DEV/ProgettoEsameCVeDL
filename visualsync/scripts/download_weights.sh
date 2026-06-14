mkdir -p ./preprocess/pretrained
mkdir -p ./Tracking-Anything-with-DEVA/saves/

wget https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt -O ./preprocess/pretrained/sam2.1_hiera_large.pt
wget https://github.com/hkchengrex/Tracking-Anything-with-DEVA/releases/download/v1.0/DEVA-propagation.pth -O ./Tracking-Anything-with-DEVA/saves/DEVA-propagation.pth

wget https://download.europe.naverlabs.com/ComputerVision/MASt3R/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth -O ./preprocess/pretrained/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth