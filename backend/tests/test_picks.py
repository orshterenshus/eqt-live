import numpy as np

from app.picks import downsample, extract_picks, stitch


def gaussian(center, n=6000, height=0.9, sigma=10):
    i = np.arange(n)
    return (height * np.exp(-((i - center) ** 2) / (2 * sigma**2))).astype(np.float32)


def test_stitch_places_windows_at_offsets_and_keeps_max():
    a = np.zeros(6000, np.float32)
    a[4000] = 0.4
    b = np.zeros(6000, np.float32)
    b[1000] = 0.8  # absolute sample 3000 + 1000 = 4000
    out = stitch(np.stack([a, b]), [0, 3000])
    assert out.shape == (9000,)
    assert out[4000] == np.float32(0.8)


def test_extract_picks_finds_peaks():
    det = np.full(6000, 0.9, np.float32)
    picks = extract_picks(det, gaussian(1500), gaussian(2700, height=0.6))
    assert picks.detected
    assert picks.p_index == 1500 and abs(picks.p_conf - 0.9) < 1e-6
    assert picks.s_index == 2700


def test_no_pick_below_threshold():
    det = np.full(6000, 0.9, np.float32)
    picks = extract_picks(det, gaussian(1500, height=0.2), gaussian(2700))
    assert picks.p_index is None and picks.p_conf is None
    assert picks.s_index == 2700


def test_no_detection_means_no_picks():
    picks = extract_picks(np.full(6000, 0.1, np.float32), gaussian(1500), gaussian(2700))
    assert not picks.detected
    assert picks.p_index is None and picks.s_index is None


def test_downsample_limits_points():
    x, step = downsample(np.arange(12000), max_points=3000)
    assert step == 4 and len(x) == 3000
    x, step = downsample(np.arange(100), max_points=3000)
    assert step == 1 and len(x) == 100
