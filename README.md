- 👋 Hi, I’m @Aldin322
- 👀 I’m interested in python, javascript, c++
- 🌱 I’m currently learning some python modules along with javascript, and a bit c++
- 💞️ I’m looking to collaborate on python opencv, socket, requests projects, if you are learning and want to make a project, feel free to contact me
- 📫 You can reach me via discord: Aldin#6666

<!---
Aldin322/Aldin322 is a ✨ special ✨ repository because its `README.md` (this file) appears on your GitHub profile.
You can click the Preview link to take a look at your changes.
--->

## Interactive Green's Theorem Visualizer

This repository now includes a pygame-based Green's theorem playground. Draw any simple closed curve, observe the line integral of the vector field \(F(x, y) = (-y/2, x/2)\), and compare it with the signed area enclosed by the curve — a direct illustration of Green's theorem.

### Getting started

1. Install dependencies (only once):

   ```bash
   pip install pygame
   ```

2. Launch the visualization:

   ```bash
   python greens_theorem_visualizer.py
   ```

### Controls

- **Left click** to drop vertices. Right click (or left-click near the first vertex) to close the polygon.
- Once the curve is closed, **drag vertices** with the left mouse button to reshape it.
- Press **G** to toggle the underlying vector field, **H** to toggle the information overlay, and **R** to start from scratch.
- Press **Esc** to exit.

The line integral, double integral (area), and their difference are displayed in real time to demonstrate Green's theorem in action.
