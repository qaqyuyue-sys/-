"""ffmpeg rendering: shot conform → dissolve edit → audio mix → card composite."""
import json
from pathlib import Path

from .common import duration, find_footage, log, run


def _srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_sidecars(tl, out_dir):
    out_dir = Path(out_dir)
    srt, n = [], 0
    for c in tl.cards:
        if c.style == "line":
            n += 1
            srt += [str(n), f"{_srt_time(c.voice_in)} --> {_srt_time(c.voice_out)}", c.text, ""]
    (out_dir / "subtitles.srt").write_text("\n".join(srt), encoding="utf-8")
    (out_dir / "timeline.json").write_text(json.dumps({
        "duration": tl.duration,
        "shots": [s.__dict__ for s in tl.shots],
        "cards": [c.__dict__ for c in tl.cards],
        "voices": [v.__dict__ for v in tl.voices],
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def conform_shots(tl, shots_meta, footage_dir, video, out_dir):
    """Cut each shot to length, scale-to-fill 16:9, grade. Short clips are slowed."""
    W, H, fps, T = video["width"], video["height"], video["fps"], video["transition"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    missing = [s.id for s in tl.shots if not find_footage(footage_dir, s.id)]
    if missing:
        raise SystemExit("缺少镜头素材（放到 footage/<id>.mp4）：\n  " + "\n  ".join(missing))

    clips = []
    for j, s in enumerate(tl.shots):
        need = s.length + (T if j < len(tl.shots) - 1 else 0)
        src = find_footage(footage_dir, s.id)
        src_dur = duration(src)
        meta = shots_meta.get(s.id, {}) or {}
        if "start" in meta:
            start = min(float(meta["start"]), max(0.0, src_dur - 0.5))
        else:
            start = max(0.0, (src_dur - need) / 2)
        avail = src_dur - start
        slow = max(1.0, need / avail)
        vf = []
        if slow > 1.0:
            log(f"{s.id}: 素材 {avail:.1f}s 不足 {need:.1f}s，放慢 {min(slow, 2.5):.2f}x")
            vf.append(f"setpts={min(slow, 2.5):.4f}*PTS")
        vf += [f"fps={fps}",
               f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos",
               f"crop={W}:{H}", "setsar=1", video.get("grade") or "null",
               f"tpad=stop_mode=clone:stop_duration={need:.3f}", "format=yuv420p"]
        out = out_dir / f"{j:02d}_{s.id}.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-i", src, "-an",
             "-vf", ",".join(vf), "-t", f"{need:.3f}",
             "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-g", str(fps), out])
        clips.append(out)
    return clips


def edit_base(tl, clips, video, out):
    fps, T = video["fps"], video["transition"]
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for c in clips:
        cmd += ["-i", c]
    graph, prev, offset = [], "[0:v]", 0.0
    for j in range(1, len(clips)):
        offset += tl.shots[j - 1].length
        graph.append(f"{prev}[{j}:v]xfade=transition=fade:duration={T}:offset={offset:.3f}[x{j}]")
        prev = f"[x{j}]"
    end = tl.duration
    graph.append(f"{prev}fade=t=in:st=0:d=1.0,fade=t=out:st={end - 1.2:.3f}:d=1.2,"
                 f"trim=duration={end:.3f},format=yuv420p[v]")
    cmd += ["-filter_complex", ";".join(graph), "-map", "[v]", "-r", str(fps),
            "-c:v", "libx264", "-preset", "medium", "-crf", "14", out]
    run(cmd)


def mix_audio(tl, music, out, root):
    end = tl.duration
    cmd = ["ffmpeg", "-y", "-v", "error"]
    graph, labels = [], []
    for i, v in enumerate(tl.voices):
        cmd += ["-i", v.file]
        ms = int(round(v.start * 1000))
        graph.append(f"[{i}:a]adelay={ms}:all=1[v{i}]")
        labels.append(f"[v{i}]")
    graph.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,"
                 f"apad=whole_dur={end:.3f}[vox]")
    bgm = Path(root) / music["file"] if music and music.get("file") else None
    if bgm and bgm.exists():
        k = len(tl.voices)
        cmd += ["-stream_loop", "-1", "-i", bgm]
        graph.append(f"[{k}:a]atrim=duration={end:.3f},aformat=channel_layouts=stereo,"
                     f"volume={music.get('volume', 0.3)}[bgm]")
        if music.get("duck", True):
            graph.append("[vox]asplit[vox][key]")
            graph.append("[bgm][key]sidechaincompress=threshold=0.03:ratio=6:"
                         "attack=80:release=600[bgm]")
        graph.append("[vox][bgm]amix=inputs=2:normalize=0[mix]")
    else:
        log("未找到背景音乐，仅输出配音")
        graph.append("[vox]anull[mix]")
    graph.append(f"[mix]afade=t=in:d=0.8,afade=t=out:st={end - 1.5:.3f}:d=1.5,"
                 f"atrim=duration={end:.3f},loudnorm=I=-16:TP=-1.5:LRA=11[a]")
    cmd += ["-filter_complex", ";".join(graph), "-map", "[a]", "-ar", "48000", out]
    run(cmd)


def composite(base, mask, overlay, audio, out):
    graph = (
        "[0:v]split[a][b];"
        "[b]gblur=sigma=26,eq=brightness=-0.03:saturation=1.2[bl];"
        "[bl][1:v]alphamerge[glass];"
        "[a][glass]overlay=format=auto[g];"
        "[g][2:v]overlay=format=auto,format=yuv420p[v]"
    )
    run(["ffmpeg", "-y", "-v", "error", "-i", base, "-i", mask, "-i", overlay, "-i", audio,
         "-filter_complex", graph, "-map", "[v]", "-map", "3:a",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", out])
