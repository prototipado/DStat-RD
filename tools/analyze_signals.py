#!/usr/bin/env python3
"""Analyze DStat chronoamperometry and potential sweep captures.

Reads the tab-separated text files produced by the DStat GUI
(``test_signals/*.txt``, ``test_signals/sweep/*.txt``, etc.) and reports:

For Chronoamperometry (CA):
  * basic statistics (mean, std, min, max, peak-to-peak, RMS noise, CV)
  * comparison against the Ohm's-law expectation (V_cell / R_test)
  * FFT spectrum (dominant frequency, noise floor, SNR estimate)

For Linear Sweep (LSV / CV):
  * voltage range, current span, and data points
  * linear regression (Ohm's law): measured conductance (S), fitted resistance (Ω), offset current (A)
  * comparison against expected resistance (error %) and ideal Ohm's line
  * linearity metrics: R² determination coefficient, max non-linearity (% FS), RMS error / noise (% FS)
  * signal-to-noise ratio (SNR) of the sweep

Optionally writes summary CSV and PNG figures (time/FFT for chrono, I-V / residuals for sweep).

Usage:
    python tools/analyze_signals.py
    python tools/analyze_signals.py --dir docs/characterization/signals/sweep
    python tools/analyze_signals.py --dir docs/characterization/signals --recursive
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
    r"(?P<type>chrono|sweep|lsv|cv)_(?P<pot>[-+]?[\d.]+)mV_"
    r"(?P<gain>[\d.]+)(?P<gain_unit>[kM]?)(?:ohm)?"
    r"_R(?P<r>open|[\d.]+)(?P<r_unit>[kM]?)_"
    r"(?P<freq>[\d.]+)Hz_"
    r"(?P<shield>[A-Za-z0-9_]+)_(?P<idx>\d+)\.txt$",
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
    sig_type = d["type"].lower()
    if sig_type in ("lsv", "cv"):
        sig_type = "sweep"
    pot_mv = float(d["pot"])
    gain_ohm = _unit_to_ohms(d["gain"], d["gain_unit"])
    r_raw = d["r"].lower()
    if r_raw == "open":
        r_ohm = None
        expected = None
    else:
        r_ohm = _unit_to_ohms(d["r"], d["r_unit"])
        expected = (pot_mv / 1000.0) / r_ohm if sig_type == "chrono" else None
    return {
        "type": sig_type,
        "potential_mV": pot_mv,
        "gain_ohm": gain_ohm,
        "r_test_ohm": r_ohm,
        "r_test_label": "open (no resistor)" if r_ohm is None else "%g ohm" % r_ohm,
        "sample_rate_hz": float(d["freq"]),
        "shield": d["shield"],
        "index": d["idx"],
        "expected_current_A": expected,
    }


def load_signal(path: Path) -> tuple[np.ndarray, np.ndarray, str | None]:
    x_vals, currents = [], []
    detected_type = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                comment = line.lstrip("#").strip().lower()
                if "current_voltage" in comment:
                    detected_type = "sweep"
                elif "current_time" in comment:
                    detected_type = "chrono"
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                x = float(parts[0])
                i = float(parts[1])
            except ValueError:
                continue
            x_vals.append(x)
            currents.append(i)
    return np.asarray(x_vals, dtype=float), np.asarray(currents, dtype=float), detected_type


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def analyze_chrono(times: np.ndarray, currents: np.ndarray, meta: dict) -> dict:
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

    expected = meta.get("expected_current_A")
    if expected is None:
        err_pct = float("nan")
    else:
        err_pct = ((mean - expected) / expected * 100.0) if expected != 0 else float("nan")

    # FFT (one-sided magnitude, excluding DC bin)
    if n > 4 and fs > 0:
        x = currents - mean
        w = np.hanning(n)
        spectrum = np.abs(np.fft.rfft(x * w))
        freqs = np.fft.rfftfreq(n, d=dt_med)
        mag = spectrum[1:]
        fr = freqs[1:]
        if len(mag):
            peak_idx = int(np.argmax(mag))
            peak_freq = float(fr[peak_idx])
            peak_mag = float(mag[peak_idx])
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
        "type": "chrono",
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
        # Sweep fields as None
        "v_min_mV": None,
        "v_max_mV": None,
        "r_fit_ohm": None,
        "error_r_pct": None,
        "slope_S": None,
        "offset_A": None,
        "r2": None,
        "max_nonlin_A": None,
        "max_nonlin_pct": None,
        "rms_noise_pct": None,
        "_freqs": freqs,
        "_spectrum": spectrum,
        "_currents": currents,
        "_times": times,
    }


def analyze_sweep(voltages_mV: np.ndarray, currents: np.ndarray, meta: dict) -> dict:
    n = len(currents)
    v_V = voltages_mV / 1000.0
    v_min_mV = float(np.min(voltages_mV))
    v_max_mV = float(np.max(voltages_mV))
    v_span_V = float(np.ptp(v_V))

    i_min_A = float(np.min(currents))
    i_max_A = float(np.max(currents))
    i_span_A = float(np.ptp(currents))
    mean_A = float(np.mean(currents))
    std_A = float(np.std(currents, ddof=1)) if n > 1 else 0.0

    # Linear regression: I = m * V + b
    if n >= 2 and v_span_V > 0:
        poly = np.polyfit(v_V, currents, 1)
        slope_S = float(poly[0])      # Conductance (S)
        offset_A = float(poly[1])     # Zero-voltage current intercept (A)
        r_fit_ohm = (1.0 / slope_S) if slope_S != 0 else float("inf")

        i_fit = slope_S * v_V + offset_A
        res_fit = currents - i_fit
        ss_res = float(np.sum(res_fit ** 2))
        ss_tot = float(np.sum((currents - mean_A) ** 2))
        r2 = (1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")

        max_nonlin_A = float(np.max(np.abs(res_fit)))
        max_nonlin_pct = (max_nonlin_A / i_span_A * 100.0) if i_span_A > 0 else float("nan")
        rms_noise_A = float(np.sqrt(np.mean(res_fit ** 2)))
        rms_noise_pct = (rms_noise_A / i_span_A * 100.0) if i_span_A > 0 else float("nan")
        snr_db = (20.0 * np.log10((i_span_A / 2.0) / rms_noise_A)) if rms_noise_A > 0 else float("inf")
    else:
        slope_S = 0.0
        offset_A = mean_A
        r_fit_ohm = float("nan")
        i_fit = np.zeros_like(currents)
        res_fit = np.zeros_like(currents)
        r2 = float("nan")
        max_nonlin_A = 0.0
        max_nonlin_pct = float("nan")
        rms_noise_A = 0.0
        rms_noise_pct = float("nan")
        snr_db = float("nan")

    # Comparison against test resistor (Ohm's law)
    r_exp = meta.get("r_test_ohm")
    if r_exp is not None and r_exp > 0:
        error_r_pct = ((r_fit_ohm - r_exp) / r_exp * 100.0) if not np.isnan(r_fit_ohm) else float("nan")
        slope_exp_S = 1.0 / r_exp
        error_slope_pct = ((slope_S - slope_exp_S) / slope_exp_S * 100.0)
        i_ideal = v_V / r_exp
        res_ideal = currents - i_ideal
        max_err_ideal_A = float(np.max(np.abs(res_ideal)))
        max_err_ideal_pct = (max_err_ideal_A / i_span_A * 100.0) if i_span_A > 0 else float("nan")
        rms_err_ideal_A = float(np.sqrt(np.mean(res_ideal ** 2)))
    else:
        error_r_pct = float("nan")
        slope_exp_S = float("nan")
        error_slope_pct = float("nan")
        i_ideal = None
        max_err_ideal_A = float("nan")
        max_err_ideal_pct = float("nan")
        rms_err_ideal_A = float("nan")

    return {
        "type": "sweep",
        "n": n,
        "duration_s": 0.0,
        "fs_hz": meta.get("sample_rate_hz", 0.0),
        "mean_A": mean_A,
        "std_A": std_A,
        "min_A": i_min_A,
        "max_A": i_max_A,
        "p2p_A": i_span_A,
        "rms_noise_A": rms_noise_A,
        "rms_noise_pct": rms_noise_pct,
        "cv_pct": float("nan"),
        "expected_A": None,
        "error_pct": error_r_pct,
        "v_min_mV": v_min_mV,
        "v_max_mV": v_max_mV,
        "v_span_V": v_span_V,
        "slope_S": slope_S,
        "offset_A": offset_A,
        "r_fit_ohm": r_fit_ohm,
        "error_r_pct": error_r_pct,
        "error_slope_pct": error_slope_pct,
        "r2": r2,
        "max_nonlin_A": max_nonlin_A,
        "max_nonlin_pct": max_nonlin_pct,
        "max_err_ideal_A": max_err_ideal_A,
        "max_err_ideal_pct": max_err_ideal_pct,
        "rms_err_ideal_A": rms_err_ideal_A,
        "snr_db": snr_db,
        "peak_freq_hz": None,
        "peak_mag": None,
        "noise_floor": None,
        "_v_mV": voltages_mV,
        "_v_V": v_V,
        "_currents": currents,
        "_i_fit": i_fit,
        "_i_ideal": i_ideal,
        "_residuals": res_fit,
    }


def analyze(x_vals: np.ndarray, currents: np.ndarray, meta: dict, detected_type: str | None = None) -> dict:
    sig_type = detected_type or meta.get("type", "chrono")
    meta["type"] = sig_type
    if sig_type == "sweep":
        return analyze_sweep(x_vals, currents, meta)
    return analyze_chrono(x_vals, currents, meta)


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
    chrono_rows = [r for r in rows if r["stats"]["type"] == "chrono"]
    sweep_rows = [r for r in rows if r["stats"]["type"] == "sweep"]

    if chrono_rows:
        print("\n=== CHRONOAMPEROMETRY CAPTURES ===")
        cols_ca = [
            ("file", "file", 44),
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
        header = "  ".join(c[0].ljust(c[2]) for c in cols_ca)
        print(header)
        print("-" * len(header))
        for r in chrono_rows:
            vals = []
            for _, key, w in cols_ca:
                if key == "file":
                    vals.append(str(r["file"])[:w].ljust(w))
                elif key == "r_test_ohm":
                    v = r.get("r_test_ohm")
                    if v is None and "meta" in r:
                        v = r["meta"].get("r_test_ohm")
                    vals.append(("open" if v is None else fmt(v, ".3g")).ljust(w))
                else:
                    v = r["stats"].get(key)
                    if v is None and key in r.get("meta", {}):
                        v = r["meta"][key]
                    vals.append(fmt(v).ljust(w))
            print("  ".join(vals))

    if sweep_rows:
        print("\n=== POTENTIAL SWEEP CAPTURES (LINEARITY / OHM FIT) ===")
        cols_sw = [
            ("file", "file", 44),
            ("V range (mV)", "v_range", 18),
            ("R exp (ohm)", "r_test_ohm", 12),
            ("R fit (ohm)", "r_fit_ohm", 12),
            ("Error R %", "error_r_pct", 10),
            ("Offset (A)", "offset_A", 12),
            ("R^2", "r2", 10),
            ("NonLin (%FS)", "max_nonlin_pct", 13),
            ("RMS Err (A)", "rms_noise_A", 12),
            ("SNR (dB)", "snr_db", 8),
        ]
        header = "  ".join(c[0].ljust(c[2]) for c in cols_sw)
        print(header)
        print("-" * len(header))
        for r in sweep_rows:
            vals = []
            s = r["stats"]
            m = r["meta"]
            for _, key, w in cols_sw:
                if key == "file":
                    vals.append(str(r["file"])[:w].ljust(w))
                elif key == "v_range":
                    v_str = "[%g, %g]" % (s["v_min_mV"], s["v_max_mV"])
                    vals.append(v_str.ljust(w))
                elif key == "r_test_ohm":
                    v = m.get("r_test_ohm")
                    vals.append(("open" if v is None else fmt(v, ".3g")).ljust(w))
                elif key == "r2":
                    vals.append(fmt(s.get("r2"), ".6f").ljust(w))
                else:
                    v = s.get(key)
                    vals.append(fmt(v).ljust(w))
            print("  ".join(vals))


def make_plots(rows: list[dict], out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    chrono_rows = [r for r in rows if r["stats"]["type"] == "chrono"]
    sweep_rows = [r for r in rows if r["stats"]["type"] == "sweep"]

    # Per-file figures
    for r in rows:
        s = r["stats"]
        m = r["meta"]
        if s["type"] == "chrono":
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

        elif s["type"] == "sweep":
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7))
            v_mV = s["_v_mV"]
            i_A = s["_currents"]
            i_fit = s["_i_fit"]
            res = s["_residuals"]

            # Subplot 1: I-V curve
            ax1.plot(v_mV, i_A, linewidth=1.0, color="#0d9488", label="Measured I-V", alpha=0.9)
            ax1.plot(v_mV, i_fit, "r--", linewidth=1.1,
                     label="Linear fit (R=%.4g Ω, R²=%.6f)" % (s["r_fit_ohm"], s["r2"]))
            if s["_i_ideal"] is not None:
                ax1.plot(v_mV, s["_i_ideal"], "k:", linewidth=0.9,
                         label="Ideal Ohm (R=%g Ω)" % m["r_test_ohm"])

            ax1.set_xlabel("Potential (mV)")
            ax1.set_ylabel("Current (A)")
            err_str = "Err=%.3f%%" % s["error_r_pct"] if not np.isnan(s["error_r_pct"]) else "R_exp=None"
            ax1.set_title("%s  (R_fit=%.4g Ω, %s, R²=%.6f)" % (r["file"], s["r_fit_ohm"], err_str, s["r2"]), fontsize=10)
            ax1.grid(True, alpha=0.3, linestyle="--")
            ax1.legend(loc="best", fontsize=8)

            # Subplot 2: Residuals / Non-linearity
            ax2.plot(v_mV, res, linewidth=0.8, color="#0d9488", label="Residual (I_meas - I_fit)")
            ax2.axhline(0, color="gray", linestyle="--", linewidth=0.7)
            ax2.set_xlabel("Potential (mV)")
            ax2.set_ylabel("Residual (A)")
            ax2.set_title(
                "Non-linearity & Noise (Max: %.3g A / %.3f%% FS, RMS: %.3g A / %.3f%% FS, SNR: %.1f dB)" % (
                    s["max_nonlin_A"], s["max_nonlin_pct"], s["rms_noise_A"], s["rms_noise_pct"], s["snr_db"]
                ),
                fontsize=9
            )
            ax2.grid(True, alpha=0.3, linestyle="--")
            ax2.legend(loc="best", fontsize=8)

            fig.tight_layout()
            fig.savefig(out_dir / (Path(r["file"]).stem + ".png"), dpi=120)
            plt.close(fig)

    # Summary figure for Chrono
    if chrono_rows:
        fig, ax = plt.subplots(figsize=(10, 5))
        labels = [r["file"] for r in chrono_rows]
        means = [r["stats"]["mean_A"] for r in chrono_rows]
        stds = [r["stats"]["std_A"] for r in chrono_rows]
        expecteds = [r["stats"]["expected_A"] for r in chrono_rows]
        x = np.arange(len(chrono_rows))
        ax.bar(x, means, yerr=stds, capsize=4, color="#0d9488", alpha=0.75, label="measured mean ± std")
        ex_x = [i for i, e in enumerate(expecteds) if e is not None]
        ex_y = [e for e in expecteds if e is not None]
        if ex_x:
            ax.plot(ex_x, ex_y, "rx", markersize=10, label="Ohm expectation")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("Current (A)")
        ax.set_title("Chronoamperometry: Measured vs expected current")
        ax.grid(True, alpha=0.3, axis="y")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / "summary_chrono.png", dpi=120)
        plt.close(fig)

    # Summary figure for Sweep
    if sweep_rows:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        labels = [r["file"] for r in sweep_rows]
        r_fits = [r["stats"]["r_fit_ohm"] for r in sweep_rows]
        r_exps = [r["meta"]["r_test_ohm"] or 0.0 for r in sweep_rows]
        r2s = [r["stats"]["r2"] for r in sweep_rows]
        nonlins = [r["stats"]["max_nonlin_pct"] for r in sweep_rows]
        x = np.arange(len(sweep_rows))

        # Panel 1: R fit vs R exp
        ax1.bar(x - 0.15, r_fits, width=0.3, color="#0d9488", label="Fitted Resistance (Ω)")
        ax1.bar(x + 0.15, r_exps, width=0.3, color="#f59e0b", alpha=0.8, label="Expected Resistance (Ω)")
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, rotation=40, ha="right", fontsize=8)
        ax1.set_ylabel("Resistance (Ω)")
        ax1.set_title("Sweep: Resistance Fit vs Nominal")
        ax1.grid(True, alpha=0.3, axis="y")
        ax1.legend(fontsize=8)

        # Panel 2: Non-linearity (% FS) and R²
        ax2.bar(x, nonlins, width=0.4, color="#6366f1", alpha=0.8, label="Max Non-linearity (% FS)")
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, rotation=40, ha="right", fontsize=8)
        ax2.set_ylabel("Max Non-Linearity (% of Full Scale)")
        ax2.set_title("Sweep Linearity Metrics")
        ax2.grid(True, alpha=0.3, axis="y")
        ax2.legend(loc="upper left", fontsize=8)

        fig.tight_layout()
        fig.savefig(out_dir / "summary_sweep.png", dpi=120)
        plt.close(fig)

    print("Figures saved to", out_dir)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Analyze DStat chronoamperometry and sweep captures.")
    ap.add_argument("--dir", default="docs/characterization/signals", help="directory with capture files (default: docs/characterization/signals)")
    ap.add_argument("--out", default=None, help="output directory for CSV/figures (default: <dir>/analysis)")
    ap.add_argument("--no-plot", action="store_true", help="skip generating figures")
    ap.add_argument("--pattern", default="*.txt", help="glob pattern for capture files")
    ap.add_argument("-r", "--recursive", action="store_true", help="search subdirectories recursively")
    args = ap.parse_args()

    base = Path(args.dir)
    if not base.exists():
        print("Directory not found:", base, file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else base / "analysis"

    if args.recursive:
        files = sorted(base.rglob(args.pattern))
    else:
        files = sorted(base.glob(args.pattern))
        # If no files found in top dir but subdirectories exist, search recursively by default
        if not files:
            sub_files = sorted(base.rglob(args.pattern))
            if sub_files:
                files = sub_files

    if not files:
        print("No capture files found in", base, file=sys.stderr)
        return 1

    rows = []
    for f in files:
        meta = parse_filename(f.name)
        if meta is None:
            # Skip non-capture files silently or note
            continue
        times_or_v, currents, detected_type = load_signal(f)
        if len(currents) == 0:
            print("Skipping (no data):", f.name, file=sys.stderr)
            continue
        stats = analyze(times_or_v, currents, meta, detected_type)
        rows.append({"file": f.name, "path": f, "meta": meta, "stats": stats})

    if not rows:
        print("No valid captures found matching supported formats.", file=sys.stderr)
        return 1

    print_table(rows)

    # Write summary CSV
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "summary.csv"
    fieldnames = [
        "file", "type", "potential_mV", "gain_ohm", "r_test_ohm", "sample_rate_hz",
        "shield", "n", "v_min_mV", "v_max_mV", "r_fit_ohm", "error_r_pct",
        "slope_S", "offset_A", "r2", "max_nonlin_A", "max_nonlin_pct",
        "rms_noise_A", "rms_noise_pct", "duration_s", "fs_hz", "mean_A",
        "std_A", "min_A", "max_A", "p2p_A", "cv_pct", "expected_A",
        "error_pct", "peak_freq_hz", "peak_mag", "noise_floor", "snr_db",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            m = r["meta"]
            s = r["stats"]
            row_dict = {
                "file": r["file"],
                "type": s["type"],
                "potential_mV": m["potential_mV"],
                "gain_ohm": m["gain_ohm"],
                "r_test_ohm": m["r_test_ohm"],
                "sample_rate_hz": m["sample_rate_hz"],
                "shield": m["shield"],
                "n": s["n"],
                "v_min_mV": s["v_min_mV"],
                "v_max_mV": s["v_max_mV"],
                "r_fit_ohm": s["r_fit_ohm"],
                "error_r_pct": s["error_r_pct"],
                "slope_S": s["slope_S"],
                "offset_A": s["offset_A"],
                "r2": s["r2"],
                "max_nonlin_A": s["max_nonlin_A"],
                "max_nonlin_pct": s["max_nonlin_pct"],
                "rms_noise_A": s["rms_noise_A"],
                "rms_noise_pct": s["rms_noise_pct"],
                "duration_s": s["duration_s"],
                "fs_hz": s["fs_hz"],
                "mean_A": s["mean_A"],
                "std_A": s["std_A"],
                "min_A": s["min_A"],
                "max_A": s["max_A"],
                "p2p_A": s["p2p_A"],
                "cv_pct": s["cv_pct"],
                "expected_A": s["expected_A"],
                "error_pct": s["error_pct"],
                "peak_freq_hz": s["peak_freq_hz"],
                "peak_mag": s["peak_mag"],
                "noise_floor": s["noise_floor"],
                "snr_db": s["snr_db"],
            }
            # Clean nan / None
            for k, v in row_dict.items():
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    row_dict[k] = ""
            w.writerow(row_dict)
    print("\nSummary CSV:", csv_path)

    if not args.no_plot:
        make_plots(rows, out_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

