# MotionBuilder API coverage

The adapter exposes read-only projections of the public MotionBuilder Python
API and keeps host mutations behind explicit typed skills.

## Core object model

- `mobu-api.inspect_system` reads `FBSystem`, `FBApplication`, and `FBScene`
  metadata, including scene collections and file metadata.
- `mobu-api.list_components` reads `FBComponent.Name`, `LongName`, `ClassName`,
  `ClassGroupName`, `TypeInfo`, and `Selected`.
- `mobu-api.list_characters` reads `FBCharacter` characterization, input,
  extension, and `SyncMode` state.
- `mobu-scene.inspect_scene` and `mobu-scene.list_models` provide concise scene
  and model projections for common agent queries.

## Animation and interchange

- `mobu-animation` covers `FBTake` and `FBStory` inspection.
- `mobu-interchange` uses the documented `FBApplication` file operations for
  open, merge, append, motion import, and motion export.
- `mobu-mocap` reads devices, optical devices, actors, and marker sets without
  starting, stopping, recording, or calibrating a device.
- `mobu-plugins` reads loaded plug-in items and configured runtime paths.

## Reference sources

- [Autodesk FBSystem reference](https://help.autodesk.com/cloudhelp/2026/ENU/MOBU-PYTHON-API-REF/classpyfbsdk_1_1_f_b_system.html)
- [Autodesk FBScene reference](https://help.autodesk.com/cloudhelp/2026/ENU/MOBU-PYTHON-API-REF/classpyfbsdk_1_1_f_b_scene.html)
- [Autodesk FBComponent reference](https://help.autodesk.com/cloudhelp/2026/ENU/MOBU-PYTHON-API-REF/classpyfbsdk_1_1_f_b_component.html)
- [Autodesk FBCharacter reference](https://help.autodesk.com/cloudhelp/2026/ENU/MOBU-PYTHON-API-REF/class_f_b_character.html)
- [Autodesk FBApplication reference](https://help.autodesk.com/cloudhelp/2026/ENU/MOBU-PYTHON-API-REF/classpyfbsdk_1_1_f_b_application.html)
- [MoBuCore](https://github.com/Danlowlows/MobuCore) for common MotionBuilder workflow patterns
- [MoPlugs](https://github.com/Neill3d/MoPlugs) for plug-in and script ecosystem patterns
- [MotionBuilder Take Manager](https://github.com/Fuggy/MotionBuilder-TakeManager) for take workflow patterns
- [pyfbsdk stubs](https://github.com/nils-soderman/pyfbsdk-stub-generator) for versioned typing references

Third-party repositories inform capability discovery and naming only. The
adapter does not copy their implementation or redistribute their binaries.
