"""Product recognition by local image features (SIFT + RANSAC).
It looks for the same logo / text / pattern from a product's photo inside a shelf object, so a red can is no longer
mistaken for another red can. A product is only named when many feature points agree geometrically."""
try:
    import cv2
except Exception:
    cv2 = None
import numpy as np

MIN_INLIERS = 25         # feature points that must agree before a product is named
MIN_SHARE = 0.20         # ...and they must be at least this share of the object's/photo's feature points
MIN_RATIO = 1.3          # best product must have this many times more agreeing points than the runner-up
_SIDE = 360

_sift = None
_bf = None


def _engine():
    global _sift, _bf
    if _sift is None and cv2 is not None:
        _sift = cv2.SIFT_create(nfeatures=600)
        _bf = cv2.BFMatcher(cv2.NORM_L2)
    return _sift, _bf


def features(bgr):
    """(keypoint coordinates, descriptors) or None when the picture has too little detail."""
    if bgr is None or bgr.size == 0:
        return None
    h, w = bgr.shape[:2]
    if min(h, w) < 20:
        return None
    s = _SIDE / max(h, w)
    if s != 1:
        bgr = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    gray = cv2.createCLAHE(2.0, (4, 4)).apply(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    sift, _ = _engine()
    kp, des = sift.detectAndCompute(gray, None)
    if des is None or len(kp) < 8:
        return None
    return np.float32([k.pt for k in kp]), des


def agreeing_points(q, r):
    """How many feature points of query q sit in the same geometric place in reference r."""
    if q is None or r is None:
        return 0
    _, bf = _engine()
    try:
        pairs = bf.knnMatch(q[1], r[1], k=2)
    except cv2.error:
        return 0
    good = [m[0] for m in pairs if len(m) == 2 and m[0].distance < 0.72 * m[1].distance]
    if len(good) < 8:
        return 0
    src = q[0][[m.queryIdx for m in good]].reshape(-1, 1, 2)
    dst = r[0][[m.trainIdx for m in good]].reshape(-1, 1, 2)
    M, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    if M is None or mask is None:
        return 0
    inl = int(mask.sum())
    return inl if inl >= MIN_SHARE * min(len(q[0]), len(r[0])) else 0     # too small a share = coincidence


def best_product(query_feats, refs):
    """refs: [{id, name, feats: [features,...]}]. Returns (product or None, inliers, runner_up_inliers)."""
    if query_feats is None:
        return None, 0, 0
    scored = []
    for r in refs:
        pts = max((agreeing_points(query_feats, f) for f in r.get("feats", [])), default=0)
        scored.append((pts, r))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return None, 0, 0
    best, second = scored[0][0], (scored[1][0] if len(scored) > 1 else 0)
    if best >= MIN_INLIERS and best >= MIN_RATIO * max(second, 1):
        return scored[0][1], best, second
    return None, best, second
