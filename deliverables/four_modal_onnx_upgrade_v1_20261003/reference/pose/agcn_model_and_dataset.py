import argparse
import csv
import json
import math
import random
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset
except ImportError as e:
    raise RuntimeError("Please install pytorch first: pip install torch") from e


DEFAULT_LABEL_ORDER = ["ang", "sad", "neu", "hap", "fear", "disg", "surp"]
MP_POSE_EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32),
]


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def load_manifest(path: Path) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_label_mapping(rows: Sequence[Dict[str, str]]) -> Dict[str, int]:
    labels = sorted(
        {r["label"] for r in rows},
        key=lambda x: (DEFAULT_LABEL_ORDER.index(x) if x in DEFAULT_LABEL_ORDER else 999, x),
    )
    return {label: idx for idx, label in enumerate(labels)}


def choose_group_key(rows: Sequence[Dict[str, str]], group_key: str) -> str:
    if group_key != "auto":
        return group_key
    for key in ("group_id", "actor", "dialog", "speaker", "scene_id"):
        if any((r.get(key) or "").strip() for r in rows):
            return key
    return "utt_id"


def split_by_group(
    rows: Sequence[Dict[str, str]],
    val_ratio: float,
    seed: int,
    group_key: str,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    resolved_group_key = choose_group_key(rows, group_key)
    groups = sorted({(r.get(resolved_group_key) or "").strip() or r["utt_id"] for r in rows})
    rng = random.Random(seed)
    rng.shuffle(groups)
    n_val = max(1, int(round(len(groups) * val_ratio)))
    val_groups = set(groups[:n_val])
    train_rows = [r for r in rows if ((r.get(resolved_group_key) or "").strip() or r["utt_id"]) not in val_groups]
    val_rows = [r for r in rows if ((r.get(resolved_group_key) or "").strip() or r["utt_id"]) in val_groups]
    return train_rows, val_rows


def normalize_pose(seq: np.ndarray) -> np.ndarray:
    xyz = seq[:, :, :3].astype(np.float32)
    vis = seq[:, :, 3:4].astype(np.float32)
    root = (xyz[:, 23:24, :] + xyz[:, 24:25, :]) * 0.5 if xyz.shape[1] > 24 else xyz[:, 0:1, :]
    xyz = xyz - root
    scale = np.linalg.norm(xyz, axis=2, keepdims=False).mean(axis=1, keepdims=True)
    scale = np.maximum(scale, 1e-4).reshape(-1, 1, 1)
    xyz = xyz / scale
    return np.concatenate([xyz, vis], axis=2)


def temporal_resize(seq: np.ndarray, target_len: int) -> np.ndarray:
    t = seq.shape[0]
    if t == target_len:
        return seq
    if t <= 1:
        return np.repeat(seq, target_len, axis=0)
    old_idx = np.linspace(0.0, 1.0, num=t, dtype=np.float32)
    new_idx = np.linspace(0.0, 1.0, num=target_len, dtype=np.float32)
    out = np.zeros((target_len, seq.shape[1], seq.shape[2]), dtype=np.float32)
    for j in range(seq.shape[1]):
        for k in range(seq.shape[2]):
            out[:, j, k] = np.interp(new_idx, old_idx, seq[:, j, k])
    return out


class SkeletonEmotionDataset(Dataset):
    def __init__(self, rows: Sequence[Dict[str, str]], seq_len: int, label2id: Dict[str, int]):
        self.items: List[Tuple[str, int, str]] = []
        self.seq_len = seq_len
        for r in rows:
            if r["label"] in label2id:
                self.items.append((r["seq_path"], label2id[r["label"]], r["utt_id"]))
        if self.items:
            sample = normalize_pose(np.load(self.items[0][0])["keypoints"].astype(np.float32))
            self.num_joints = int(sample.shape[1])
            self.in_channels = int(sample.shape[2])
        else:
            self.num_joints = 0
            self.in_channels = 0

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int):
        seq_path, y, utt_id = self.items[idx]
        arr = normalize_pose(np.load(seq_path)["keypoints"].astype(np.float32))
        arr = temporal_resize(arr, self.seq_len)
        arr = np.transpose(arr, (2, 0, 1))  # C,T,V
        arr = np.expand_dims(arr, axis=-1)  # C,T,V,M=1
        return torch.from_numpy(arr), torch.tensor(y, dtype=torch.long), utt_id


def extract_bvh_edges(source_path: Path) -> List[Tuple[int, int]]:
    if not source_path.exists():
        return []
    lines = source_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    parents: List[int] = []
    stack: List[int] = []
    current_joint = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("MOTION"):
            break
        if line.startswith("ROOT ") or line.startswith("JOINT "):
            parents.append(stack[-1] if stack else -1)
            current_joint = len(parents) - 1
            i += 1
            continue
        if line.startswith("End Site"):
            current_joint = None
            i += 1
            continue
        if line == "{":
            if current_joint is not None:
                stack.append(current_joint)
            i += 1
            continue
        if line == "}":
            if stack:
                stack.pop()
            current_joint = stack[-1] if stack else None
            i += 1
            continue
        i += 1
    return [(child, parent) for child, parent in enumerate(parents) if parent >= 0]


def load_subset_edges(manifest_dir: Path, num_joints: int) -> List[Tuple[int, int]]:
    spec_path = manifest_dir / "subset_spec.json"
    if not spec_path.exists():
        return []
    try:
        payload = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    spec_num_joints = int(payload.get("num_joints", -1))
    if spec_num_joints != num_joints:
        return []
    edges = payload.get("edges", [])
    parsed: List[Tuple[int, int]] = []
    for edge in edges:
        if isinstance(edge, (list, tuple)) and len(edge) == 2:
            parsed.append((int(edge[0]), int(edge[1])))
    return parsed


def resolve_edges(rows: Sequence[Dict[str, str]], num_joints: int, manifest_dir: Path) -> List[Tuple[int, int]]:
    if num_joints == 33:
        return MP_POSE_EDGES
    subset_edges = load_subset_edges(manifest_dir, num_joints)
    if subset_edges:
        return subset_edges
    for row in rows:
        edges = extract_bvh_edges(Path(row.get("source_path", "")))
        if edges:
            return [(i, j) for i, j in edges if 0 <= i < num_joints and 0 <= j < num_joints]
    return [(i - 1, i) for i in range(1, num_joints)]


def edge2mat(link: Sequence[Tuple[int, int]], num_node: int) -> np.ndarray:
    adj = np.zeros((num_node, num_node), dtype=np.float32)
    for i, j in link:
        adj[j, i] = 1.0
    return adj


def normalize_digraph(adj: np.ndarray) -> np.ndarray:
    degree = np.sum(adj, 0)
    h, w = adj.shape
    norm = np.zeros((w, w), dtype=np.float32)
    for i in range(w):
        if degree[i] > 0:
            norm[i, i] = degree[i] ** (-1)
    return np.dot(adj, norm)


def build_agcn_adjacency(num_joints: int, edges: Sequence[Tuple[int, int]]) -> np.ndarray:
    self_link = [(i, i) for i in range(num_joints)]
    inward = [(dst, src) for src, dst in edges]
    outward = [(j, i) for i, j in inward]
    identity = edge2mat(self_link, num_joints)
    inward_mat = normalize_digraph(edge2mat(inward, num_joints))
    outward_mat = normalize_digraph(edge2mat(outward, num_joints))
    return np.stack((identity, inward_mat, outward_mat)).astype(np.float32)


def conv_branch_init(conv: nn.Conv2d, branches: int) -> None:
    weight = conv.weight
    n = weight.size(0)
    k1 = weight.size(1)
    k2 = weight.size(2)
    nn.init.normal_(weight, 0, math.sqrt(2.0 / (n * k1 * k2 * branches)))
    if conv.bias is not None:
        nn.init.constant_(conv.bias, 0.0)


def conv_init(conv: nn.Conv2d) -> None:
    nn.init.kaiming_normal_(conv.weight, mode="fan_out")
    if conv.bias is not None:
        nn.init.constant_(conv.bias, 0.0)


def bn_init(bn: nn.BatchNorm2d, scale: float) -> None:
    nn.init.constant_(bn.weight, scale)
    nn.init.constant_(bn.bias, 0.0)


class UnitTCN(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 9, stride: int = 1):
        super().__init__()
        pad = int((kernel_size - 1) / 2)
        self.conv = nn.Conv2d(
            in_channels,
            out_channels,
            kernel_size=(kernel_size, 1),
            padding=(pad, 0),
            stride=(stride, 1),
        )
        self.bn = nn.BatchNorm2d(out_channels)
        conv_init(self.conv)
        bn_init(self.bn, 1.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.bn(self.conv(x))


class UnitGCN(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, adjacency: np.ndarray, coff_embedding: int = 4, num_subset: int = 3):
        super().__init__()
        inter_channels = max(1, out_channels // coff_embedding)
        self.inter_c = inter_channels
        self.num_subset = num_subset
        self.register_buffer("a_base", torch.from_numpy(adjacency.astype(np.float32)))
        self.pa = nn.Parameter(torch.from_numpy(adjacency.astype(np.float32)))

        self.conv_a = nn.ModuleList()
        self.conv_b = nn.ModuleList()
        self.conv_d = nn.ModuleList()
        for _ in range(self.num_subset):
            self.conv_a.append(nn.Conv2d(in_channels, inter_channels, 1))
            self.conv_b.append(nn.Conv2d(in_channels, inter_channels, 1))
            self.conv_d.append(nn.Conv2d(in_channels, out_channels, 1))

        if in_channels != out_channels:
            self.down = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.down = nn.Identity()

        self.bn = nn.BatchNorm2d(out_channels)
        self.soft = nn.Softmax(-2)
        self.relu = nn.ReLU(inplace=True)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                conv_init(m)
            elif isinstance(m, nn.BatchNorm2d):
                bn_init(m, 1.0)
        bn_init(self.bn, 1e-6)
        for i in range(self.num_subset):
            conv_branch_init(self.conv_d[i], self.num_subset)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        n, c, t, v = x.size()
        a = self.a_base.to(x.device) + self.pa
        y = None
        for i in range(self.num_subset):
            a1 = self.conv_a[i](x).permute(0, 3, 1, 2).contiguous().view(n, v, self.inter_c * t)
            a2 = self.conv_b[i](x).view(n, self.inter_c * t, v)
            a1 = self.soft(torch.matmul(a1, a2) / max(1, a1.size(-1)))
            a1 = a1 + a[i]
            a2 = x.view(n, c * t, v)
            z = self.conv_d[i](torch.matmul(a2, a1).view(n, c, t, v))
            y = z + y if y is not None else z
        y = self.bn(y)
        y = y + self.down(x)
        return self.relu(y)


class TCNGCNUnit(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, adjacency: np.ndarray, stride: int = 1, residual: bool = True):
        super().__init__()
        self.gcn1 = UnitGCN(in_channels, out_channels, adjacency)
        self.tcn1 = UnitTCN(out_channels, out_channels, stride=stride)
        self.relu = nn.ReLU(inplace=True)
        if not residual:
            self.residual = lambda x: 0
        elif (in_channels == out_channels) and (stride == 1):
            self.residual = lambda x: x
        else:
            self.residual = UnitTCN(in_channels, out_channels, kernel_size=1, stride=stride)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.relu(self.tcn1(self.gcn1(x)) + self.residual(x))


class AGCNEmotion(nn.Module):
    def __init__(self, in_channels: int, num_classes: int, num_joints: int, adjacency: np.ndarray, num_person: int = 1):
        super().__init__()
        self.data_bn = nn.BatchNorm1d(num_person * in_channels * num_joints)
        self.l1 = TCNGCNUnit(in_channels, 64, adjacency, residual=False)
        self.l2 = TCNGCNUnit(64, 64, adjacency)
        self.l3 = TCNGCNUnit(64, 64, adjacency)
        self.l4 = TCNGCNUnit(64, 64, adjacency)
        self.l5 = TCNGCNUnit(64, 128, adjacency, stride=2)
        self.l6 = TCNGCNUnit(128, 128, adjacency)
        self.l7 = TCNGCNUnit(128, 128, adjacency)
        self.l8 = TCNGCNUnit(128, 256, adjacency, stride=2)
        self.l9 = TCNGCNUnit(256, 256, adjacency)
        self.l10 = TCNGCNUnit(256, 256, adjacency)
        self.head = nn.Linear(256, num_classes)
        nn.init.normal_(self.head.weight, 0, math.sqrt(2.0 / num_classes))
        nn.init.constant_(self.head.bias, 0.0)
        bn_init(self.data_bn, 1.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        n, c, t, v, m = x.size()
        x = x.permute(0, 4, 3, 1, 2).contiguous().view(n, m * v * c, t)
        x = self.data_bn(x)
        x = x.view(n, m, v, c, t).permute(0, 1, 3, 4, 2).contiguous().view(n * m, c, t, v)

        x = self.l1(x)
        x = self.l2(x)
        x = self.l3(x)
        x = self.l4(x)
        x = self.l5(x)
        x = self.l6(x)
        x = self.l7(x)
        x = self.l8(x)
        x = self.l9(x)
        x = self.l10(x)

        c_new = x.size(1)
        x = x.view(n, m, c_new, -1)
        x = x.mean(3).mean(1)
        return self.head(x)


def compute_class_weights(dataset: SkeletonEmotionDataset, num_classes: int) -> torch.Tensor:
    counts = np.zeros((num_classes,), dtype=np.float32)
    for _, y, _ in dataset.items:
        counts[y] += 1
    counts = np.maximum(counts, 1.0)
    weights = counts.sum() / counts
    return torch.tensor(weights / weights.mean(), dtype=torch.float32)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, n_cls: int) -> Dict[str, float]:
    acc = float((y_true == y_pred).mean()) if len(y_true) else 0.0
    f1_list = []
    recall_list = []
    for c in range(n_cls):
        tp = np.sum((y_true == c) & (y_pred == c))
        fp = np.sum((y_true != c) & (y_pred == c))
        fn = np.sum((y_true == c) & (y_pred != c))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        f1_list.append(float(f1))
        recall_list.append(float(recall))
    return {"acc": acc, "macro_f1": float(np.mean(f1_list)), "uar": float(np.mean(recall_list))}


def run_epoch(model, loader, criterion, optimizer, device, num_classes: int):
    is_train = optimizer is not None
    model.train(is_train)
    losses: List[float] = []
    ys: List[int] = []
    ps: List[int] = []
    for x, y, _ in loader:
        x = x.to(device)
        y = y.to(device)
        logits = model(x)
        loss = criterion(logits, y)
        if is_train:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        losses.append(float(loss.item()))
        pred = torch.argmax(logits, dim=1)
        ys.extend(y.detach().cpu().numpy().tolist())
        ps.extend(pred.detach().cpu().numpy().tolist())
    metrics = compute_metrics(np.array(ys), np.array(ps), n_cls=num_classes)
    metrics["loss"] = float(np.mean(losses)) if losses else math.nan
    return metrics


def maybe_load_init_checkpoint(model: nn.Module, checkpoint_path: str) -> Dict[str, object]:
    if not checkpoint_path:
        return {"used": False, "loaded_keys": 0, "skipped_keys": 0, "path": ""}
    ckpt_path = Path(checkpoint_path).expanduser().resolve()
    ckpt = torch.load(ckpt_path, map_location="cpu")
    state = ckpt["model_state"] if isinstance(ckpt, dict) and "model_state" in ckpt else ckpt
    current = model.state_dict()
    filtered = {}
    skipped = []
    for key, value in state.items():
        if key.startswith("head."):
            skipped.append(key)
            continue
        if key in current and tuple(current[key].shape) == tuple(value.shape):
            filtered[key] = value
        else:
            skipped.append(key)
    missing, unexpected = model.load_state_dict(filtered, strict=False)
    print(
        f"[INIT] loaded={len(filtered)} skipped={len(skipped)} missing_after_load={len(missing)} "
        f"unexpected_after_load={len(unexpected)} path={ckpt_path}"
    )
    return {
        "used": True,
        "loaded_keys": len(filtered),
        "skipped_keys": len(skipped),
        "path": str(ckpt_path),
    }


def parse_args():
    parser = argparse.ArgumentParser("Train AGCN baseline for skeleton emotion recognition")
    parser.add_argument("--manifest-csv", type=str, default="experiments/pose/session5_skeleton_shared21/skeleton_manifest.csv")
    parser.add_argument("--out-dir", type=str, default="experiments/pose/session5_shared21_agcn")
    parser.add_argument("--seq-len", type=int, default=96)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=35)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--label-smoothing", type=float, default=0.0)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--group-key", type=str, default="auto")
    parser.add_argument("--early-stop-patience", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--max-train-samples", type=int, default=0)
    parser.add_argument("--max-val-samples", type=int, default=0)
    parser.add_argument("--init-checkpoint", type=str, default="", help="Optional warm-start checkpoint to initialize backbone weights")
    return parser.parse_args()


def maybe_trim_rows(rows: List[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
    if limit <= 0 or len(rows) <= limit:
        return rows
    return rows[:limit]


def main():
    args = parse_args()
    seed_everything(args.seed)
    manifest_csv = Path(args.manifest_csv).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = load_manifest(manifest_csv)
    if len(rows) < 10:
        raise RuntimeError("Too few samples in manifest.")
    label2id = build_label_mapping(rows)
    rows = [r for r in rows if r["label"] in label2id]
    train_rows, val_rows = split_by_group(rows, args.val_ratio, args.seed, args.group_key)
    train_rows = maybe_trim_rows(train_rows, args.max_train_samples)
    val_rows = maybe_trim_rows(val_rows, args.max_val_samples)
    train_ds = SkeletonEmotionDataset(train_rows, args.seq_len, label2id)
    val_ds = SkeletonEmotionDataset(val_rows, args.seq_len, label2id)
    if len(train_ds) == 0 or len(val_ds) == 0:
        raise RuntimeError("Empty train/val split. Try another val_ratio, seed, or group_key.")
    edges = resolve_edges(rows, train_ds.num_joints, manifest_csv.parent)
    adjacency = build_agcn_adjacency(train_ds.num_joints, edges)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers, pin_memory=True)
    model = AGCNEmotion(train_ds.in_channels, len(label2id), train_ds.num_joints, adjacency)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    init_info = maybe_load_init_checkpoint(model, args.init_checkpoint)
    criterion = nn.CrossEntropyLoss(
        weight=compute_class_weights(train_ds, len(label2id)).to(device),
        label_smoothing=args.label_smoothing,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    best_uar = -1.0
    best_epoch = 0
    no_improve_epochs = 0
    resolved_group_key = choose_group_key(rows, args.group_key)
    history: List[Dict[str, float]] = []
    for epoch in range(1, args.epochs + 1):
        tr = run_epoch(model, train_loader, criterion, optimizer, device, len(label2id))
        va = run_epoch(model, val_loader, criterion, None, device, len(label2id))
        line = {
            "epoch": epoch,
            "train_loss": tr["loss"],
            "train_acc": tr["acc"],
            "train_macro_f1": tr["macro_f1"],
            "train_uar": tr["uar"],
            "val_loss": va["loss"],
            "val_acc": va["acc"],
            "val_macro_f1": va["macro_f1"],
            "val_uar": va["uar"],
        }
        history.append(line)
        print(
            "[E%03d] train loss=%.4f acc=%.4f f1=%.4f uar=%.4f | val loss=%.4f acc=%.4f f1=%.4f uar=%.4f"
            % (
                epoch,
                line["train_loss"],
                line["train_acc"],
                line["train_macro_f1"],
                line["train_uar"],
                line["val_loss"],
                line["val_acc"],
                line["val_macro_f1"],
                line["val_uar"],
            )
        )
        if line["val_uar"] > best_uar:
            best_uar = line["val_uar"]
            best_epoch = epoch
            no_improve_epochs = 0
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "label2id": label2id,
                    "seq_len": args.seq_len,
                    "in_channels": train_ds.in_channels,
                    "num_joints": train_ds.num_joints,
                    "edges": list(edges),
                    "group_key": resolved_group_key,
                    "best_epoch": best_epoch,
                    "best_val_uar": best_uar,
                    "init_checkpoint": init_info["path"],
                    "init_loaded_keys": init_info["loaded_keys"],
                },
                out_dir / "best_model.pt",
            )
        else:
            no_improve_epochs += 1
        if args.early_stop_patience > 0 and no_improve_epochs >= args.early_stop_patience:
            print(f"[EARLY_STOP] no improvement for {no_improve_epochs} epochs, best_epoch={best_epoch}")
            break
    with open(out_dir / "history.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)
    print(f"[DONE] labels={label2id}")
    print(f"[DONE] split_group={resolved_group_key}")
    print(f"[DONE] best_epoch={best_epoch}")
    print(f"[DONE] best_val_uar={best_uar:.4f}")
    print(f"[DONE] best model: {out_dir / 'best_model.pt'}")


if __name__ == "__main__":
    main()
