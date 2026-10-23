import sys
import threading
import queue
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from pase.user_support_tools import PASE_Logger

Number = Union[int, float]


@dataclass(frozen=True)
class EvalResult:
    tracking_active: bool
    n_source_points: int
    mf: Optional[float]


class InputsEvaluator:
    def __init__(
        self,
        *dicts: Dict[str, Any],
        nSourcePoints_threshold: int = 500,
        MF_threshold: int = 1,
        input_timeout: float = 15.0,  # timeout for user input in seconds
    ):
        if not dicts:
            raise ValueError("At least one dictionary must be provided")

        # Keep originals; aggregate a working view; and map each key to
        # its "owning" dict
        self._original_dicts: List[Dict[str, Any]] = []
        self.inputs: Dict[str, Any] = {}
        self._key_owner: Dict[str, int] = {}  # last-writer wins

        for idx, d in enumerate(dicts):
            if not isinstance(d, dict):
                raise TypeError("All arguments must be dictionaries")
            self._original_dicts.append(d)
            for k, v in d.items():
                self.inputs[k] = v
                self._key_owner[k] = idx

        # thresholds
        self.nSourcePoints_threshold = nSourcePoints_threshold
        self.MF_threshold = MF_threshold
        self.input_timeout = input_timeout

        # state
        self.tracking_active: Optional[bool] = None
        self.n_source_points: Optional[int] = None
        self.mf: Optional[float] = None

        self.run()

    # --- helpers for in-place updates ---
    def _set(self, key: str, value: Any) -> None:
        """Set key in the owning original dict AND in self.inputs (in place)."""
        self.inputs[key] = value
        idx = self._key_owner.get(key)
        if idx is None:
            idx = 0
            self._key_owner[key] = idx
        self._original_dicts[idx][key] = value

    # ---------- public API ----------
    def run(self) -> None:
        """
        Evaluate inputs, apply policy checks, and possibly edit input
        dictionaries in-place.
        """
        self.tracking_active = self._check_tracking()
        self.n_source_points = self._compute_nsourcepoints()
        self.mf = self._read_mf()
        self._policy_checks()

    def return_dicts(self) -> Tuple[Dict[str, Any], ...]:
        return tuple(self._original_dicts)

    # ---------- step 1: tracking ----------
    def _check_tracking(self) -> bool:
        if "Tracking" in self.inputs:
            val = self.inputs["Tracking"]
            if isinstance(val, bool):
                return val
            raise ValueError("'Tracking' must be a boolean (True/False).")

        if "RotationAxisNumber" in self.inputs:
            raw = self.inputs["RotationAxisNumber"]
            if isinstance(raw, bool):
                return raw
            if isinstance(raw, int) and raw in (0, 1):
                return bool(raw)
            raise ValueError("'RotationAxisNumber' must be a boolean or "
                             "integer 0/1.")

        return False

    # ---------- step 2: nSourcePoints ----------
    def _compute_nsourcepoints(self) -> int:
        required_keys = [
            "Xmin_InterestZone", "Xmax_InterestZone", "dX_InterestZone",
            "Ymin_InterestZone", "Ymax_InterestZone", "dY_InterestZone",
        ]
        if not all(k in self.inputs for k in required_keys):
            raise KeyError(f"Missing keys for InterestZone: {required_keys}")

        Xmin = float(self.inputs["Xmin_InterestZone"])
        Xmax = float(self.inputs["Xmax_InterestZone"])
        dX = float(self.inputs["dX_InterestZone"])
        Ymin = float(self.inputs["Ymin_InterestZone"])
        Ymax = float(self.inputs["Ymax_InterestZone"])
        dY = float(self.inputs["dY_InterestZone"])

        xrng = np.arange(Xmin, Xmax + dX, dX)
        yrng = np.arange(Ymin, Ymax + dY, dY)
        return xrng.size * yrng.size

    # ---------- step 3: MF ----------
    def _read_mf(self) -> Optional[int]:
        if "MF" not in self.inputs:
            return None
        val = self.inputs["MF"]
        if isinstance(val, (int)):
            return int(val)
        raise ValueError("'MF' must be numeric (int).")

    # ---------- timed input ----------
    def _timed_prompt(self, prompt: str, default: str) -> str:
        """Prompt with timeout. Returns default if no input after
        self.input_timeout."""
        q = queue.Queue()

        def reader(q):
            try:
                q.put(input(prompt))
            except Exception:
                q.put("")

        t = threading.Thread(target=reader, args=(q,), daemon=True)
        t.start()
        try:
            val = q.get(timeout=self.input_timeout)
        except queue.Empty:
            PASE_Logger(f"\n[INFO] No input after {self.input_timeout}s "
                        f"→ default '{default}'", level='INFO')
            return default

        resp = val.strip().lower()
        if resp == "":
            return default

        mapping = {
            "y": "y", "yes": "y",
            "n": "n", "no": "n",
            "e": "e", "edit": "e",
            "1": "1",
            "2": "2",
            "3": "3",
        }
        if resp in mapping:
            return mapping[resp]

        PASE_Logger(f"[WARNING] Invalid input '{resp}'. "
                    f"Using default '{default}'.", level='WARNING')
        return default

    # ---------- step 4: policy ----------
    def _policy_checks(self):
        if not self.tracking_active:
            return

        triggered = False
        if self.n_source_points > self.nSourcePoints_threshold:
            PASE_Logger(f"[WARNING] Tracking active with "
                        f"{self.n_source_points} points → expect longer "
                        f"runtime.",
                        level='WARNING')
            triggered = True

        if (
            self.mf is not None
            and self.n_source_points > self.nSourcePoints_threshold
            and self.mf > self.MF_threshold
        ):
            PASE_Logger(f"[WARNING] Tracking + "
                        f"{self.n_source_points} points + MF={self.mf} "
                        f"→ may cause memory issues.", level='WARNING')
            triggered = True

        if triggered:
            PASE_Logger("[INFO] Suggestions:"
                        "\n\t- reduce MF (reduces accuracy on diffuse "
                        "irr. modeling)"
                        "\n\t- coarsen the grid (reduces number of pixels to "
                        "approx. 100; this may slighlty offset the Xmax and Ymax values)"
                        "\n\t- deactivate tracking "
                        "(if applicable to your case)", level='INFO')

            resp = self._timed_prompt("Proceed anyway? [y]/n/e: ",
                                      default="y")
            if resp == "n":
                PASE_Logger("[INFO] Operation cancelled. Exiting.",
                            level='INFO')
                sys.exit(1)
            if resp == "e":
                self._edit_inputs()

    # ---------- edit flow ----------
    def _edit_inputs(self):
        choice = self._timed_prompt(
            "Edit options: 1) reduce MF, 2) coarsen grid, "
            "3) disable tracking. Choose: ",
            default=""  # empty default => do nothing on idle
        )
        if choice == "":
            PASE_Logger(f"[INFO] No input after {self.input_timeout}s "
                        f"→ keeping current parameters.", level='INFO')
            return

        if choice == "1":
            new_val = input("Enter new MF value: ").strip()
            try:
                new_mf = int(new_val)
                self._set("MF", new_mf)
                self.mf = new_mf
                PASE_Logger(f"[SUCCESS] MF set to {self.mf}", level='INFO')
            except ValueError:
                PASE_Logger("[ERROR] Invalid MF. Keeping previous value.",
                            level='ERROR')
        elif choice == "2":
            factor = np.sqrt(self.n_source_points / 100)
            if factor < 1:
                factor = 1
            self._set("dX_InterestZone",
                      float(self.inputs["dX_InterestZone"]) * factor)
            self._set("dY_InterestZone",
                      float(self.inputs["dY_InterestZone"]) * factor)
            self.n_source_points = self._compute_nsourcepoints()
            PASE_Logger(f"[SUCCESS] Grid coarsened → new nSourcePoints = "
                        f"{self.n_source_points}", level='INFO')
        elif choice == "3":
            if "Tracking" in self.inputs:
                self._set("Tracking", False)
            elif "RotationAxisNumber" in self.inputs:
                self._set("RotationAxisNumber", 0)
            self.tracking_active = False
            PASE_Logger("[SUCCESS] Tracking disabled.", level='INFO')


if __name__ == "__main__":
    params = {
        "RotationAxisNumber": 1,
        "Xmin_InterestZone": 0, "Xmax_InterestZone": 40, "dX_InterestZone": 0.5,
        "Ymin_InterestZone": 0, "Ymax_InterestZone": 40, "dY_InterestZone": 0.5,
        "MF": 5,
    }

    # Instantiate with thresholds
    evaluator = InputsEvaluator(
        params,
        nSourcePoints_threshold=500,  # runtime threshold
        MF_threshold=1,               # memory threshold
        input_timeout=15.0            # user idle timeout
    )

    PASE_Logger("\nUpdated dicts (in-place modifications):", level='INFO')
    PASE_Logger(evaluator.return_dicts(), level='INFO')
