#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import cairosvg

CATEGORIES = [
    ("paint", "PAINT"), ("daek", "TYRES"), ("hjulkapsel", "RIMS"),
    ("spoiler", "SPOILER"), ("udstodning", "EXHAUST"), ("vinduer", "WINDOWS"),
    ("soltag", "SUNROOF"), ("indtraek", "INTERIOR"), ("farvestribe", "STRIPES"),
    ("forrude", "WINDSCREEN"),
]

def transform(position=(0.0,0.0,0.0), scale=(1.0,1.0,1.0)):
    return {"position":list(position),"rotation":[0.0,0.0,0.0,1.0],"scale":list(scale)}

def make_label(out:Path,name:str,text:str,accent="#66d9c0",width=512,height=160):
    out.mkdir(parents=True,exist_ok=True)
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect x="3" y="3" width="{width-6}" height="{height-6}" rx="28" fill="#17191d" stroke="#3c4148" stroke-width="6"/><rect x="20" y="22" width="8" height="{height-44}" rx="4" fill="{accent}"/><text x="52" y="{height/2+14}" font-family="sans-serif" font-size="42" font-weight="700" fill="#f4f1e8">{text}</text></svg>'''
    cairosvg.svg2png(bytestring=svg.encode(),write_to=str(out/f"{name}.png"),output_width=width,output_height=height)

def ui_image(entity_id,name,parent,texture,position,scale,anchor="center",layer=120,button_label=None,disabled=False):
    c={"sindri.ui.image":{"texture":texture,"anchor":anchor,"tint":[1,1,1,1],"layer":layer}}
    if button_label is not None:c["sindri.ui.button"]={"label":button_label}
    return {"id":entity_id,"name":name,"parent":parent,"disabled":disabled,"transform_3d":transform(position,scale),"components":c}

def world_image(entity_id,name,texture,position=(0,0,-4.6),scale=(10.0,9.0,1.0),layer=-6):
    return {
        "id":entity_id,
        "name":name,
        "transform_3d":transform(position,scale),
        "components":{
            "sindri.sprite":{"texture":texture,"tint":[1,1,1,1],"layer":layer},
            "sindri.tags":{"tags":["garage-art","original-swf-art"]},
        },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--project",type=Path,default=Path("."));args=ap.parse_args()
    project=args.project.resolve();scene_path=project/"main.scene.json";scene=json.loads(scene_path.read_text(encoding="utf-8"));art=project/"assets/generated/garage-ui"
    make_label(art,"menu","MENU","#e5b45f",360,150);make_label(art,"previous","‹  PREVIOUS","#66d9c0",480,160);make_label(art,"next","NEXT  ›","#66d9c0",480,160);make_label(art,"customize","CUSTOMIZE","#e5b45f",560,150);make_label(art,"garage","MUJAFFA GARAGE","#66d9c0",620,150)
    for key,label in CATEGORIES:
        make_label(art,f"category-{key}",label,"#66d9c0",480,150);make_label(art,f"current-{key}",label,"#e5b45f",520,140)

    # The previous pass invented a generic modern garage around the original
    # BMW. Remove that scaffolding. The canonical room is SWF character 934,
    # present at the original `showroom` label on main timeline frame 730.
    prefixes=("garage-ui-mobile-category-","garage-ui-mobile-prev","garage-ui-mobile-next","garage-polish-")
    scene["entities"]=[e for e in scene["entities"] if not str(e.get("id","")).startswith(prefixes)]
    scene["entities"].append(world_image(
        "garage-polish-original-showroom",
        "Original Mujaffa Showroom",
        "assets/generated/showroom/original-showroom-background.png",
        (0.0,0.35,-4.6),
        (10.8,9.7,1.0),
        -6,
    ))

    tex=lambda n:f"assets/generated/garage-ui/{n}.png"
    scene["entities"].extend([
        ui_image("garage-polish-mobile-title","Mobile Garage Title","garage-ui-mobile",tex("garage"),(-0.04,0.88,0),(0.58,0.105,1),"top",125),
        ui_image("garage-polish-mobile-menu","Mobile Garage Menu","garage-ui-mobile",tex("menu"),(0.72,0.88,0),(0.22,0.105,1),"top",126,"Menu"),
        {"id":"garage-polish-mobile-sheet","name":"Mobile Customization Sheet","parent":"garage-ui-mobile","transform_3d":transform((0,-0.76,0),(0.96,0.40,1)),"components":{"sindri.ui.shape":{"kind":"rect","fill":[0.055,0.06,0.07,0.97],"anchor":"bottom","layer":116}}},
        ui_image("garage-ui-mobile-prev","Mobile Previous Part","garage-ui-mobile",tex("previous"),(-0.36,-0.86,0),(0.40,0.115,1),"bottom",126,"Previous"),
        ui_image("garage-ui-mobile-next","Mobile Next Part","garage-ui-mobile",tex("next"),(0.36,-0.86,0),(0.40,0.115,1),"bottom",126,"Next"),
        ui_image("garage-polish-mobile-categories","Mobile Categories Button","garage-ui-mobile",tex("customize"),(0,-0.70,0),(0.52,0.10,1),"bottom",126,"Categories"),
        {"id":"garage-polish-mobile-drawer","name":"Mobile Category Drawer","parent":"garage-ui-mobile","disabled":True,"transform_3d":transform((0,-0.18,0),(0.94,1.30,1)),"components":{"sindri.ui.shape":{"kind":"rect","fill":[0.045,0.05,0.06,0.985],"anchor":"bottom","layer":130}}},])
    for i,(key,label) in enumerate(CATEGORIES):
        scene["entities"].append(ui_image(f"garage-polish-current-{key}",f"Mobile Current {label}","garage-ui-mobile",tex(f"current-{key}"),(0,-0.56,0),(0.44,0.085,1),"bottom",127,disabled=i!=0))
    for i,(key,label) in enumerate(CATEGORIES):
        x=-0.28 if i%2==0 else 0.28;y=-0.12-(i//2)*0.20
        scene["entities"].append(ui_image(f"garage-ui-mobile-category-{key}",f"Mobile Category {label}","garage-polish-mobile-drawer",tex(f"category-{key}"),(x,y,0),(0.43,0.145,1),"bottom",134,label))
    scene["entities"].append({"id":"garage-polish-controller","name":"Garage Polish Controller","transform_3d":transform(),"components":{"sindri.script":{"source":"scripts/garage_polish.decay","script":"GaragePolish","properties":{},"enabled":True}}})
    scene_path.write_text(json.dumps(scene,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("polished garage using original SWF showroom artwork and responsive controls")
if __name__=="__main__":main()
