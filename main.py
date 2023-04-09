"""Main entrypoint of the application."""
import os
import json
from dotenv import load_dotenv

from flask import Flask, render_template, request
from pymongo import MongoClient
from text import send_twilio_message

import tensorflow as tf
import torch
import torch.nn as nn           # for creating  neural networks

new_model = tf.keras.models.load_model('./Model_Files/disease-classification_1')

# Check its architecture

class ImageClassificationBase(nn.Module):
    
    def training_step(self, batch):
        images, labels = batch
        out = self(images)                  # Generate predictions
        loss = F.cross_entropy(out, labels) # Calculate loss
        return loss
    
    def validation_step(self, batch):
        images, labels = batch
        out = self(images)                   # Generate prediction
        loss = F.cross_entropy(out, labels)  # Calculate loss
        acc = accuracy(out, labels)          # Calculate accuracy
        return {"val_loss": loss.detach(), "val_accuracy": acc}
    
    def validation_epoch_end(self, outputs):
        batch_losses = [x["val_loss"] for x in outputs]
        batch_accuracy = [x["val_accuracy"] for x in outputs]
        epoch_loss = torch.stack(batch_losses).mean()       # Combine loss  
        epoch_accuracy = torch.stack(batch_accuracy).mean()
        return {"val_loss": epoch_loss, "val_accuracy": epoch_accuracy} # Combine accuracies
    
    def epoch_end(self, epoch, result):
        print("Epoch [{}], last_lr: {:.5f}, train_loss: {:.4f}, val_loss: {:.4f}, val_acc: {:.4f}".format(
            epoch, result['lrs'][-1], result['train_loss'], result['val_loss'], result['val_accuracy']))

class ResNet9(ImageClassificationBase):
    def __init__(self, in_channels, num_diseases):
        super().__init__()
        
        self.conv1 = ConvBlock(in_channels, 64)
        self.conv2 = ConvBlock(64, 128, pool=True) # out_dim : 128 x 64 x 64 
        self.res1 = nn.Sequential(ConvBlock(128, 128), ConvBlock(128, 128))
        
        self.conv3 = ConvBlock(128, 256, pool=True) # out_dim : 256 x 16 x 16
        self.conv4 = ConvBlock(256, 512, pool=True) # out_dim : 512 x 4 x 44
        self.res2 = nn.Sequential(ConvBlock(512, 512), ConvBlock(512, 512))
        
        self.classifier = nn.Sequential(nn.MaxPool2d(4),
                                       nn.Flatten(),
                                       nn.Linear(512, num_diseases))
        
    def forward(self, xb): # xb is the loaded batch
        out = self.conv1(xb)
        out = self.conv2(out)
        out = self.res1(out) + out
        out = self.conv3(out)
        out = self.conv4(out)
        out = self.res2(out) + out
        out = self.classifier(out)
        return out  
      
def ConvBlock(in_channels, out_channels, pool=False):
    layers = [nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
             nn.BatchNorm2d(out_channels),
             nn.ReLU(inplace=True)]
    if pool:
        layers.append(nn.MaxPool2d(4))
    return nn.Sequential(*layers)
model = torch.load('./Model_Files/disease-classification_2.pth', map_location=torch.device('cpu'))
model.eval()
print(model)

def diseasemodel1():
    return 1

def diseasemodel2():
    return 1





app = Flask(__name__)

load_dotenv()

MONGODB_USER = os.environ.get('MONGODB_USER')
MONGODB_PASS = os.environ.get('MONGODB_PASS')

client = MongoClient(f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASS}"
                     "@main.hup8pvq.mongodb.net/?retryWrites=true&w=majority")

db = client.development
reports = db.reports

@app.route("/")
def home():
    """Home page of the application."""
    print(diseasemodel1(), diseasemodel2())
    return render_template("home.html")

@app.route("/scan", methods=["GET", "POST"])
def scan():
    """Scan a plant."""
    if request.method == "GET":
        return render_template("scan.html")
 
    elif request.method == "POST":
        phoneno = request.form.get("phoneno")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        # disease = request.form.get("disease")

        print(latitude, longitude)

        report = {
            "phoneno": phoneno,
            "latitude": latitude,
            "longitude": longitude,
            # "disease": disease
        }

        reports.insert_one(report)

        send_twilio_message("Your plant has been scanned! Thank you for your input.", phoneno.replace(" ", ""))

        return render_template("scan.html")

@app.route("/map")
def display_map():
    """Map of plants."""
    all_reports = {"data": list(reports.find({}, {"_id": 0}))}

    print(all_reports)

    return render_template("map.html", reports=all_reports)

if __name__ == "__main__":
    app.run()
