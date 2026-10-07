# Hybrid four-modality runtime upgrade

This deliverable implements the approved deployment profile:

| Modality | Runtime selection | Deployment action |
|---|---|---|
| Text | Existing two-class target model | Retain the complete target directory unchanged |
| Audio | `emotion2vec_plus_large` | Replace ONNX, labels, and preprocessor |
| Face | Facial-expression ViT | Replace ONNX and RGB 224x224 adapter |
| Pose | AGCN seed72 | Replace ONNX; retain the 33-to-21-joint adapter |

The replacement files for Audio, Face, and Pose are under
`runtime-assets/models/`. Text is deliberately absent from the overlay so an
installation cannot accidentally overwrite the retained target model.

The corresponding live files under
`services/multimodal-service/runtime-assets/models/` have been replaced in the
current worktree. The old Audio, Face, and Pose TensorRT `.plan` files were
removed because TensorRT engines are tied to the old graphs and target runtime.
The existing Text ONNX, tokenizer, adapter, and Text `.plan` remain unchanged.

## Runtime contracts

| Modality | Input | Output | Important preprocessing |
|---|---|---|---|
| Text | `input_ids`, `attention_mask` | `logits[batch,2]` | Existing tokenizer and binary labels |
| Audio | `input_values[batch,audio_len]` | `logits[batch,9]` | Mono float waveform, 16 kHz feature extractor |
| Face | `input[batch,3,224,224]` | `output[batch,7]` | OpenCV BGR to RGB, resize, normalize to `[-1,1]` |
| Pose | `sequence[batch,time,21,4]` | `probs[batch,4]` | MediaPipe 33 landmarks mapped to shared 21 joints; 96-frame target window |

## Installation rule

Do not copy this directory over the whole model root. Apply only the three
overlay directories:

- `audio_emotion/`
- `face_emotion/`
- `pose_emotion/`

Leave `text_emotion/` untouched. Restart `multimodal-service` after changing
assets because sessions are cached in process memory.

## Verification

From this directory, run:

```powershell
python verify_bundle.py --output reports/bundle_verification_hybrid_ort_1_23_2.json
```

The verifier checks the retained target Text hash, the three replacement
hashes, ONNX graph contracts, dummy inference, and the absence of obsolete
Audio/Face/Pose TensorRT plans.

Jetson preparation, provider selection, TensorRT regeneration, acceptance
gates, and rollback guidance are documented in `JETSON_DEPLOYMENT.md`.
