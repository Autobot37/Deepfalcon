# -*- coding: utf-8 -*-
"""CT1.Auto-encoder of the quark/gluon events

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/#fileId=https%3A//storage.googleapis.com/kaggle-colab-exported-notebooks/ct1-auto-encoder-of-the-quark-gluon-events-ff6a72a3-6241-4536-8e75-2fe2f76e1a9c.ipynb%3FX-Goog-Algorithm%3DGOOG4-RSA-SHA256%26X-Goog-Credential%3Dgcp-kaggle-com%2540kaggle-161607.iam.gserviceaccount.com/20240331/auto/storage/goog4_request%26X-Goog-Date%3D20240331T093318Z%26X-Goog-Expires%3D259200%26X-Goog-SignedHeaders%3Dhost%26X-Goog-Signature%3D8aa913479b397d5876d16545d8aeba10386a4ab7fa5d44424d9eb620c181ef8a4620d86f97ecf0b90c2e1e36d33c8fc9ac1d95c8892e615b0ef6030e7219995d753e39c6e3b0d7c47e46c09c0c661b282059e4fa0a1ab49a5fbf9d1f599bc9fbe355e6a872ad0aaaa1d77f062335a9b6f3e33ee78f10aa665f4f7ae8eac8f2b4d24cc9696a05250c2fb9f1fcab46adf82ca9438497d5cbc6c6c9942a245d595795f838ed33daebed5df6d4a4fce3647b8672604d0e1868ec45cbc87501e6cc846abf378c631eace36d50720a3ebd1c2a7b8754bdd93e4c6b9b4e3d38662e9742ec9baa1d0780dc051d089c47014a6743e637dd04a06581612613832b1cbfb961
"""

!pip install gdown
!pip install h5py
import gdown
import gdown
import zipfile
import os
url = 'https://drive.google.com/uc?id=1WO2K-SfU2dntGU4Bb3IYBp9Rh7rtTYEr'
output_path = 'large_file.hdf5'
gdown.download(url, output_path, quiet=False)

import h5py

def print_hdf5_file_contents(file, indent=0):
    for key in file.keys():
        if isinstance(file[key], h5py.Group):
            print(" " * indent + f"Group: {key}")
            print_hdf5_file_contents(file[key], indent + 4)
        elif isinstance(file[key], h5py.Dataset):
            print(" " * indent + f"Dataset: {key} (Shape: {file[key].shape}, Dtype: {file[key].dtype})")
        else:
            print(" " * indent + f"Attribute: {key} = {file[key].value}")

with h5py.File('large_file.hdf5', 'r') as file:
    print_hdf5_file_contents(file)

import matplotlib.pyplot as plt
import numpy as np
train_imgs = None
test_imgs = None
with h5py.File('large_file.hdf5', 'r') as file:
    train_imgs = np.array(file['X_jets'][:4096])
    test_imgs = np.array(file['X_jets'][4096:4096+1024])
    print(train_imgs[0].shape)

import torch
device = "cuda" if torch.cuda.is_available() else "cpu"

"""## Converting all 3 features to 3 channels image"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torchvision.transforms.v2 as transforms
class Data(torch.utils.data.Dataset):
    def __init__(self,imgs):
        super().__init__()
        self.transform = transforms.Compose([
            transforms.ToTensor(),
#             transforms.Normalize([0.,0.,0.],[1.,1.,1.]),
        ])
        self.imgs = imgs
    def __len__(self):
        return len(self.imgs)
    def __getitem__(self,idx):
        img = self.transform(self.imgs[idx])
        img2 = torch.zeros((3,128,128)).to(img.dtype)
        img2[:,:125,:125] = img
        return img2

train_loader = torch.utils.data.DataLoader(Data(train_imgs), batch_size=64)
val_loader = torch.utils.data.DataLoader(Data(test_imgs), batch_size=64)

for imgs in val_loader:
    print(imgs.shape,imgs.dtype)
    break

"""## Variational Autoencoder with Reparametrization trick"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm

class VAE(nn.Module):
    def __init__(self, latent_dim):
        super(VAE, self).__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, stride=2, padding=1),  # Increased channels
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1),  # Increased channels
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1),  # Increased channels
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(256 * 16 * 16, latent_dim * 2),
            nn.BatchNorm1d(latent_dim * 2)
        )

        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 256 * 16 * 16),
            nn.BatchNorm1d(256 * 16 * 16),
            nn.Unflatten(1, (256, 16, 16)),
            nn.ConvTranspose2d(256, 128, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.ConvTranspose2d(128, 64, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.ConvTranspose2d(64, 3, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.Sigmoid()
        )

    def encode(self, x):
        z = self.encoder(x)
        mu, log_var = torch.chunk(z, 2, dim=1)
        return mu, log_var

    def decode(self, z):
        return self.decoder(z)
    ## to ensure gradient flow
    def reparameterize(self, mu, log_var):
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        mu, log_var = self.encode(x)
        z = self.reparameterize(mu, log_var)
        x_recon = self.decode(z)
        return x_recon, mu, log_var

latent_dim = 64
learning_rate = 0.1
num_epochs = 50
batch_size = 64

model = VAE(latent_dim).to(device)
reconstruction_loss = nn.MSELoss(reduction='sum')
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

prev_loss = float('inf')
best_loss = float('inf')
for epoch in range(num_epochs):
    train_loss = 0.0
    val_loss = 0.0

    # Validation loop
    model.eval()
    val_loader = tqdm(val_loader, desc=f'Epoch {epoch + 1}/{num_epochs} (val)')
    for batch_idx, data in enumerate(val_loader):
        data = data.to(device)
        with torch.no_grad():
            recon_batch, mu, log_var = model(data)
            loss = reconstruction_loss(recon_batch, data)
            kl_divergence = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())##kl divergence loss
            loss += 0.5*kl_divergence
            val_loss += loss.item()
            val_loader.set_postfix(val_loss=val_loss / ((batch_idx + 1)))
        del data

    if val_loss / len(val_loader) >= prev_loss:
        learning_rate *= 0.1
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        print(f"Changing learning rate to {learning_rate}")
    prev_loss = val_loss/(len(val_loader))

    # Training loop
    model.train()
    train_loader = tqdm(train_loader, desc=f'Epoch {epoch + 1}/{num_epochs} (train)')
    for batch_idx, data in enumerate(train_loader):
        data = data.to(device)
        optimizer.zero_grad()
        recon_batch, mu, log_var = model(data)
        loss = reconstruction_loss(recon_batch, data)
        kl_divergence = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())
        loss += 0.5*kl_divergence
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
        train_loader.set_postfix(train_loss=train_loss / ((batch_idx + 1)))
    del data

    if val_loss<best_loss:
        best_loss = val_loss
        torch.save(model.state_dict(),"model.pth")
        print("saved model to model.pth")

try:
    del model
    print("deleted model")
except:
    None
torch.cuda.empty_cache()

"""## comparing all three features"""

model = VAE(latent_dim).to(device)
model.load_state_dict(torch.load("model.pth"))
import random
model.eval()
r = random.randint(0,500)
dataset = Data(test_imgs)
imgorig = dataset[r]
imgrecons = model(imgorig.unsqueeze(0).to(device))[0]
recon_batch, mu, log_var = model(imgorig.unsqueeze(0).to(device))
loss = reconstruction_loss(recon_batch, imgorig.unsqueeze(0).to(device))
print(loss)
kl_divergence = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())
loss += kl_divergence
print(loss)
# print(np.array(imgrecons.cpu()).shape)
pltorig = imgorig.permute(1,2,0).cpu().numpy()[:125,:125,:]
pltrecons = imgrecons.permute(0,2,3,1).detach().cpu().numpy()[0][:125,:125,:]
fig, axs = plt.subplots(1, 3, figsize=(15, 5))

axs[0].imshow(pltorig[:,:,0])
axs[0].set_title('original Channel 0')

axs[1].imshow(pltorig[:,:,1])
axs[1].set_title('original Channel 1')

axs[2].imshow(pltorig[:,:,2])
axs[2].set_title('original Channel 2')
plt.show()

import matplotlib.pyplot as plt

fig, axs = plt.subplots(1, 3, figsize=(15, 5))

axs[0].imshow(pltrecons[:,:,0])
axs[0].set_title('Reconstructed Channel 0')

axs[1].imshow(pltrecons[:,:,1])
axs[1].set_title('Reconstructed Channel 1')

axs[2].imshow(pltrecons[:,:,2])
axs[2].set_title('Reconstructed Channel 2')
plt.show()



