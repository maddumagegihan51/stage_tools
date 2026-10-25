# StageTools

**StageTools** is a production-focused pipeline toolkit that brings asset normalization, material cleanup, and camera frustum isolation into one interface.

Designed for individual artists and production teams, StageTools simplifies repetitive scene preparation tasks and helps keep asset workflows consistent.

---

# Features

## 📐 Asset Vector Normalizer

Prepare static mesh assets with bottom-center origins and baked transforms.

- **Normalize for UE5** — applies a −90° Z-axis correction, mapping an assumed +Y forward direction to +X.
- **Normalize for Maya** — applies a +90° X-axis correction, mapping an assumed +Y forward direction to +Z.
- **Freeze Blender Matrix** — bakes existing rotation and scale without an additional axis correction.
- Protects other objects sharing the same mesh by creating a separate mesh datablock.
- Preserves the world placement of editable child objects.

The final origin is positioned at the original world-space bottom center. Rotation, scale, and delta transforms are reset, while translation is retained at that pivot.

## 🧹 Material Network Pruner

Consolidate duplicate material names and remove unused local materials.

- Detects numeric suffixes such as `.001` and `.002`.
- Remaps mesh material slots to an existing unsuffixed local master.
- Skips protected linked data.
- Removes local material datablocks with zero users.
- Reports remapped slots, removed materials, and skipped operations.

For example, slots using `Steel.001` are reassigned to `Steel` when that master material exists.

## 🎥 Camera Frustum Isolator

Focus the viewport on assets within a selected camera’s view.

- Includes a camera picker with fallback to the scene camera.
- Supports perspective and orthographic cameras.
- Evaluates mesh bounding boxes and collection instances.
- Supports linked collection assets through their local instancers.
- Keeps an instancer visible when any of its evaluated mesh instances intersects the camera frustum.
- Provides **Clear View Isolation** to reveal objects again.

---

# Installation

1. Download the StageTools extension ZIP from the repository’s **Releases**.
2. Open Blender **Preferences → Get Extensions**.
3. Open the menu in the upper-right corner and choose **Install from Disk**.
4. Select the ZIP file without extracting it.
5. Enable **StageTools** if needed.

---

# Getting Started

- Open the **3D Viewport → Sidebar (N Panel)**.
- Select the **StageTools** tab.
- Expand **StageTools Engine**.
- Select editable meshes in **Object Mode** to use the normalization tools.
- Use **Purge Duplicate Materials** to consolidate suffix-named materials.
- Choose a camera and click **Isolate Frustum View** to focus the viewport.
- Click **Clear View Isolation** to show objects again.

Save your scene before processing production assets. The operators support Blender Undo.

---

# Important Notes

## Asset Normalization

Normalization is intended for static export meshes.

- Selected meshes must contain vertices and have nonzero scale.
- Mesh objects with parents, modifiers, animation, constraints, or rigid-body settings are rejected.
- Child objects must be editable.
- Applying an engine correction repeatedly rotates the geometry again.
- Exporter settings, engine units, and file-format axis conversion must be configured separately.

## Material Cleanup

Material merging is **name-based**. The tool does not compare shader nodes, textures, or material values.

The operation scans mesh material slots across the Blender file, regardless of selection. It also removes unrelated local materials with zero users. Materials with fake users or remaining references are retained.

## Camera Isolation

Isolation uses conservative bounding-box tests and does not test occlusion.

- Rerun isolation after moving the camera, changing geometry, or changing frames.
- Render visibility remains unchanged.
- Generated instances share their owner’s visibility.
- Object visibility changes can affect other scenes and view layers sharing those objects.
- Hidden or excluded collections remain hidden or excluded.
- **Clear View Isolation** clears object hiding rather than restoring a previous visibility snapshot.
- Panoramic cameras are unsupported.

---

# Designed For

StageTools is useful for:

- Environment Artists
- Asset Artists
- Layout Artists
- Technical Artists
- Game Development
- Animation Production
- VFX Pipelines

---

# Why StageTools?

StageTools brings three common pipeline tasks into a single panel, reducing repetitive asset preparation and scene maintenance work.

Normalize static assets, consolidate material variants, and isolate camera-visible content without switching between separate add-ons.

---

# Compatibility

- Minimum declared version: **Blender 4.5**
- Uses APIs shared by **Blender 4.5 and Blender 5.x**
- No external Python packages required

Automated integration checks passed in **Blender 5.1.2**. Blender 4.5 compatibility has been reviewed at API level; runtime testing in 4.5 remains outstanding.

The code uses platform-independent Blender APIs, but Windows, Linux, and macOS have not all been individually tested.

---

# Permissions

StageTools requests **no additional permissions**.

The add-on does not access the network, send telemetry, or require external services.

---

# Support

For bug reports, feature requests, or assistance, use this repository’s **Issues** tab.

When reporting a problem, include:

- Blender version and operating system
- Steps to reproduce the issue
- Expected and actual behavior
- Relevant error messages
- A minimal sample file, when possible

---

# License

StageTools is licensed under the **GNU General Public License v3.0 or later**.

See [LICENSE](LICENSE) for details.
