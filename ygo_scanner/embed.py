"""KI-Bildmerkmale (DINOv2) für robusten Artwork-Vergleich.

DINOv2 ist ein vortrainiertes Bildmodell von Meta, das sehr gut darin ist, "dasselbe Bild"
auch bei Unschärfe, Spiegelungen, Farbstich und leichter Verschiebung wiederzuerkennen.
"""
import warnings

import cv2
import numpy as np

from . import config  # noqa: F401 - setzt TORCH_HOME, bevor torch geladen wird
import torch  # noqa: E402

warnings.filterwarnings("ignore", message="xFormers is not available")

_MODEL = None
_DEVICE = "cpu"   # bewusst CPU: klein genug, und die Grafikkarte bleibt unangetastet
_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
_STD = np.array([0.229, 0.224, 0.225], np.float32)
SIZE = 224


def model():
    global _MODEL
    if _MODEL is None:
        _MODEL = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14", verbose=False)
        _MODEL.eval().to(_DEVICE)
    return _MODEL


def _prep(img_bgr: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(cv2.resize(img_bgr, (SIZE, SIZE), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
    x = (rgb.astype(np.float32) / 255.0 - _MEAN) / _STD
    return x.transpose(2, 0, 1)


@torch.inference_mode()
def embed(images: list[np.ndarray]) -> np.ndarray:
    """Gibt L2-normalisierte Merkmalsvektoren (N x 384) zurück."""
    x = torch.from_numpy(np.stack([_prep(i) for i in images])).to(_DEVICE)
    f = model()(x).float()
    f = torch.nn.functional.normalize(f, dim=1)
    return f.cpu().numpy()
