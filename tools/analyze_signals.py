#!/usr/bin/env python3
"""Analyze DStat chronoamperometry captures.

Reads the tab-separated text files produced by the DStat GUI
(``test_signals/*.txt``) and reports, per capture:

  * basic statistics (mean, std, min, max, peak-to-peak, RMS noise, CV)
  * comparison against the Ohm's-law expectation (V_cell / R_test)
  * FFT spectrum (dominant frequency, noise floor, SNR estimate)

Optionally writes a summary CSV and PNG figures.

Usage:
    python tools/analyze_signals.py
    python tools/analyze_signals.py --dir test_signals --out test_signals/analysis
    python tools/analyze_signals.py --no-plot
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
FILENAME_RE = re.compile(
    r"chrono_(?P<pot>[\d.]+)mV_(?P<gain>[\d.]+)(?P<gain_unit>[kM]?)ohm"
    r"_R(?P<r>[\d.]+)(?P<r_unit>[kM]?)_(?P<freq>[\d.]+)Hz_"
    r"(?P<shield>[A-Za-z_]+)_(?P<idx>\d+)\.txt$",
    re.IGNORECASE,
)


def _unit_to_ohms(value: str, unit: str) -> float:
    v = float(value)
    u = (unit or "").lower()
    if u == "k":
        return v * 1e3
    if u == "m":
        return v * 1e6
    return v


def parse_filename(name: str) -> dict | None:
    m = FILENAME_RE.match(name)
    if not m:
        return None
    d = m.groupdict()
    pot_mv = float(d["pot"])
    gain_ohm = _unit_to_ohms(d["gain"], d["gain_unit"])
    r_ohm = _unit_to_ohms(d["r"], d["r_unit"])
    return {
        "potential_mV": pot_mv,
        "gain_ohm": gain_ohm,
        "r_test_ohm": r_ohm,
        "sample_rate_hz": float(d["freq"]),
        "shield": d["shield"],
        "index": d["idx"],
        "expected_current_A": (pot_mv / 1000.0) / r_ohm,
    }


def load_signal(path: Path) -> tuple[np.ndarray, np.ndarray]:
    times, currents = [], []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                t = float(parts[0])
                i = float(parts[1])
            except ValueError:
                continue
            times.append(t)
            currents.append(i)
    return np.asarray(times, dtype=float), np.asarray(currents, dtype=float)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def analyze(times: np.ndarray, currents: np.ndarray, meta: dict) -> dict:
    n = len(currents)
    dt = np.diff(times)
    dt_med = float(np.median(dt)) if len(dt) else 0.0
    fs = 1.0 / dt_med if dt_med > 0 else 0.0

    mean = float(np.mean(currents))
    std = float(np.std(currents, ddof=1)) if n > 1 else 0.0
    vmin = float(np.min(currents))
    vmax = float(np.max(currents))
    p2p = vmax - vmin
    rms_ac = float(np.sqrt(np.mean((currents - mean) ** 2)))
    cv_pct = (std / mean * 100.0) if mean != 0 else float("nan")

    expected = meta["expected_current_A"]
    err_pct = ((mean - expected) / expected * 100.0) if expected != 0 else float("nan")

    # FFT (one-sided magnitude, excluding DC bin)
    if n > 4 and fs > 0:
        # detrend to remove DC
        x = currents - mean
        # use a Hann window to reduce leakage
        w = np.hanning(n)
        spectrum = np.abs(np.fft.rfft(x * w))
        freqs = np.fft.rfftfreq(n, d=dt_med)
        # skip DC (index 0) and very low bins
        mag = spectrum[1:]
        fr = freqs[1:]
        if len(mag):
            peak_idx = int(np.argmax(mag))
            peak_freq = float(fr[peak_idx])
            peak_mag = float(mag[peak_idx])
            # noise floor = median of spectrum excluding the peak neighbourhood
            mask = np.ones(len(mag), dtype=bool)
            lo = max(0, peak_idx - 2)
            hi = min(len(mag), peak_idx + 3)
            mask[lo:hi] = False
            noise_floor = float(np.median(mag[mask])) if mask.any() else float(np.median(mag))
            snr_db = 20 * np.log10(peak_mag / noise_floor) if noise_floor > 0 else float("inf")
        else:
            peak_freq = 0.0
            peak_mag = 0.0
            noise_floor = 0.0
            snr_db = float("nan")
    else:
        freqs = np.array([])
        spectrum = np.array([])
        peak_freq = 0.0
        peak_mag = 0.0
        noise_floor = 0.0
        snr_db = float("nan")

    return {
        "n": n,
        "duration_s": float(times[-1] - times[0]) if n else 0.0,
        "fs_hz": fs,
        "mean_A": mean,
        "std_A": std,
        "min_A": vmin,
        "max_A": vmax,
        "p2p_A": p2p,
        "rms_noise_A": rms_ac,
        "cv_pct": cv_pct,
        "expected_A": expected,
        "error_pct": err_pct,
        "peak_freq_hz": peak_freq,
        "peak_mag": peak_mag,
        "noise_floor": noise_floor,
        "snr_db": snr_db,
        "_freqs": freqs,
        "_spectrum": spectrum,
        "_currents": currents,
        "_times": times,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def fmt(x, spec=".4g"):
    if x is None:
        return ""
    try:
        if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
            return "nan" if np.isnan(x) else "inf"
    except Exception:
        pass
    return format(x, spec)


def print_table(rows: list[dict]):
    cols = [
        ("file", "file", 46),
        ("pot (mV)", "potential_mV", 8),
        ("R (ohm)", "r_test_ohm", 10),
        ("fs (Hz)", "sample_rate_hz", 8),
        ("N", "n", 6),
        ("mean (A)", "mean_A", 12),
        ("std (A)", "std_A", 12),
        ("p2p (A)", "p2p_A", 12),
        ("expected (A)", "expected_A", 12),
        ("error %", "error_pct", 8),
        ("peak f (Hz)", "peak_freq_hz", 10),
        ("SNR (dB)", "snr_db", 8),
    ]
    header = "  ".join(c[0].ljust(c[2]) for c in cols)
    print(header)
    print("-" * len(header))
    for r in rows:
        vals = []
        for _, key, w in cols:
            if key == "file":
                vals.append(str(r["file"])[:w].ljust(w))
            else:
                v = r["stats"][key] if key in r["stats"] else r.get(key)
                vals.append(fmt(v).ljust(w))
        print("  ".join(vals))


def make_plots(rows: list[dict], out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    # Per-file figure: time series + FFT
    for r in rows:
        s = r["stats"]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6))
        ax1.plot(s["_times"], s["_currents"], linewidth=0.8, color="#0d9488")
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Current (A)")
        ax1.set_title("%s  (mean=%.3g A, std=%.3g A)" % (r["file"], s["mean_A"], s["std_A"]))
        ax1.grid(True, alpha=0.3, linestyle="--")
        if s["_spectrum"].size:
            ax2.plot(s["_freqs"][1:], s["_spectrum"][1:], linewidth=0.8, color="#0d9488")
            ax2.set_xlabel("Frequency (Hz)")
            ax2.set_ylabel("|FFT|")
            ax2.set_title("Spectrum (peak %.2f Hz, SNR %.1f dB)" % (s["peak_freq_hz"], s["snr_db"]))
            ax2.grid(True, alpha=0.3, linestyle="--")
            ax2.set_yscale("log")
        fig.tight_layout()
        fig.savefig(out_dir / (Path(r["file"]).stem + ".png"), dpi=120)
        plt.close(fig)

    # Summary figure: mean current per file with error bars + expected
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = [r["file"] for r in rows]
    means = [r["stats"]["mean_A"] for r in rows]
    stds = [r["stats"]["std_A"] for r in rows]
    expecteds = [r["stats"]["expected_A"] for r in rows]
    x = np.arange(len(rows))
    ax.bar(x, means, yerr=stds, capsize=4, color="#0d9488", alpha=0.75, label="measured mean ± std")
    ax.plot(x, expecteds, "rx", markersize=10, label="Ohm expectation")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Current (A)")
    ax.set_title("Measured vs expected current")
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "summary.png", dpi=120)
    plt.close(fig)
    print("Figures saved to", out_dir)


def main():
    ap = argparse.ArgumentParser(description="Analyze DStat chronoamperometry captures.")
    ap.add_argument("--dir", default="test_signals", help="directory with capture files")
    ap.add_argument("--out", default=None, help="output directory for CSV/figures (default: <dir>/analysis)")
    ap.add_argument("--no-plot", action="store_true", help="skip generating figures")
    ap.add_argument("--pattern", default="*.txt", help="glob pattern for capture files")
    args = ap.parse_args()

    base = Path(args.dir)
    if not base.exists():
        print("Directory not found:", base, file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else base / "analysis"

    files = sorted(base.glob(args.pattern))
    if not files:
        print("No capture files found in", base, file=sys.stderr)
        return 1

    rows = []
    for f in files:
        meta = parse_filename(f.name)
        if meta is None:
            print("Skipping (unrecognized name):", f.name, file=sys.stderr)
            continue
        times, currents = load_signal(f)
        if len(currents) == 0:
            print("Skipping (no data):", f.name, file=sys.stderr)
            continue
        stats = analyze(times, currents, meta)
        rows.append({"file": f.name, "meta": meta, "stats": stats})

    if not rows:
        print("No valid captures.", file=sys.stderr)
        return 1

    print_table([{ "file": r["file"], "stats": r["stats"],
                   "potential_mV": r["meta"]["potential_mV"],
                   "r_test_ohm": r["meta"]["r_test_ohm"],
                   "sample_rate_hz": r["meta"]["sample_rate_hz"],
                   "n": r["stats"]["n"],
                   "mean_A": r["stats"]["mean_A"],
                   "std_A": r["stats"]["std_A"],
                   "p2p_A": r["stats"]["p2p_A"],
                   "expected_A": r["stats"]["expected_A"],
                   "error_pct": r["stats"]["error_pct"],
                   "peak_freq_hz": r["stats"]["peak_freq_hz"],
                   "snr_db": r["stats"]["snr_db"],
                 } for r in rows])

    # Write summary CSV
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "summary.csv"
    fieldnames = [
        "file", "potential_mV", "gain_ohm", "r_test_ohm", "sample_rate_hz",
        "shield", "n", "duration_s", "fs_hz", "mean_A", "std_A", "min_A",
        "max_A", "p2p_A", "rms_noise_A", "cv_pct", "expected_A", "error_pct",
        "peak_freq_hz", "peak_mag", "noise_floor", "snr_db",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            m = r["meta"]
            s = r["stats"]
            w.writerow({
                "file": r["file"],
                "potential_mV": m["potential_mV"],
                "gain_ohm": m["gain_ohm"],
                "r_test_ohm": m["r_test_ohm"],
                "sample_rate_hz": m["sample_rate_hz"],
                "shield": m["shield"],
                "n": s["n"],
                "duration_s": s["duration_s"],
                "fs_hz": s["fs_hz"],
                "mean_A": s["mean_A"],
                "std_A": s["std_A"],
                "min_A": s["min_A"],
                "max_A": s["max_A"],
                "p2p_A": s["p2p_A"],
                "rms_noise_A": s["rms_noise_A"],
                "cv_pct": s["cv_pct"],
                "expected_A": s["expected_A"],
                "error_pct": s["error_pct"],
                "peak_freq_hz": s["peak_freq_hz"],
                "peak_mag": s["peak_mag"],
                "noise_floor": s["noise_floor"],
                "snr_db": s["snr_db"],
            })
    print("\nSummary CSV:", csv_path)

    if not args.no_plot:
        make_plots(rows, out_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
