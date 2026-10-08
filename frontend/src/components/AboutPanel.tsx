import type { ModelsInfo } from "../api/client";

export function AboutPanel({ models }: { models?: ModelsInfo }) {
  const sizes = models
    ? `${models.student.params.toLocaleString()} parameters, ${models.compression.toFixed(1)}x fewer than the teacher's ${models.teacher.params.toLocaleString()}`
    : "about 6x fewer parameters than the teacher";
  return (
    <section className="panel method">
      <h2>Method</h2>
      <p>
        EQTransformer is a deep-learning model that detects earthquakes and picks the arrival
        times of P and S waves. In my final project at Braude College (with Shiraz Balmas) we
        compressed it using <strong>knowledge distillation</strong>: a small "student" network
        learns to imitate the original "teacher" while also learning from the true labels.
      </p>
      <p>
        The student has {sizes}, runs about 7x faster on a GPU in the thesis benchmarks (on this free CPU host the gap is smaller than the GPU result; see the measured times in the comparison card), and keeps the teacher's detection
        performance. This site runs both models side by side on real seismic data from EarthScope
        (IRIS), using earthquake catalogs from USGS.
      </p>
      <p>
        <a href="https://github.com/orshterenshus/eqt-live">Source code on GitHub</a> ·{" "}
        <a href="https://www.linkedin.com/in/or-shterenshus/">Or Shterenshus on LinkedIn</a> ·
        Original EQTransformer: Mousavi et al., Nature Communications (2020)
      </p>
    </section>
  );
}
