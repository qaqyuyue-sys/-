// Shared, stateless helpers. Every value is a pure function of t.
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const smooth = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };
const easeInOut = k => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);

// Closed-form damped spring step response. x = seconds since the target changed.
function spring(x, w = 16, z = 0.75) {
  if (x <= 0) return 0;
  if (z >= 1) return 1 - Math.exp(-w * x) * (1 + w * x);
  const wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * x) * (Math.cos(wd * x) + (z * w / wd) * Math.sin(wd * x));
}

// A value that changes target many times: keys = [[time, value], ...] sorted by time.
// v(t) = v0 + Σ (v_i − v_{i−1}) · spring(t − t_i)
function track(keys, t, w = 16, z = 0.75) {
  let v = keys[0][1];
  for (let i = 1; i < keys.length; i++) v += (keys[i][1] - keys[i - 1][1]) * spring(t - keys[i][0], w, z);
  return v;
}

// Same as track, for [x, y] points.
function track2(keys, t, w, z) {
  return [track(keys.map(k => [k[0], k[1][0]]), t, w, z), track(keys.map(k => [k[0], k[1][1]]), t, w, z)];
}

// Seeded PRNG for anything that needs noise.
function rnd(seed) { const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453; return x - Math.floor(x); }
