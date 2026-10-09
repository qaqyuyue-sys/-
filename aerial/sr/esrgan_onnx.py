#!/usr/bin/env python3
"""Convert Real-ESRGAN .pth weights to ONNX without PyTorch, and upscale images.

The .pth zip is unpickled with a stub for torch's tensor-rebuild hooks; the two
architectures (SRVGGNetCompact = realesr-general-x4v3, RRDBNet = RealESRGAN_x4plus)
are rebuilt as ONNX graphs and run with onnxruntime on CPU, tile by tile.

  python esrgan_onnx.py convert realesr-general-x4v3.pth general.onnx
  python esrgan_onnx.py upscale general.onnx in.jpg out.jpg
"""
import pickle, sys, zipfile
import numpy as np


class _Storage:
    def __init__(self, data): self.data = data


def load_pth(path):
    z = zipfile.ZipFile(path)
    root = z.namelist()[0].split("/")[0]
    dtypes = {"FloatStorage": np.float32, "HalfStorage": np.float16, "LongStorage": np.int64}

    class U(pickle.Unpickler):
        def find_class(self, mod, name):
            if name == "_rebuild_tensor_v2":
                def rebuild(storage, offset, size, stride, *a):
                    arr = storage.data
                    n = int(np.prod(size)) if size else 1
                    out = np.lib.stride_tricks.as_strided(
                        arr[offset:], shape=size, strides=[s * arr.itemsize for s in stride]) if size else arr[offset:offset + 1]
                    return np.array(out, dtype=np.float32)
                return rebuild
            if name in dtypes:
                return dtypes[name]
            if mod.startswith("collections") and name == "OrderedDict":
                import collections; return collections.OrderedDict
            if mod.startswith("torch"):
                return lambda *a, **k: None
            return super().find_class(mod, name)

        def persistent_load(self, pid):
            _, dtype, key, _, numel = pid
            raw = z.read(f"{root}/data/{key}")
            return _Storage(np.frombuffer(raw, dtype=dtype))

    obj = U(z.open(f"{root}/data.pkl")).load()
    for k in ("params_ema", "params"):
        if isinstance(obj, dict) and k in obj:
            return obj[k]
    return obj


def build_onnx(w, out):
    import onnx
    from onnx import helper as h, TensorProto as T, numpy_helper as nh
    nodes, inits = [], []
    cnt = [0]

    def name(p): cnt[0] += 1; return f"{p}{cnt[0]}"

    def const(arr, n=None):
        n = n or name("c"); inits.append(nh.from_array(np.asarray(arr, np.float32), n)); return n

    def conv(x, k):
        wt = w[k + ".weight"]; o = name("conv")
        nodes.append(h.make_node("Conv", [x, const(wt), const(w[k + ".bias"])], [o], pads=[1, 1, 1, 1]))
        return o

    def lrelu(x):
        o = name("lr"); nodes.append(h.make_node("LeakyRelu", [x], [o], alpha=0.2)); return o

    def add(a, b):
        o = name("add"); nodes.append(h.make_node("Add", [a, b], [o])); return o

    def mul(a, s):
        o = name("mul"); nodes.append(h.make_node("Mul", [a, const(np.float32(s))], [o])); return o

    def up2(x):
        o = name("up"); nodes.append(h.make_node("Resize", [x, "", const([1, 1, 2, 2])], [o], mode="nearest")); return o

    x = "input"
    if "conv_first.weight" in w:                          # RRDBNet
        feat = conv(x, "conv_first"); b = feat
        nb = max(int(k.split(".")[1]) for k in w if k.startswith("body.")) + 1
        for i in range(nb):
            r = b
            for j in (1, 2, 3):
                p = f"body.{i}.rdb{j}"
                x1 = lrelu(conv(r, p + ".conv1"))
                c = name("cat"); nodes.append(h.make_node("Concat", [r, x1], [c], axis=1))
                x2 = lrelu(conv(c, p + ".conv2"))
                c2 = name("cat"); nodes.append(h.make_node("Concat", [r, x1, x2], [c2], axis=1))
                x3 = lrelu(conv(c2, p + ".conv3"))
                c3 = name("cat"); nodes.append(h.make_node("Concat", [r, x1, x2, x3], [c3], axis=1))
                x4 = lrelu(conv(c3, p + ".conv4"))
                c4 = name("cat"); nodes.append(h.make_node("Concat", [r, x1, x2, x3, x4], [c4], axis=1))
                x5 = conv(c4, p + ".conv5")
                r = add(mul(x5, 0.2), r)
            b = add(mul(r, 0.2), b)
        feat = add(feat, conv(b, "conv_body"))
        feat = lrelu(conv(up2(feat), "conv_up1"))
        feat = lrelu(conv(up2(feat), "conv_up2"))
        y = conv(lrelu(conv(feat, "conv_hr")), "conv_last")
    else:                                                 # SRVGGNetCompact
        idx = sorted({int(k.split(".")[1]) for k in w if k.startswith("body.")})
        y = x
        for i in idx:
            k = f"body.{i}"
            if w[k + ".weight"].ndim == 4:
                y = conv(y, k)
            else:
                o = name("prelu")
                nodes.append(h.make_node("PRelu", [y, const(w[k + ".weight"].reshape(-1, 1, 1))], [o])); y = o
        o = name("ps"); nodes.append(h.make_node("DepthToSpace", [y], [o], blocksize=4, mode="CRD")); y = o
        base = name("base"); nodes.append(h.make_node("Resize", [x, "", const([1, 1, 4, 4])], [base], mode="nearest"))
        y = add(y, base)
    nodes.append(h.make_node("Identity", [y], ["output"]))
    g = h.make_graph(nodes, "esrgan", [h.make_tensor_value_info("input", T.FLOAT, [1, 3, None, None])],
                     [h.make_tensor_value_info("output", T.FLOAT, [1, 3, None, None])], inits)
    m = h.make_model(g, opset_imports=[h.make_opsetid("", 13)], ir_version=8)
    onnx.save(m, out)


def upscale(model, src, dst, tile=192, pad=12):
    import onnxruntime as ort
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    so = ort.SessionOptions(); so.intra_op_num_threads = 4
    sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
    img = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255.0
    H, W, _ = img.shape
    out = np.zeros((H * 4, W * 4, 3), np.float32)
    padded = np.pad(img, ((pad, pad), (pad, pad), (0, 0)), mode="reflect")
    for y in range(0, H, tile):
        for x in range(0, W, tile):
            th, tw = min(tile, H - y), min(tile, W - x)
            patch = padded[y:y + th + 2 * pad, x:x + tw + 2 * pad].transpose(2, 0, 1)[None]
            r = sess.run(None, {"input": patch})[0][0].transpose(1, 2, 0)
            out[y * 4:(y + th) * 4, x * 4:(x + tw) * 4] = r[pad * 4:(pad + th) * 4, pad * 4:(pad + tw) * 4]
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(dst, quality=93)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "convert":
        build_onnx(load_pth(sys.argv[2]), sys.argv[3])
    else:
        upscale(sys.argv[2], sys.argv[3], sys.argv[4])
