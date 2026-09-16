#!/usr/bin/env python3
"""Add functional category and original-style LAKKERING controls."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import cairosvg
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools.workshop_catalog import CATEGORIES

def transform(position,scale): return {"position":list(position),"rotation":[0.,0.,0.,1.],"scale":list(scale)}
def stage_x(px): return px/250.-1.
def stage_y(px): return 1.-px/250.
def stage_size(px): return px/250.
def burst():
    pts="11,0 14,5 20,3 19,9 25,11 20,15 22,21 15,19 11,24 8,19 2,21 4,15 0,11 5,8 3,3 9,5"
    return f'<g transform="translate(2 0) scale(.72)"><polygon points="{pts}" fill="#ffd719" stroke="#111" stroke-width="1.4"/><text x="11.5" y="14" text-anchor="middle" font-size="8" font-weight="700" font-style="italic">ny</text></g>'
def render(out,name,w,h,body):
    out.mkdir(parents=True,exist_ok=True); svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'
    cairosvg.svg2png(bytestring=svg.encode(),write_to=str(out/name),output_width=w*4,output_height=h*4)
def make_button(out,entry):
    badge=burst() if entry['label'] in ('BÅT-HORN','BMW CAM') else ''
    render(out,f"category-{entry['id']}.png",145,24,f'{badge}<rect x="27" y="3" width="102" height="16" rx="3" fill="#2ca2c8" stroke="#111827" stroke-width="2"/><text x="78" y="14.5" text-anchor="middle" font-family="Arial" font-size="10.5" font-weight="700" fill="#15151b">{entry["label"]}</text>')
def button(entry,index):
    return {"id":f"workshop-category-{entry['id']}","name":f"Workshop Category {entry['label']}","parent":"garage-ui-desktop","transform_3d":transform((stage_x(72.5),stage_y(137+25*index),0),(stage_size(145),stage_size(24),1)),"components":{"sindri.ui.image":{"texture":f"assets/generated/workshop-ui/category-{entry['id']}.png","tint":[1,1,1,1],"anchor":"center","layer":240},"sindri.ui.button":{"label":entry['label']}}}
def make_panel(out,entry): render(out,f"panel-{entry['id']}.png",500,500,f'<rect x="153" y="351" width="343" height="111" rx="12" fill="#129bc4" stroke="#0b103b" stroke-width="4"/><text x="176" y="380" font-family="Arial" font-size="18" font-weight="700">{entry["label"]}</text>')
def panel_entity(entry): return {"id":f"workshop-panel-{entry['id']}","name":f"Workshop Panel {entry['label']}","disabled":True,"transform_3d":transform((0,0,-4),(10,10,1)),"components":{"sindri.sprite":{"texture":f"assets/generated/workshop-ui/panel-{entry['id']}.png","tint":[1,1,1,1],"layer":230}}}
def make_paint_controls(out):
    render(out,'paint-change.png',56,38,'<rect x="2" y="2" width="52" height="34" rx="3" fill="#2a9ac3" stroke="#6b3150" stroke-width="2"/><text x="28" y="26" text-anchor="middle" font-family="Arial" font-size="18" font-weight="700" fill="#ec3345">skift</text>')
    stripe=[('none','#32a8c8','#e33435'),('white','#fff','#2486bf'),('green','#5fd52e','#258cc1'),('black','#111','#217ead'),('pink','#f66ca9','#267eac')]
    for name,fill,line in stripe: render(out,f'stripe-{name}.png',34,26,f'<rect x="2" y="2" width="30" height="22" rx="5" fill="{fill}" stroke="#111" stroke-width="2"/><path d="M4 6 l26 16" stroke="{line}" stroke-width="4"/>')
    render(out,'rgb-mixer.png',343,111,'<rect x="2" y="2" width="339" height="107" rx="12" fill="#129bc4" stroke="#0b103b" stroke-width="4"/><rect x="28" y="11" width="12" height="9" fill="#f22" stroke="#111"/><rect x="56" y="11" width="12" height="9" fill="#3d3" stroke="#111"/><rect x="84" y="11" width="12" height="9" fill="#23e" stroke="#111"/><rect x="29" y="25" width="8" height="72" fill="#dff" stroke="#125"/><rect x="57" y="25" width="8" height="72" fill="#dff" stroke="#125"/><rect x="85" y="25" width="8" height="72" fill="#dff" stroke="#125"/><text x="120" y="49" font-family="Arial" font-size="12" font-weight="700">Velg farge ved å dra i</text><text x="120" y="66" font-family="Arial" font-size="12" font-weight="700">fargeskalaene, og trykk “OK”!</text>')
    for n in ('red','green','blue'): render(out,f'rgb-{n}.png',18,78,'<rect x="5" y="2" width="8" height="74" rx="3" fill="#dff" stroke="#125"/>')
    for n,c in [('red','#ef3038'),('green','#38cf42'),('blue','#254fe0')]: render(out,f'rgb-{n}-marker.png',16,7,f'<rect x="1" y="1" width="14" height="5" rx="2" fill="{c}" stroke="#10254f" stroke-width="2"/>')
    render(out,'rgb-ok.png',54,38,'<rect x="2" y="2" width="50" height="34" rx="4" fill="#2aa6ca" stroke="#17305f" stroke-width="2"/><text x="27" y="27" text-anchor="middle" font-family="Arial" font-size="22" font-weight="700" fill="#ef3345">OK!</text>')
def control(eid,name,texture,x,y,w,h,layer=250):
    return {"id":eid,"name":name,"parent":"garage-ui-desktop","transform_3d":transform((stage_x(x),stage_y(y),0),(stage_size(w),stage_size(h),1)),"components":{"sindri.ui.image":{"texture":f"assets/generated/workshop-ui/{texture}","tint":[1,1,1,1],"anchor":"center","layer":layer},"sindri.ui.button":{"label":name}}}
def image_control(eid,name,texture,x,y,w,h,layer=252):
    entity=control(eid,name,texture,x,y,w,h,layer); entity["components"].pop("sindri.ui.button"); return entity
def slider(eid,name,texture,x,y,w,h,value,layer=251):
    entity=image_control(eid,name,texture,x,y,w,h,layer)
    entity["components"]["sindri.ui.slider"]={"label":name,"orientation":"vertical","min":0.0,"max":255.0,"step":1.0,"value":value,"disabled":False}
    return entity
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project',type=Path,default=Path('.')); args=ap.parse_args(); p=args.project/'main.scene.json'; scene=json.loads(p.read_text())
    scene['entities']=[e for e in scene['entities'] if not any(str(e.get('id','')).startswith(s) for s in ('workshop-category-','workshop-panel-','workshop-paint-','workshop-stripe-','workshop-rgb-')) and e.get('id') not in {'workshop-state','workshop-category-controller'}]
    out=args.project/'assets/generated/workshop-ui'
    for entry in CATEGORIES: make_button(out,entry)
    for entry in CATEGORIES[1:]: make_panel(out,entry); scene['entities'].append(panel_entity(entry))
    make_paint_controls(out); scene['entities'].extend(button(e,i) for i,e in enumerate(CATEGORIES))
    scene['entities'].extend([
      control('workshop-paint-change','Workshop Paint Change','paint-change.png',205,433,56,38),
      control('workshop-stripe-none','Workshop Stripe None','stripe-none.png',359,400,34,26),control('workshop-stripe-white','Workshop Stripe White','stripe-white.png',397,400,34,26),control('workshop-stripe-green','Workshop Stripe Green','stripe-green.png',359,430,34,26),control('workshop-stripe-black','Workshop Stripe Black','stripe-black.png',397,430,34,26),control('workshop-stripe-pink','Workshop Stripe Pink','stripe-pink.png',435,430,34,26),
      image_control('workshop-rgb-mixer','Workshop RGB Mixer','rgb-mixer.png',324.5,406.5,343,111,249),
      slider('workshop-rgb-red','Workshop RGB Red','rgb-red.png',185,407,18,78,32.0),slider('workshop-rgb-green','Workshop RGB Green','rgb-green.png',213,407,18,78,64.0),slider('workshop-rgb-blue','Workshop RGB Blue','rgb-blue.png',241,407,18,78,184.0),
      image_control('workshop-rgb-red-marker','Workshop RGB Red Marker','rgb-red-marker.png',185,436,16,7),image_control('workshop-rgb-green-marker','Workshop RGB Green Marker','rgb-green-marker.png',213,426,16,7),image_control('workshop-rgb-blue-marker','Workshop RGB Blue Marker','rgb-blue-marker.png',241,390,16,7),
      control('workshop-rgb-ok','Workshop RGB OK','rgb-ok.png',459,431,54,38,253)])
    scene['entities'] += [
      {"id":"workshop-state","name":"Workshop State","transform_3d":transform((0,0,0),(1,1,1)),"components":{"sindri.script":{"source":"scripts/workshop_state.decay","script":"WorkshopState","properties":{},"enabled":True}}},
      {"id":"workshop-category-controller","name":"Workshop Category Controller","transform_3d":transform((0,0,0),(1,1,1)),"components":{"sindri.script":{"source":"scripts/workshop_category_controller.decay","script":"WorkshopCategoryController","properties":{},"enabled":True}}},
      {"id":"workshop-paint-controller","name":"Workshop Paint Controller","transform_3d":transform((0,0,0),(1,1,1)),"components":{"sindri.script":{"source":"scripts/workshop_paint_controller.decay","script":"WorkshopPaintController","properties":{},"enabled":True}}}]
    p.write_text(json.dumps(scene,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__': main()
