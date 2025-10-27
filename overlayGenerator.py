"""
Overlay Generator for Game Map
------------------------------
This script captures an in-game map, splits it into tiles,
classifies each tile with a trained ResNet18 model, and displays
an overlay on top of the game window. 

Controls:
    - Press F9 to generate the overlay (with map open in-game)
    - Press M to toggle the overlay visibility
    - Press ] to exit the program (unreliable)
"""

import os
import torch
import keyboard
import pyautogui
from torchvision import transforms, models
from PIL import Image, ImageTk
import tkinter as tk
from pynput import keyboard as pkb


# --- CONFIG ---
modelPath = "models/main.pth"    # Trained model checkpoint
overlaysDir = "overlays"         # Directory with overlay icons
tilesDir = "tiles"               # Directory to save temporary map tiles
imgSize = 133                    # Model input size
mapX, mapY = 627, 207            # Top-left corner of map in screenshot
mapSize = 665                    # Map width/height in pixels
gridSize = 5                     # Number of rows/cols to split map into


# --- LOAD MODEL ---
checkpoint = torch.load(modelPath, map_location="cpu")
classes = checkpoint["classes"]

# Build a ResNet18 with custom final layer matching our classes
net = models.resnet18(weights=None)
net.fc = torch.nn.Linear(net.fc.in_features, len(classes))
net.load_state_dict(checkpoint["model_state_dict"])
net.eval()


# --- IMAGE TRANSFORM ---
# Preprocessing before passing images to the model.
# Normalization centers pixel values and improves performance,
# especially for symmetrical tiles where orientation matters.
transform = transforms.Compose([
    transforms.Resize((imgSize, imgSize)),
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])


# --- SPLIT MAP INTO TILES ---
def splitMap(imgPath: str, outputFolder: str) -> None:
    """
    Splits the captured map screenshot into gridSize x gridSize tiles

    Args:
    imgPath (str): Path to full screenshot
    outputFolder (str): Directory where cropped tiles will be saved
    """
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
def predictTile(imgPath: str) -> tuple[str, float]:
    """
    Runs inference on a single tile image

    Args:
    imgPath (str): Path to the tile image

    Returns:
    tuple: (predictedClassName, confidenceScore)
    """
    img = Image.open(imgPath).convert("RGB")
    img = transform(img).unsqueeze(0)  # add batch dimension

    with torch.no_grad():  # no gradients needed for inference
        outputs = net(img)
        probs = torch.softmax(outputs, dim=1)
        conf, pred = torch.max(probs, 1)

    return classes[pred.item()], conf.item()


# --- BUILD OVERLAY IMAGE ---
def buildOverlay(gridLabels: list[list[str]]) -> None:
    """
    Builds the final overlay image using predicted tile classes

    Args:
    gridLabels (list of list of str): Predicted class names for each tile
    """
    baseOverlay = Image.new("RGBA", (mapSize, mapSize), (0, 255, 0, 0))
    tileSize = mapSize // gridSize

    for row in range(gridSize):
        for col in range(gridSize):
            className = gridLabels[row][col]
            overlayPath = os.path.join(overlaysDir, f"{className}_overlay.png")

            if os.path.exists(overlayPath):
                icon = Image.open(overlayPath).convert("RGBA").resize((tileSize, tileSize))
                baseOverlay.paste(icon, (col * tileSize, row * tileSize), icon)

    baseOverlay.save("final_overlay.png")
    print("Overlay generated and saved to final_overlay.png")


# --- CAPTURE SCREEN AND GENERATE OVERLAY ---
def generateOverlayFromScreen() -> None:
    """Captures the screen, splits map into tiles, predicts each tile, and shows overlay."""
    print("Capturing map and generating overlay...")

    screenshot = pyautogui.screenshot()
    screenshot.save("map_capture.png")

    splitMap("map_capture.png", tilesDir)

    # Predict each tile
    gridLabels = []
    for row in range(gridSize):
        rowLabels = []
        for col in range(gridSize):
            tilePath = os.path.join(tilesDir, f"tile_{row}_{col}.png")
            label, conf = predictTile(tilePath)
            rowLabels.append(label)
            print(f"({row},{col}) {label} ({conf*100:.1f}%)")  # prints confidence of chosen class/module+rotation
        gridLabels.append(rowLabels)

    buildOverlay(gridLabels)
    showOverlay("final_overlay.png")


# --- SHOW TRANSPARENT OVERLAY WINDOW ---
def showOverlay(imgPath: str = "final_overlay.png", transparencyColor: str = "#00FF00") -> None:
    """Displays the generated overlay in a transparent window aligned with the map"""
    root = tk.Tk()
    root.title("Map Overlay")
    root.attributes("-topmost", True)           # always on top
    root.overrideredirect(True)                 # no window border
    root.wm_attributes("-transparentcolor", transparencyColor)

    overlay = Image.open(imgPath).convert("RGBA")
    bg = Image.new("RGBA", overlay.size, transparencyColor)
    overlay = Image.alpha_composite(bg, overlay)
    tkOverlay = ImageTk.PhotoImage(overlay)

    label = tk.Label(root, image=tkOverlay, borderwidth=0)
    label.pack()
    root.geometry(f"+{mapX}+{mapY}")

    # Visibility toggle state
    visible = {"state": True}

    def applyVisibility():
        """Updates window transparency based on visibility state"""
        root.attributes("-alpha", 1.0 if visible["state"] else 0.0)
        root.after(50, applyVisibility)

    applyVisibility()

    def onPress(key):
        """Toggle overlay with M"""
        try:
            if key.char.lower() == "m":
                visible["state"] = not visible["state"]
        except AttributeError:
            pass

    listener = pkb.Listener(on_press=onPress)
    listener.start()

    print("overlay active, press m to toggle, ] to close")
    root.mainloop()


# --- MAIN LOOP ---
if __name__ == "__main__":
    print("press f9 with map open to generate overlay")
    keyboard.add_hotkey("f9", generateOverlayFromScreen)
    keyboard.wait("]")  # block until ] is pressed
    print("exiting")
