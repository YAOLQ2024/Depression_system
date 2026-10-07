# Target compatibility matrix

| Modality | Previous target artifact | Selected runtime artifact | Companion change | Local gate |
|---|---:|---:|---|---|
| Text | 390.33 MiB, 2 classes | Retained unchanged | Keep tokenizer, adapter, labels, and Text plan | PASS |
| Audio | 360.98 MiB, 4 classes | 618.92 MiB, 9 native classes | Replace labels/preprocessor; remove old plan | PASS |
| Face | 42.61 MiB, gray 48x48 | 327.58 MiB, RGB 224x224 | Replace `infer_face.py`; remove old plan | PASS |
| Pose | 8.47 MiB | 13.38 MiB, 21 joints x 4 channels | Use 33-to-21 mapping and 96-frame window; remove old plan | PASS |

`PASS` means hashes, graph contracts, local CPU inference, and service runtime
loading passed. It is not Jetson GPU/TensorRT, latency, memory, temperature, or
production acceptance.
