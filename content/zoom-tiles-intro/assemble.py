"""Assemble a local Final Cut edit package from the rendered scenes."""
import array
import json
import math
import subprocess
import tempfile
import textwrap
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
OUTPUT = SOURCE.parents[1] / "artifacts" / "zoom-tiles-intro"
RATE = 48_000
STORY = json.loads((SOURCE / "story.json").read_text())
DURATION = sum(scene["duration"] for scene in STORY)
TITLE = "What are zoom tiles?"


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
                   check=True, cwd=OUTPUT)


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def cues():
    offset = 0
    for scene in STORY:
        for start, end, text in scene["lines"]:
            yield offset + start, offset + end, text
        offset += scene["duration"]


def write_audio(name, samples):
    with wave.open(str(OUTPUT / name), "wb") as track:
        track.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        track.writeframes(samples.tobytes())


def record_scratch():
    voice = array.array("h", [0]) * (DURATION * RATE)
    with tempfile.TemporaryDirectory(prefix="ztiles-voice-") as temporary:
        source = Path(temporary) / "read.aiff"
        segment = Path(temporary) / "line.wav"
        for start, end, text in cues():
            spoken = text.replace("zTiles", "zee tiles").replace("Middle-earth", "Middle Earth")
            subprocess.run(["say", "-v", "Samantha", "-r", "177", "-o", str(source), spoken], check=True)
            ffmpeg("-i", source, "-ar", RATE, "-ac", 1, "-c:a", "pcm_s16le", segment)
            with wave.open(str(segment), "rb") as input_file:
                available = (end - start) - .08
                speed = input_file.getnframes() / RATE / available
            if speed > 1:
                ffmpeg("-i", source, "-af", f"atempo={speed:.6f}", "-ar", RATE, "-ac", 1,
                       "-c:a", "pcm_s16le", segment)
            with wave.open(str(segment), "rb") as input_file:
                audio = array.array("h")
                audio.frombytes(input_file.readframes(input_file.getnframes()))
            sample = round(start * RATE)
            limit = round(end * RATE) - sample
            if len(audio) > limit:
                raise ValueError(f"Narration exceeds cue at {start}s: {text}")
            voice[sample:sample + len(audio)] = audio
    write_audio("scratch-narration.wav", voice)


def sound_cues():
    sound = array.array("h", [0]) * (DURATION * RATE)
    hits = [
        (0.15, 196, .55), (3.8, 280, .25), (7.2, 350, .26),
        (11.6, 392, .24), (16.75, 494, .26), (19.6, 587, .32),
        (24, 196, .52), (27, 287, .26), (31, 370, .28),
        (39.2, 294, .26), (43.3, 392, .26), (45, 494, .3),
        (53.2, 294, .24), (57.25, 392, .22), (60.15, 523, .38),
        (64.2, 196, .5), (72.35, 294, .48), (72.48, 392, .6), (72.64, 523, .7),
    ]
    for start, frequency, duration in hits:
        offset = round(start * RATE)
        for index in range(round(duration * RATE)):
            time = index / RATE
            envelope = min(1, time / .012) * (1 - time / duration) ** 3
            phase = 2 * math.pi * frequency * time
            sound[offset + index] += int(1750 * envelope * (math.sin(phase) + .25 * math.sin(2 * phase)))
    write_audio("sound-cues.wav", sound)


def write_script_and_captions():
    chunks = [
        "# What are zoom tiles? — Recording script",
        "",
        "76 seconds at 30 fps. Cue times match the silent edit and scratch narration.",
        "",
        "Use the first four seconds for the OBS host intro and 01:10 to 01:16 for the close. "
        "For an overlay in either shot, keep the character inside x=85–540 and y=595–950 "
        "in the 1920 × 1080 frame. Keep the real product demo full frame.",
        "",
    ]
    offset = 0
    for scene in STORY:
        end = offset + scene["duration"]
        start_label = timestamp(offset)[3:8]
        end_label = timestamp(end)[3:8]
        chunks += [f"## {start_label}–{end_label} · {scene['title']}", "", scene["marker"], ""]
        for start, _, text in scene["lines"]:
            label = timestamp(offset + start)[3:12].replace(",", ".")
            chunks.append(f"- **{label}** {text}")
        chunks.append("")
        offset = end
    (OUTPUT / "recording-script.md").write_text("\n".join(chunks), encoding="utf-8")
    captions = []
    for index, (start, end, text) in enumerate(cues(), 1):
        wrapped = "\n".join(textwrap.wrap(text, width=42, break_long_words=False))
        captions.append(f"{index}\n{timestamp(start)} --> {timestamp(end)}\n{wrapped}\n")
    (OUTPUT / "captions.srt").write_text("\n".join(captions), encoding="utf-8")


def write_fcpxml():
    root = ET.Element("fcpxml", version="1.10")
    resources = ET.SubElement(root, "resources")
    ET.SubElement(resources, "format", id="r1", name="FFVideoFormat1080p30",
                  frameDuration="1/30s", width="1920", height="1080", colorSpace="1-1-1 (Rec. 709)")
    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", name="zTiles Explainers")
    project = ET.SubElement(event, "project", name=TITLE)
    sequence = ET.SubElement(project, "sequence", format="r1", duration=f"{DURATION}s",
                             tcStart="0s", tcFormat="NDF")
    spine = ET.SubElement(sequence, "spine")
    offset = 0
    for index, scene in enumerate(STORY, 2):
        name = scene["title"]
        duration = f"{scene['duration']}s"
        asset = ET.SubElement(resources, "asset", id=f"r{index}", name=name, start="0s",
                              duration=duration, hasVideo="1", format="r1")
        path = OUTPUT / "clips" / f"{scene['slug']}.mp4"
        ET.SubElement(asset, "media-rep", kind="original-media", src=path.as_uri())
        clip = ET.SubElement(spine, "asset-clip", ref=f"r{index}", name=name, offset=f"{offset}s",
                             start="0s", duration=duration, format="r1")
        ET.SubElement(clip, "marker", start="0s", duration="1/30s", value=scene["marker"])
        if scene["slug"] == "06-outro":
            ET.SubElement(clip, "marker", start="6s", duration="1/30s", value="OBS closing overlay begins")
        offset += scene["duration"]
    ET.indent(root)
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + ET.tostring(root, encoding="unicode")
    (OUTPUT / "What are zoom tiles.fcpxml").write_text(xml + "\n", encoding="utf-8")


def main():
    write_script_and_captions()
    record_scratch()
    sound_cues()
    concat = OUTPUT / "clip-order.txt"
    concat.write_text("".join(f"file clips/{scene['slug']}.mp4\n" for scene in STORY), encoding="utf-8")
    ffmpeg("-f", "concat", "-safe", "1", "-i", concat, "-map", "0:v", "-c", "copy",
           "-movflags", "+faststart", "master-silent.mp4")
    ffmpeg("-i", "master-silent.mp4", "-i", "scratch-narration.wav", "-i", "sound-cues.wav",
           "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.90:latency=1[mix]",
           "-map", "0:v", "-map", "[mix]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
           "-movflags", "+faststart", "scratch-preview.mp4")
    ffmpeg("-ss", "8.5", "-i", "master-silent.mp4", "-frames:v", "1", "-q:v", "2", "title-poster.jpg")
    write_fcpxml()


if __name__ == "__main__":
    main()
