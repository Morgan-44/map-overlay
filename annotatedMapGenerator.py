"""
Static Map Annotator
--------------------
This script captures an in-game map, splits it into tiles,
classifies each tile with a trained ResNet18 model, and then
produces a new annotated image showing the original map with
overlay icons (shrines, chests, etc.) placed in the right spots.

Controls:
    - Press F9 to capture & annotate the map (with map open in-game)
    - Press ] to exit
"""

import os
import torch
import keyboard
import pyautogui
from torchvision import transforms, models
from PIL import Image

# --- CONFIG ---
modelPath = "models/main.pth"     # Trained model checkpoint
overlaysDir = "overlays"          # Directory with overlay icons
tilesDir = "tiles"                # Temporary tiles folder
imgSize = 133                     # Model input size
mapX, mapY = 627, 207             # Top-left of map in screenshot
mapSize = 665                     # Map width/height in pixels
gridSize = 5                      # 5×5 grid

# --- LOAD MODEL ---
checkpoint = torch.load(modelPath, map_location="cpu")
classes = checkpoint["classes"]

net = models.resnet18(weights=None)
net.fc = torch.nn.Linear(net.fc.in_features, len(classes))
net.load_state_dict(checkpoint["model_state_dict"])
net.eval()

# --- IMAGE TRANSFORM ---
transform = transforms.Compose([
    transforms.Resize((imgSize, imgSize)),
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])

# --- SPLIT MAP ---
def splitMap(imgPath, outputFolder):
    os.makedirs(outputFolder, exist_ok=True)
    img = Image.open(imgPath)
    tileSize = mapSize // gridSize
    for row in range(gridSize):
        for col in range(gridSize):
            left = mapX + col * tileSize
            top = mapY + row * tileSize
            right = left + tileSize
            bottom = top + tileSize
            tile = img.crop((left, top, right, bottom))
            tile.save(f"{outputFolder}/tile_{row}_{col}.png")

# --- PREDICT SINGLE TILE ---
def predictTile(imgPath):
    img = Image.open(imgPath).convert("RGB")
    img = transform(img).unsqueeze(0)
    with torch.no_grad():
        outputs = net(img)
        probs = torch.softmax(outputs, dim=1)
        conf, pred = torch.max(probs, 1)
    return classes[pred.item()], conf.item()

# --- BUILD ANNOTATED MAP ---
def buildAnnotatedMap(originalMapPath, gridLabels):
    screenshot = Image.open(originalMapPath).convert("RGBA")
    tileSize = mapSize // gridSize

    # Crop just the map region
    mapRegion = screenshot.crop((mapX, mapY, mapX + mapSize, mapY + mapSize)).convert("RGBA")

    # Paste overlay icons onto the cropped map
    for row in range(gridSize):
        for col in range(gridSize):
            className = gridLabels[row][col]
            overlayPath = os.path.join(overlaysDir, f"{className}_overlay.png")
            if os.path.exists(overlayPath):
                icon = Image.open(overlayPath).convert("RGBA").resize((tileSize, tileSize))
                mapRegion.paste(icon, (col * tileSize, row * tileSize), icon)

    # Save result
    mapRegion.save("annotated_map.png")
    print("map saved to annotated_map.png")

# --- MAIN FUNCTION ---
def generateAnnotatedMap():
    print("generating annotated map")
    screenshot = pyautogui.screenshot()
    screenshot.save("map_capture.png")

    splitMap("map_capture.png", tilesDir)

    gridLabels = []
    for row in range(gridSize):
        rowLabels = []
        for col in range(gridSize):
            tilePath = os.path.join(tilesDir, f"tile_{row}_{col}.png")
            label, conf = predictTile(tilePath)
            rowLabels.append(label)
            print(f"({row},{col}) {label} ({conf*100:.1f}%)")
        gridLabels.append(rowLabels)

    buildAnnotatedMap("map_capture.png", gridLabels)

# --- MAIN LOOP ---
if __name__ == "__main__":
    print("press f9 (with map open) to generate annotated map, ] to quit.")
    keyboard.add_hotkey("f9", generateAnnotatedMap)
    keyboard.wait("]")
    print("Exiting.")
