import os
import pickle
import skimage.io
import scipy.misc 
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.autograd import Variable
import numpy as np
import sys
import pickle
from collections import defaultdict


text_path = sys.argv[1]
os.environ['CUDA_VISIBLE_DEVICES'] = "0"

if not os.path.exists('./samples'):
	os.mkdir('./samples')
	print("./samples makedir")

class generator(nn.Module):
    # initializers
    def __init__(self, d=64):
        super(generator, self).__init__()
        self.deconv1 = nn.ConvTranspose2d(123, d*8, 4, 1, 0)
        self.deconv1_bn = nn.BatchNorm2d(d*8)
        self.deconv2 = nn.ConvTranspose2d(d*8, d*4, 4, 2, 1)
        self.deconv2_bn = nn.BatchNorm2d(d*4)
        self.deconv3 = nn.ConvTranspose2d(d*4, d*2, 4, 2, 1)
        self.deconv3_bn = nn.BatchNorm2d(d*2)
        self.deconv4 = nn.ConvTranspose2d(d*2, d, 4, 2, 1)
        self.deconv4_bn = nn.BatchNorm2d(d)
        self.deconv5 = nn.ConvTranspose2d(d, 3, 4, 2, 1)

    # weight_init
    def weight_init(self, mean, std):
        for m in self._modules:
            normal_init(self._modules[m], mean, std)

    # forward method
    # def forward(self, input):
    def forward(self, input, label):
        """
        torch.Size([64, 251, 1, 1])
        torch.Size([64, 256, 4, 4])
        torch.Size([64, 512, 8, 8])
        torch.Size([64, 128, 16, 16])
        torch.Size([64, 64, 32, 32])
        torch.Size([64, 3, 64, 64])
        """
        x = torch.cat([input, label], 1)
        x = F.leaky_relu(self.deconv1_bn(self.deconv1(x)), 0.2)
        x = F.leaky_relu(self.deconv2_bn(self.deconv2(x)), 0.2)
        x = F.leaky_relu(self.deconv3_bn(self.deconv3(x)), 0.2)
        x = F.leaky_relu(self.deconv4_bn(self.deconv4(x)), 0.2)
        x = F.tanh(self.deconv5(x))/2.0+0.5
        return x

print("load model")
G = generator()
G.cuda()
G.load_state_dict(torch.load("anime_cDCGAN_model/anime_cDCGAN_generator_param_100.pkl"))
print("model loaded")

print(text_path)
# read test text for texting 
with open(text_path, "r") as f:
    content = f.readlines()
    print(content)
    testing_text_id = [line.strip().split(",")[0] for line in content]
    test_text = [line.strip().split(",")[1] for line in content]
    
# load best color match dict
def dd():
    return defaultdict(int)
with open("hair_color_match.plk","rb") as f:
    hair_color_match = pickle.load(f)
with open("eyes_color_match.plk","rb") as f:
    eyes_color_match = pickle.load(f)

def get_color(text):
    e = False
    h = False
    text = text.split(" ")
    for i,t in enumerate(text):
        if t == "hair":
            hair_color = text[i-1] + " hair"
            h = True
        if t == "eyes":
            eyes_color = text[i-1] + " eyes"
            e = True
    if h == False: # no condition for hair
        sub_dict = eyes_color_match[eyes_color]
        hair_color = sorted(sub_dict, key=sub_dict.get,reverse=True)[0]
    if e == False:
        sub_dict = hair_color_match[hair_color]
        eyes_color = sorted(sub_dict, key=sub_dict.get,reverse=True)[0]
    return hair_color, eyes_color


#create specific color 
with open("hair_encoder.pkl","rb") as f:
    hair_encoder = pickle.load(f)
with open("eyes_encoder.pkl","rb") as f:
    eyes_encoder = pickle.load(f)

# label preprocess (onehot embedding matrix)
hair_onehot = torch.zeros(12, 12)
hair_onehot = hair_onehot.scatter_(1, torch.LongTensor(list(range(12))).view(12,1), 1).view(12, 12, 1, 1)

eyes_onehot = torch.zeros(11, 11)
eyes_onehot = eyes_onehot.scatter_(1, torch.LongTensor(list(range(11))).view(11,1), 1).view(11, 11, 1, 1)

G.eval()

for t_id, i in zip(testing_text_id,test_text):
	print(i)
	for j in range(5):
		with open("fix_z/fix_z_"+str(j+1)+".pkl", "rb") as f:
			z_special = pickle.load(f)
		hair_color, eyes_color = get_color(i)
		y_special = torch.cat([hair_onehot[hair_encoder[hair_color]].view(1,12,1,1),
			eyes_onehot[eyes_encoder[eyes_color]].view(1,11,1,1)], 1)
		var_z, var_y = Variable(z_special.cuda(), volatile=True), Variable(y_special.cuda(), volatile=True)
		test_images = G(var_z, var_y)
		image_arr = test_images[0].cpu().data.numpy().transpose(1, 2, 0)
		skimage.io.imsave("./samples/sample_"+t_id+"_"+str(j+1)+".jpg",image_arr)
print("Done")