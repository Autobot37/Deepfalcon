# -*- coding: utf-8 -*-
"""ST-3Graph Transformers Fast Detector Simulation

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/#fileId=https%3A//storage.googleapis.com/kaggle-colab-exported-notebooks/st-3graph-transformers-fast-detector-simulation-62e27a84-a615-4944-a87e-6a305a68272a.ipynb%3FX-Goog-Algorithm%3DGOOG4-RSA-SHA256%26X-Goog-Credential%3Dgcp-kaggle-com%2540kaggle-161607.iam.gserviceaccount.com/20240331/auto/storage/goog4_request%26X-Goog-Date%3D20240331T101456Z%26X-Goog-Expires%3D259200%26X-Goog-SignedHeaders%3Dhost%26X-Goog-Signature%3D32a38bd9997146a573b5c996b85c7fede2f2011c4c6954cbf47cd7b19f421c113ea97fc5174a5e5f06bf3b67ce628a9ab5258f7c7bf1a5c35fbdda778b0a35f034dd41adb23f1e9df973b78d752a84319db0d34f6d33a2545d9c8bfbaef057e549f20901bb1c9fc6b022114eb36eb33cf81e2a28afea449402bc1f0b85f9592fdbe269ec0bdd9f40a7dd1f06a190a0a7b613234d1b3f9d440ca2a727de6e559209fc12fbe131c6c746731465fe3dcacdadbf461f27aafe8122a00ff61fb8b6cac2e41830bf02e7e5d4cb9b842ab3cf9c88d04c510e1525f0f059bfa8fb0acb7170b242bacb0507ce008eadbb76ac3e4bbcf7dab3c2ee11f009c879b278955549
"""

!pip install gdown
import gdown
import gdown
import zipfile
import os
url = 'https://drive.google.com/uc?id=1WO2K-SfU2dntGU4Bb3IYBp9Rh7rtTYEr'
output_path = 'large_file.hdf5'
gdown.download(url, output_path, quiet=False)
import matplotlib.pyplot as plt
import numpy as np
import h5py
with h5py.File('large_file.hdf5', 'r') as file:
    train_imgs = np.array(file['X_jets'][:4096])
    test_imgs = np.array(file['X_jets'][4096:4096+1024])
    train_labels = np.array(file['y'][:4096])
    test_labels = np.array(file['y'][4096:4096+1024])
    print(train_imgs[0].shape)

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torchvision.transforms.v2 as transforms

class Data(torch.utils.data.Dataset):
    def __init__(self,imgs,labels):
        super().__init__()
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Resize((16, 16))###smaller size for efficient processing in ViT
            #transforms.Normalize([0.,0.,0.],[1.,1.,1.]),
        ])
        self.imgs = imgs
        self.labels = labels
    def __len__(self):
        return len(self.imgs)
    def __getitem__(self,idx):
        img = self.transform(self.imgs[idx])
        return img,torch.tensor(self.labels[idx]).to(torch.long)

train_loader = torch.utils.data.DataLoader(Data(train_imgs,train_labels), batch_size=64)
val_loader = torch.utils.data.DataLoader(Data(test_imgs,test_labels), batch_size=64)

for imgs,labels in train_loader:
    print(imgs.shape)
    img = imgs[0]
    plt.imshow(img.permute(1,2,0).cpu().numpy()[:,:,2])
    print(labels.shape)
    break

"""## Vision Transformer for Classification"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
from torchvision.datasets import ImageFolder
from tqdm import tqdm

# Define the ViT model
class ViT(nn.Module):
    def __init__(self, image_size, patch_size, num_classes, dim, depth, heads, mlp_dim, channels=3):
        super().__init__()
        self.image_size = image_size
        self.patch_size = patch_size
        num_patches = (image_size // patch_size) ** 2
        patch_dim = channels * patch_size ** 2
        self.patch_embeddings = nn.Conv2d(channels, dim, kernel_size=patch_size, stride=patch_size)
        self.cls_token = nn.Parameter(torch.randn(1, 1, dim))
        self.pos_embeddings = nn.Parameter(torch.randn(1, num_patches + 1, dim))
        self.transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model=dim, nhead=heads, dim_feedforward=mlp_dim),
            num_layers=depth
        )
        self.mlp_head = nn.Linear(dim, num_classes)

    def forward(self, x):
        B, C, H, W = x.shape
        x = self.patch_embeddings(x)
        x = x.flatten(2).transpose(1, 2)
        cls_tokens = self.cls_token.expand(B, -1, -1)
        x = torch.cat((cls_tokens, x), dim=1)
        x += self.pos_embeddings
        x = self.transformer(x)
        x = x[:, 0]
        x = self.mlp_head(x)
        return x

# Define the hyperparameters
image_size = 16
patch_size = 2
num_classes = 2  # Replace with the number of classes in your dataset
dim = 768
depth = 2
heads = 4
mlp_dim = 256
channels = 3
batch_size = 64
learning_rate = 0.01
num_epochs = 10

# Initialize the model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = ViT(image_size, patch_size, num_classes, dim, depth, heads, mlp_dim, channels).to(device)

# Define the loss function and optimizer
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

losses = []
accuracies = []
# Training loop
for epoch in range(num_epochs):
    train_loss = 0.0
    model.train()
    for images, labels in tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs}"):
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        train_loss += loss.item()

    train_loss /= len(train_loader)

    # Validation loop
    val_loss = 0.0
    correct = 0
    total = 0
    model.eval()
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            val_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    val_loss /= len(val_loader)
    val_accuracy = correct / total
    losses.append(val_loss)
    accuracies.append(val_accuracy)

    print(f"Epoch {epoch+1}/{num_epochs}, Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}, Val Accuracy: {val_accuracy:.4f}")

import matplotlib.pyplot as plt

plt.plot(losses)
plt.title("Losses")
plt.xlabel("Epochs")
plt.ylabel("Loss")
plt.show()

plt.plot(accuracies)
plt.title("Accuraacy")
plt.xlabel("Epochs")
plt.ylabel("Accuracy")
plt.show()

del model
torch.cuda.empty_cache()

"""## Vision Transformer for Image generation with Convolution Decoder"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
from torchvision.datasets import ImageFolder
from tqdm import tqdm

# Define the ViT model with encoder-decoder architecture
class ViT(nn.Module):
    def __init__(self, image_size, patch_size, num_classes, dim, depth, heads, mlp_dim, channels=3):
        super().__init__()
        self.image_size = image_size
        self.patch_size = patch_size
        num_patches = (image_size // patch_size) ** 2
        patch_dim = channels * patch_size ** 2
        self.patch_embeddings = nn.Conv2d(channels, dim, kernel_size=patch_size, stride=patch_size)
        self.cls_token = nn.Parameter(torch.randn(1, 1, dim))
        self.pos_embeddings = nn.Parameter(torch.randn(1, num_patches + 1, dim))

        # Encoder
        self.encoder_transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model=dim, nhead=heads, dim_feedforward=mlp_dim),
            num_layers=depth
        )

        # Decoder
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(dim, dim // 2, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(dim // 2, dim // 4, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(dim // 4, dim // 8, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(dim // 8, channels, kernel_size=4, stride=2, padding=1),
            nn.Sigmoid()
        )

    def forward(self, x):
        B, C, H, W = x.shape

        # Encoder
        x_enc = self.patch_embeddings(x)
        x_enc = x_enc.flatten(2).transpose(1, 2)
        cls_tokens_enc = self.cls_token.expand(B, -1, -1)
        x_enc = torch.cat((cls_tokens_enc, x_enc), dim=1)
        x_enc += self.pos_embeddings
        x_enc = self.encoder_transformer(x_enc)
        x_enc = x_enc[:, 0]  # Take the first token

        # Decoder
        x_dec = x_enc.unsqueeze(-1).unsqueeze(-1)  # Add spatial dimensions
        x_dec = self.decoder(x_dec)
        return x_dec

# Define the hyperparameters
image_size = 16
patch_size = 1
num_classes = 2  # For RGB images
dim = 64
depth = 1
heads = 2
mlp_dim = 64
channels = 3  # For RGB images
batch_size = 128
learning_rate = 0.0001
num_epochs = 20

# Initialize the model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = ViT(image_size, patch_size, num_classes, dim, depth, heads, mlp_dim, channels).to(device)

# Define the loss function and optimizer
criterion = nn.MSELoss()  # Use Mean Squared Error for image generation
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

losses = []
# Training loop
for epoch in range(num_epochs):
    train_loss = 0.0
    model.train()
    for images, _ in tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs}"):
        images = images.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, images)  # Compare generated images with ground truth
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
    train_loss /= len(train_loader)

    # Validation loop
    val_loss = 0.0
    model.eval()
    for images, _ in tqdm(val_loader, desc=f"Epoch {epoch+1}/{num_epochs}"):
        images = images.to(device)
        outputs = model(images)
        loss = criterion(outputs, images)  # Compare generated images with ground truth
        val_loss += loss.item()
    val_loss /= len(val_loader)
    losses.append(val_loss)
    print(f"Epoch {epoch+1}/{num_epochs}, Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

import matplotlib.pyplot as plt
plt.plot(losses)
plt.title("Validation Losses for Image Generation")
plt.xlabel("Epochs")
plt.ylabel("Loss")
plt.show()

import random
model.eval()
r = random.randint(0,1024)
dataset = Data(test_imgs,test_labels)
imgorig = dataset[r][0]
imgrecons = model(imgorig.unsqueeze(0).to(device))
# print(np.array(imgrecons.cpu()).shape)
pltorig = imgorig.permute(1,2,0).cpu().numpy()
pltrecons = imgrecons.permute(0,2,3,1).detach().cpu().numpy()[0]
fig, axs = plt.subplots(1, 3, figsize=(15, 5))

axs[0].imshow(pltorig[:,:,0])
axs[0].set_title('Channel 0')

axs[1].imshow(pltorig[:,:,1])
axs[1].set_title('Channel 1')

axs[2].imshow(pltorig[:,:,2])
axs[2].set_title('Channel 2')

plt.suptitle('Original', fontsize=16)  # Set a common title for all subplots in the x-axis direction
plt.show()

fig, axs = plt.subplots(1, 3, figsize=(15, 5))

axs[0].imshow(pltorig[:,:,0])
axs[0].set_title('Channel 0')
axs[0].set_xlabel('X-axis')

axs[1].imshow(pltorig[:,:,1])
axs[1].set_title('Channel 1')
axs[1].set_xlabel('X-axis')

axs[2].imshow(pltorig[:,:,2])
axs[2].set_title('Channel 2')
axs[2].set_xlabel('X-axis')

plt.suptitle('Reconstructed', fontsize=16)  # Set a common title for all subplots in the x-axis direction
plt.show()








