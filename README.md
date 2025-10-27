## Map overlay generator
This project captures an in-game map, splits into tiles, classifies each tile using a
trained ResNet18 model, and generates a transparent overlay that appears on top of the
game window.  

  
## Controls
- **F9 →** Generate the overlay (map must be open in-game)  
- **M →** Toggle overlay visibility on/off
  - I've made this to match the default map toggle button, so it's synced with whenever you open the map
- **] →** Exit the program
  - don't think this works properly

## Requirements
- Game running in **Windowed Fullscreen** mode
- Make sure you have Python 3.9+ and install dependencies with pip:  
```bash
pip install torch torchvision pyautogui pillow keyboard pynput
```

## Future ideas
- Currently the overlay only shows locations of health and resurrection shrines, I may add more features,
e.g. rare chest, mobs, module names, etc.
  - I would then make each feature toggable so the overlay doesn't get clustered
- Currently the program only works for games running at 1920x1080 resolution, I may allow users to select
from common resolutions, or try to make it work for any res.
- Package into an installer/GUI for easier use




  
