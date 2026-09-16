#!/usr/bin/env python3
"""Extract original Mujaffa opening/title timeline evidence from the SWF."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from swf_inventory import BitReader, SwfError, iter_tags, parse_header

OPENING_LABELS = {"start", "velkommen", "speakDone", "gotoInstruktioner", "gotoGame", "initGame"}


def _cstring(payload: bytes) -> str:
    return payload.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def _u16(payload: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<H", payload, offset)[0]


def _matrix(payload: bytes, offset: int) -> tuple[dict[str, float], int]:
    bits = BitReader(payload, offset)
    sx = sy = 1.0
    r0 = r1 = 0.0
    if bits.read_unsigned(1):
        n = bits.read_unsigned(5)
        sx, sy = bits.read_signed(n) / 65536.0, bits.read_signed(n) / 65536.0
    if bits.read_unsigned(1):
        n = bits.read_unsigned(5)
        r0, r1 = bits.read_signed(n) / 65536.0, bits.read_signed(n) / 65536.0
    n = bits.read_unsigned(5)
    tx = bits.read_signed(n) / 20.0 if n else 0.0
    ty = bits.read_signed(n) / 20.0 if n else 0.0
    return {"scale_x":sx,"scale_y":sy,"rotate_skew_0":r0,"rotate_skew_1":r1,"translate_x":tx,"translate_y":ty}, bits.byte_offset


def _place_object(tag_code: int, payload: bytes) -> dict[str, object]:
    if tag_code == 4:
        if len(payload) < 4: raise SwfError("truncated PlaceObject")
        cid, depth = struct.unpack_from("<HH", payload)
        matrix, _ = _matrix(payload, 4)
        return {"character_id":cid,"depth":depth,"move":False,"matrix":matrix}
    if tag_code != 26: raise SwfError(f"unsupported placement tag {tag_code}")
    if len(payload) < 3: raise SwfError("truncated PlaceObject2")
    flags, offset = payload[0], 3
    entry: dict[str, object] = {"depth":_u16(payload,1),"move":bool(flags & 1)}
    if flags & 2:
        if offset + 2 > len(payload): raise SwfError("truncated PlaceObject2 character id")
        entry["character_id"] = _u16(payload, offset); offset += 2
    if flags & 4:
        entry["matrix"], offset = _matrix(payload, offset)
    # ColorTransformWithAlpha is variable-length bit data. Stop here when present;
    # fields after it cannot be located safely until that decoder is implemented.
    if flags & 8:
        entry["has_color_transform"] = True
        return entry
    if flags & 16:
        if offset + 2 > len(payload): raise SwfError("truncated PlaceObject2 ratio")
        entry["ratio"] = _u16(payload, offset); offset += 2
    if flags & 32:
        end = payload.find(b"\0", offset)
        if end < 0: raise SwfError("unterminated PlaceObject2 name")
        entry["name"] = payload[offset:end].decode("utf-8", errors="replace"); offset = end + 1
    if flags & 64:
        if offset + 2 > len(payload): raise SwfError("truncated PlaceObject2 clip depth")
        entry["clip_depth"] = _u16(payload, offset)
    if flags & 128:
        entry["has_clip_actions"] = True
    return entry


def _named_characters(data: bytes, tags_offset: int) -> list[dict[str, object]]:
    found: dict[tuple[int,str],set[str]] = {}
    for tag in iter_tags(data,tags_offset):
        if tag.code not in {56,76} or len(tag.payload)<2: continue
        count, offset = _u16(tag.payload), 2
        for _ in range(count):
            if offset+2>len(tag.payload): break
            cid=_u16(tag.payload,offset); offset+=2
            end=tag.payload.find(b"\0",offset)
            if end<0: break
            name=tag.payload[offset:end].decode("utf-8",errors="replace"); offset=end+1
            found.setdefault((cid,name),set()).add("SymbolClass" if tag.code==76 else "ExportAssets")
    return [{"character_id":cid,"name":name,"sources":sorted(src)} for (cid,name),src in sorted(found.items())]


def _tag_counts(data: bytes, tags_offset: int) -> dict[str,int]:
    relevant={2:"DefineShape",22:"DefineShape2",32:"DefineShape3",83:"DefineShape4",7:"DefineButton",34:"DefineButton2",11:"DefineText",33:"DefineText2",37:"DefineEditText",39:"DefineSprite",4:"PlaceObject",26:"PlaceObject2",70:"PlaceObject3",5:"RemoveObject",28:"RemoveObject2"}
    counts={name:0 for name in relevant.values()}
    for tag in iter_tags(data,tags_offset):
        if tag.code in relevant: counts[relevant[tag.code]]+=1
    return {k:v for k,v in counts.items() if v}


def _opening_display_trace(data: bytes,tags_offset:int,end_frame:int)->list[dict[str,object]]:
    frame=1; trace=[]
    for tag in iter_tags(data,tags_offset):
        if frame>end_frame: break
        if tag.code==1: frame+=1; continue
        if tag.code in {4,26}:
            entry={"frame":frame,"tag":"PlaceObject" if tag.code==4 else "PlaceObject2"}; entry.update(_place_object(tag.code,tag.payload)); trace.append(entry)
        elif tag.code==5 and len(tag.payload)>=4:
            cid,depth=struct.unpack_from("<HH",tag.payload); trace.append({"frame":frame,"tag":"RemoveObject","character_id":cid,"depth":depth})
        elif tag.code==28 and len(tag.payload)>=2: trace.append({"frame":frame,"tag":"RemoveObject2","depth":_u16(tag.payload)})
        elif tag.code==43: trace.append({"frame":frame,"tag":"FrameLabel","label":_cstring(tag.payload)})
    return trace


def _display_snapshots(trace:list[dict[str,object]], label_frames:dict[int,str])->list[dict[str,object]]:
    display: dict[int,dict[str,object]]={}; snapshots=[]; current=1
    def capture(frame:int)->None:
        label=label_frames.get(frame)
        if label:
            snapshots.append({"frame":frame,"label":label,"display_list":[display[d] for d in sorted(display)]})
    for event in trace:
        frame=int(event["frame"])
        if frame!=current:
            capture(current); current=frame
        tag=str(event["tag"])
        if tag.startswith("PlaceObject"):
            depth=int(event["depth"]); prior=display.get(depth,{}) if event.get("move") else {}
            placed={**prior,**{k:v for k,v in event.items() if k not in {"frame","tag","move"}}}; display[depth]=placed
        elif tag.startswith("RemoveObject"): display.pop(int(event["depth"]),None)
    capture(current)
    # Some label frames have no display mutation. Replay/capture them directly.
    captured={int(s["frame"]) for s in snapshots}
    for frame,label in sorted(label_frames.items()):
        if frame not in captured:
            # Rebuild state through this frame for correctness over sparse events.
            state:dict[int,dict[str,object]]={}
            for event in trace:
                if int(event["frame"])>frame: break
                tag=str(event["tag"])
                if tag.startswith("PlaceObject"):
                    depth=int(event["depth"]); prior=state.get(depth,{}) if event.get("move") else {}
                    state[depth]={**prior,**{k:v for k,v in event.items() if k not in {"frame","tag","move"}}}
                elif tag.startswith("RemoveObject"): state.pop(int(event["depth"]),None)
            snapshots.append({"frame":frame,"label":label,"display_list":[state[d] for d in sorted(state)]})
    return sorted(snapshots,key=lambda s:int(s["frame"]))


def extract(path:Path)->dict[str,object]:
    data,header=parse_header(path.read_bytes()); frame=0; labels=[]
    for tag in iter_tags(data,header.tags_offset):
        if tag.code==1: frame+=1
        elif tag.code==43:
            label=_cstring(tag.payload)
            if label in OPENING_LABELS: labels.append({"label":label,"frame":frame+1})
    missing=sorted(OPENING_LABELS-{e["label"] for e in labels})
    if missing: raise ValueError(f"opening labels missing from SWF: {', '.join(missing)}")
    labels.sort(key=lambda e:int(e["frame"])); end=max(int(e["frame"]) for e in labels)
    trace=_opening_display_trace(data,header.tags_offset,end)
    label_frames={int(e["frame"]):str(e["label"]) for e in labels}
    return {"schema_version":6,"source":path.name,"stage":[header.width,header.height],"frame_rate":header.fps,"opening_labels":labels,"named_characters":_named_characters(data,header.tags_offset),"title_relevant_tag_counts":_tag_counts(data,header.tags_offset),"opening_display_trace":trace,"opening_display_snapshots":_display_snapshots(trace,label_frames),"notes":["Placement matrices use SWF coordinates converted from twips to pixels.","Display snapshots resolve depth replacements and move updates at opening labels.","Color transforms are flagged but not decoded yet; fields after such transforms are intentionally not guessed.","This file deliberately contains no workshop economy data."]}


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("swf",type=Path); p.add_argument("--out",type=Path); a=p.parse_args(); encoded=json.dumps(extract(a.swf),indent=2,ensure_ascii=False)+"\n"
    if a.out: a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(encoded,encoding="utf-8")
    else: print(encoded,end="")
    return 0
if __name__=="__main__": raise SystemExit(main())
