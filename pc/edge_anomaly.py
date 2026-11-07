"""Edge anomaly detector, written to be portable to an ESP32.

Pure Python, no numpy, O(1) memory (a handful of floats). The logic is ~25 lines and
ports directly to C++/Arduino or MicroPython. It is NOT Isolation Forest (which needs
scikit-learn and won't fit on an ESP32): it is Holt (level+trend) smoothing with a
robust residual threshold:

  * predict the next reading from level + trend (follows the normal daily warm-up),
  * flag a reading that overshoots the prediction by > k * typical residual,
  * require `confirm` consecutive overshoots (rejects single-sample sensor glitches),
  * while anomalous, "coast" on the prediction instead of learning from the spike, so
    a long heat pocket is not absorbed into the baseline.
"""


class EdgeAnomalyDetector:
    def __init__(self, alpha=0.5, beta=0.15, k=3.0, sigma_floor=0.4,
                 warmup=6, confirm=2, max_run=16):
        self.alpha, self.beta, self.k = alpha, beta, k
        self.sigma_floor, self.warmup = sigma_floor, warmup
        self.confirm, self.max_run = confirm, max_run
        self.n = 0
        self.level = 0.0
        self.trend = 0.0
        self.sigma = 0.6      # running typical |residual| (x1.25 ~ std)
        self.run = 0

    def update(self, x):
        """Feed one temperature reading; returns True if a heat anomaly is confirmed."""
        self.n += 1
        if self.n == 1:
            self.level = x
            return False
        pred = self.level + self.trend
        resid = x - pred
        thr = self.k * max(self.sigma, self.sigma_floor)
        spike = self.n > self.warmup and resid > thr
        self.run = self.run + 1 if spike else 0

        if self.run >= self.max_run:          # sustained: accept the new regime
            self.level, self.trend, self.run = x, 0.0, 0
            return False
        if spike:                              # coast, do not learn from the anomaly
            self.level = pred
        else:
            new_level = self.alpha * x + (1 - self.alpha) * pred
            self.trend = self.beta * (new_level - self.level) + (1 - self.beta) * self.trend
            self.level = new_level
            self.sigma = 0.9 * self.sigma + 0.1 * 1.25 * abs(resid)
        return self.run >= self.confirm
