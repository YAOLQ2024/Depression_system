# Jetson deployment and acceptance guide

## Selected runtime profile

- Text: retain the existing target ONNX, tokenizer, labels, adapter, and Text TensorRT plan.
- Audio: upgraded 9-class ONNX and 16 kHz feature extractor.
- Face: upgraded 7-class ViT with RGB \`224x224\` preprocessing.
- Pose: upgraded AGCN with \`[batch,time,21,4]\` input and a 96-frame target window.

## Before building containers

1. Install Git LFS on the board and run \`git lfs pull\` after checkout.
2. Reject pointer-only checkouts. Model files around 130 bytes are LFS pointers,
   not runnable ONNX files.
3. Run \`git lfs fsck\` and then run \`python verify_bundle.py\` from this bundle.
4. Keep several GiB of free disk for Docker layers, TensorRT workspace,
   generated engines, and rollback copies.

## First boot: correctness before acceleration

Use CPU ONNX Runtime first:

\`\`\`bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.jetson-local.yml \
  up -d --build multimodal-service
\`\`\`

This establishes model and preprocessing correctness without relying on stale
TensorRT engines. Confirm that all four runtime engines load and that the API
returns finite probabilities and expected labels.

## GPU and TensorRT

- The repository's Jetson build currently installs \`onnxruntime==1.20.1\`,
  which is normally CPU-only. Merely setting
  \`MODEL_PROVIDERS=CUDAExecutionProvider\` does not create GPU support; verify
  providers inside the container with \`onnxruntime.get_available_providers()\`.
- Existing \`.plan\` files cannot be reused for changed ONNX graphs. Audio,
  Face, and Pose plans were intentionally removed. Build new engines on the
  target board with the board's installed TensorRT/CUDA/JetPack versions.
- Do not copy TensorRT plans between different Jetson models or materially
  different TensorRT/CUDA versions.
- Keep \`MCS_TENSORRT_ENABLED=false\` until the new engines have passed parity.
  After plans are generated, enable them one modality at a time.
- Audio has dynamic sample length; include representative profiles such as
  8k, 16k, and 32k samples. Pose must cover 8 through 96 frames. Face is fixed
  at \`1x3x224x224\`.

## Modality-specific checks

### Text

- Do not overwrite \`text_emotion/\`.
- Preserve its tokenizer and binary \`Negative/Positive\` label mapping.
- The retained Text plan is valid only for the existing Text ONNX and current
  target TensorRT stack; rebuild it after a JetPack/TensorRT upgrade.

### Audio

- Convert input to mono float audio and use a 16 kHz sample rate.
- Verify all nine native labels and the application's downstream aggregation.
- Benchmark short and long inputs separately because memory and latency scale
  with waveform length.

### Face

- OpenCV frames arrive as BGR. The adapter must convert to RGB, resize to
  \`224x224\`, scale to \`[0,1]\`, and normalize with mean/std \`0.5\`.
- Preserve \`anger -> angry\` and \`surprise -> surprised\` normalization.
- Validate real camera frames, no-face frames, multiple faces, and low light.

### Pose

- Pin a MediaPipe build that still exposes \`mp.solutions\`; local validation
  used MediaPipe \`0.10.14\`.
- Preserve the MediaPipe 33-landmark to shared 21-joint mapping and the fourth
  visibility channel.
- Set \`POSE_WINDOW=96\`. Predictions begin after 8 frames, but acceptance must
  include full 96-frame sequences and missing-landmark cases.

## Acceptance gates

1. Hash and LFS integrity pass.
2. CPU ONNX graph-contract and dummy-inference pass.
3. Service startup and four-engine warmup pass.
4. TensorRT output labels match the CPU reference on fixed fixtures; record
   numeric tolerance rather than relying only on top-1 labels.
5. Measure per-modality P50/P95 latency, peak RAM, peak GPU memory, sustained
   temperature, throttling, and 30-minute stability.
6. Exercise concurrent requests. The current TensorRT wrapper serializes each
   cached execution context, so throughput must be measured under real load.
7. Keep the previous Git commit and model assets available until board
   acceptance completes; rollback means restoring the prior commit and
   rebuilding/restarting the service.

Passing local verification is not Jetson production acceptance. Record the
board model, JetPack, CUDA, TensorRT, ONNX Runtime, container image digest, and
generated plan hashes in the final acceptance report.
