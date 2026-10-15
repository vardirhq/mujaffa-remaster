# KJØR!: the drive, the route map and the end screens

`tools/install_drive.py` cuts the art from `mujaffa_3juni_2003.swf` and
`scripts/trip_controller.decay` and `scripts/drive_controller.decay` play it.
This page is the decoded original they follow, with what the remaster does
differently up front.

Source: `mujaffa_3juni_2003.swf` (SWF 6, 500×500, **12 fps**, 811 frames). All
frame numbers are **1-based main-timeline frames** (SWF `GotoFrame(n)` is
0-based; it is converted everywhere below). AS1 variable names are
case-insensitive. **[D]** = decoded directly from action bytes or tag data;
**[I]** = inferred (Flash Player semantics, rendering, naming, or absence of
code). Pseudo-code: `a add b` is AS1 string concat, `../:x` a parent variable,
`call("lbl")` runs that frame's actions without moving the playhead.

## What the remaster does

**One stage, several views.** The trip lives in `main.scene.json` beside the
workshop rather than in its own scene, because the workshop's state is held by
its controllers and a scene change would reset them. `workshop.view` on the
board says what covers the stage: 0 workshop, 1 showroom, 2 the frame-740
dialog, 3 the map, 4 the drive, 5 game over, 6 status.

**Board keys.** `trip.level`, `trip.district` (1 GRØNLAND, 2 GRUNERLØKKA,
3 SINSEN, 4 TVEITA, 5 RÅDHUSPLASSEN, 6 BISLETT, 7 FROGNER, 8 HOLMENKOLLEN),
`trip.energi` (damage carried between drives), `trip.earned` and `trip.spent`
(running totals the workshop adds to its money), `game.cool` (RESPEKT / street
cred), and `drive.ticket` / `drive.result` / `drive.result_ticket`, the
handshake that starts a drive and reports it finished (1) or crashed (2).

**Fixed** (as shipped, level 3 cannot be finished; see section 4):

- `bane3_grønland` is dispatched to frame 448, not back to 368.
- Holmenkollen's button at 458 sets HOLMENKOLLEN and goes to 463.
- Sinsen's button at 463 goes to 469, not level 2's 424.
- The garage repair when the money does not cover it: v1.6 zeroes `penge` and
  then sets `energi` to the whole bill (twenty times the damage). Here the
  money left pays what it can and the rest stays as damage.

**Kept as in 2003:**

- Bislett's traffic is the Grünerløkka cars (`dyr` spells its label BISLET).
- Grünerløkka's cars dent the BMW but never end the game (`eval("../../:slut")`
  names nothing).
- The traffic test only counts the top-left and bottom-right corners; the
  cousin and the girl are tested as points.
- Level 3 has the sparsest spawn table.
- `energi == 1` after a drive gets no garage dialog.

**Choices where the original leaves it open:**

- Key repeat: the arrow keys move the car one step per 1/12 s tick while held,
  in place of the OS key-repeat the original's `keyPress` events relied on.
- Phones: one finger steers and taps act, so nothing sits under the game.
  A held or dragged finger presses the same arrow steps towards a point 70 px
  above it, and the opposite arrow to brake when the BMW gets there. A tap
  (under 0.25 s, moving under 12 px) on the cousin greets him (Z), on the girl
  picks her up (X), and two taps within 0.35 s elsewhere are a burn-out (B).
  The horn (H) is sound only and waits for the sounds to be cut.
- The garage's `repair_car` dialogs (886) are cut from the SWF and wait for an
  answer: "respect" gives +15 on JA!, and its cross leaves `repairok` set so it
  asks again next time the workshop opens; "open" shows the bill as digit
  pictures from the embedded Arial Bold, and NEI! drives on with the damage.
- "Bhaias Verksted" (755-793) plays after START, after every finished drive
  and after a level's NESTE SIDE, as `workshop.view` 7. Its BMW (946) holds the
  same `karosseri` as the garage's `bil` (875), so the fitted garage car itself
  drives in, moved by the `Trip Arrival` sequence through 946's placements.
- JA on the KJØR! dialog goes straight to the map; the BMW's drive-away
  animation (sprite 875 frames 2-50) is not cut yet.
- NESTE SIDE on the status screen goes back to the title, where 659 opened the
  highscore list.

**Not cut yet:** sounds and the horn, the burnout smoke, the pedestrian splat
blood, the moped crash, the spoiler colour, BMW-CAM, the highscore list and
PRINT BILEN.

The art is cut with masks ignored, so the HUD's ENERGI cover (1214), which
slides under a mask in the original, is stretched over the bar instead.

## 1. Button 925 (KJØR!) and the sibling navigation buttons

Button 925 is placed only at frame 722 (`køb`, workshop), depth 413, at (484.25, 482.75) scale 0.944 [D].

```as
// button925, condition OverDownToOverUp (release)                       [D]
camefrom = "køb";
gotoFrame(739);          // = gotoAndStop(740) "kør"
```

Siblings in the bottom nav bar (all release-only) [D]:

| button | placed | action |
|---|---|---|
| 925 KJØR! | 722 @ x 484 | `camefrom="køb"; gotoAndStop(740)` |
| 926 (showroom tab) | 722 @ x 371 | `call("makeDescription"); gotoAndStop(730)` |
| 939 (showroom tab) | 740 @ x 371 | `call("makeDescription"); gotoAndStop(730)` |
| 936 (verksted tab) | 730, 740 @ x 258 | `gotoAndStop(722)` |
| 933 (print) | 722 | `call("makeDescription"); /printalert._visible=1; getURL("printasbitmap:#bframe","bil")` |

There is no other "KJØR" button. Pressing KJØR! does **not** start the drive: it shows the
confirm dialog at frame 740.

### Frame 740 confirm dialog — sprite 300 instance `afslut` (depth 815, at 262.85,241.55, scale 1.238)

Texts [D]: "Walla bhaia!" / "Skal vi cruise ut og ordne no' damer?" / "JA!" / "NEI!".

```as
// button293 "JA!" (stage ≈ 171,316)                                       [D]
tellTarget("/bil") { gotoFrame(1); play(); }   // car sprite 875 plays its drive-away anim from frame 2
tellTarget("../")  { nextFrame(); }            // root → 741
// button294 "NEI!" (≈ 337,316) and button295 "X" close (≈ 424,142)       [D]
tellTarget("../")  { gotoAndStop(camefrom); }  // camefrom == "køb" → frame 722
```

Car sprite 875 (`/bil` in the garage) frame 50: `karosseri.gotoFrame(1); gotoFrame(1); ../:bilGone = 1; stop();` [D]
→ the drive-away animation is frames 2–50 of sprite 875 (≈49 frames ≈ 4.1 s) [I: duration from frame count].

---

## 2. Main-timeline flow around the drive

### 2.1 Frame-by-frame

| frame | label | waits on | script (decoded) | next |
|---|---|---|---|---|
| 200 | gotoGame | — | `call("initGame"); stopAllSounds(); gotoAndPlay(755)` | 755 |
| 202 | initGame | (call target) | new-game init, see 2.2 | — |
| 721 | — | — | `/afslut._visible=0; bilGone=0; /printalert,/brokeassalert,haze ._visible=0; _quality="HIGH"` | plays → 722 |
| 722 | køb | stop | repair check (2.3); `stop()` | buttons |
| 740 | kør | stopped (gotoFrame) | none; shows confirm dialog 300 | JA → 741 / NEI → 722 |
| 741 | — | — | `play(); if (bilGone==1) { bilGone=0; gotoAndStop(743) } else play();` | 742 |
| 742 | — | — | `prevFrame()` → loops 741↔742 until 875 sets `bilGone=1` | 743 |
| 743 | load | — | `stopAllSounds(); cool_old = cool; gotoAndStop(368)` | 368 |
| 368 | bane1_start | stop | route dispatcher (section 4) then `stop()` | map frame |
| 368…469 | bane*_* | stop | map; clicking an unlocked district sets `goto_label`,`tilbane`, `gotoAndStop(794)` | 794 |
| 404 | bane2_start | — | `tilbane="GRØNLAND"; level=2;` | (stopped) |
| 443 | bane3_start | — | `tilbane="GRØNLAND"; level=3;` | (stopped) |
| 794 | — | stop; intro sprite 1204 | five DoActions, see 2.4; `stop()` | 1204 frame 98 → `_root.play()` |
| 795–805 | — | plays | nothing (≈1 s, same display) | 806 |
| 806 | — | stop | places control objects; `call("/sub:initObjects"); stop();` | drive loop runs inside sprites |
| 807 | slut | call target only | crash: `/dø.play(); /bil.gotoLabel("boom"); /burner._visible=0;` | (dø → 810) |
| 808 | afslut1 | call target | finish: `/exit.play(); /slinger.stop(); /move.stop(); gotoAndStop(808)` | (exit → 809) |
| 809 | afslut | call target | `stopAllSounds(); goto_label=="level1"→483, "level2"→492, "level3"→502, else gotoAndPlay(755)` | |
| 810 | slutbane | call target | `stopAllSounds(); gotoAndPlay(523)` | 523 |
| 483/492/502 | level1/2/3 | stopped | "GRATULERE BROR! LEVEL n COMPLETE" on the map | buttons 640/643/646 |
| 523 | incomplete | stop | `/printalert._visible=0; stop(); _quality="HIGH"` — "GAME OVER / WALLA BROR! HVA SKAL DU MED BMW? …" | button 656 → 529 |
| 529 | status | — | status tier by `cool` (2.5) | 530/534/539/544/549 |
| 755–793 | — | plays | 755 `tellTarget("/bmw/karosseri") gotoLabel("mujaffa")`; exterior "Bhaias Verksted" arrival anim; 793 `gotoAndPlay(721)` | 721 → 722 |

Note on `call("…:afslut1")`: when frame 808's actions run via `call`, their `gotoFrame(807)` moves the
**root** playhead to 808 (stopped) [D action, I semantics]. `call()`ed frames otherwise do not move the playhead.

### 2.2 initGame (frame 202, called by 200 and by button 43 "new game") [D]

```as
level = 1; goto_label = "bane1_start"; tilbane = "GRØNLAND";
Cam = 0; ScrollBarValueR = 0; ScrollBarValueG = 52; ScrollBarValueB = 156; colorHEX = "00349C";
repairok = 0; text = ""; burnerMc = 0; topTime = 0; cool = 0; bane_loop = 0; speed = 20; energi = 1;
fetter_1 = random(50)+20; fetter_2 = random(50)+150; fetter_3 = random(50)+350; fetter_4 = random(50)+500;
pige_1 = random(100)+50; pige_2 = random(50)+250; pige_3 = random(50)+400;     // overwritten at 794
bil_cool = 1; koster = 200; oversigt = "farve";
// …all workshop part vars and *_cool = 0 / defaults…
nummerplade = ("PJ "|"SL "|"MH "|"PM ") add (random(9)+1) add random(10)×4;   // nptemp = random(4): 3,2,1,0
penge = 5000;
```

### 2.3 Garage repair check (frame 722) [D]

```as
if (repairok == 1) {                       // repairok=1 is set by every drive (sprite 1082 frame 1)
  if (energi == 0) tellTarget("/repair_car") gotoLabel("respect");   // "Du kjører som en drøm… Du får 15 respekt"
  if (energi > 1)  { repair = energi * 20; tellTarget("/repair_car") gotoLabel("open"); }  // "Du har ødelagt din BMW! Det koster {repair}…"
}                                           // energi == 1 → no dialog
stop();
// button883 (respect "JA!"): gotoFrame(1); ../:repairok = 0; ../:cool += 15;
// button877 (repair "JA!"):
if (penge - repair > 0) { repairok = 0; penge -= repair; energi = 0; }
else if (penge - repair < 0) { repairok = 0; penge = 0; energi = repair - penge; }   // NB uses penge after zeroing → energi = repair (×20 units!) [D; looks like a bug]
gotoFrame(1);
```

### 2.4 Frame 794 (drive start) — five DoActions in tag order [D]

```as
// #1
setProperty("/info/en", _x, getProperty("/info/en", _x) + energi);   // damage bar pre-offset by carried damage
// #2
stopAllSounds();
// #3
stop();
// #4 dress the drive car /bil (sprite 1150) from garage choices
/bil/forrude  → frame by forrude: empty 1, wunderbaum 2, hjerte 3, nosser 4, koran 5
if (soltag == 1) /bil/soltag → frame 2
/bil/vinduer  → standard 1, gradient 2, tonede 3, spejlrefleks 4
/bil/hjul     → daek 0..3 → frame 1..4
/bil/heks (spoiler sprite 1120) → spoiler 0 → frame 1, 1 "lille", 2 "mellem", 3 "stor", 4 "enorm"
h = new Color(_root.bil.heks.hf); h.setRGB(parseInt(_root.colorHEX, 16));   // remaster: `car-heksfarve-N`, tinted like the body
c = new Color(_root.bil.farve);   c.setRGB(parseInt(_root.colorHEX, 16));
// #5 per-run reset
_quality = "MEDIUM"; bane = 0; gummiSafe = 0; pickup = 0; speed = 20; /info:cool = cool_old;
bil = 0; dansk_pige = 0; fetter = 0; kondom = 0; person = 0; domi = 0; danskpige = 0; fettercount = 0;
vej_over = 0; vej_over2 = 0; vej_kondom = 0; vej_person = 0; vej_dyr = 0; vej_nr = 0; vej_domi = 1; koert = 0;
fetter_1 = random(100)+200; fetter_2 = random(200)+500; fetter_3 = random(200)+800; fetter_4 = random(200)+900;
pige_1   = random(200)+200; pige_2   = random(150)+600; pige_3   = random(100)+900;
```

Then child sprite **1082** (instance name `NØRREBRO`, depth 106, off-stage at x 550) frame 1 [D]:

```as
../:repairok = 1;
if (_root.level == 3) gotoAndStop(20);       // frame 20: ../:speed = 26; stop();
else if (_root.level == 2) gotoAndStop(10);  // frame 10: ../:speed = 24; stop();
else if (_root.level == 1) play();           // frame 2:  ../:energi = 0; ../:speed = 22; stop();
```
[I] Flash runs the parent frame script before a newly placed child's frame-1 script, so the
level speed (22/24/26) overrides `speed = 20`. On **level 1 the damage `energi` is reset to 0 on
every drive**; on levels 2–3 it carries over until repaired.

Intro sprite **1204** (depth 307, 99 frames): "LEVEL: {../:tilbane}" (frame 7), key help (frame 21):
`X – SCORE BLONDINE`, `Z – HILS PÅ DIN KOMPIS`, `H – TUT MED HORN`, `B – BØØRN-OUT`,
`<PILTASTER> – STYRER DIN BMW`; "GET READY TO CRUISE!" blinking frames 40–88 [D texts].
Frame 98: `tellTarget("../") play();` frame 99: `stop()` [D] → root plays 795…806 (≈8.2 s + 1 s) [I timing].

Frame 806 places the logic/controller clips (all off-stage at x ≈ 530–560 except where noted) [D]:
`control` 1302, `move` 1303, `guld` 1306, `sub` 1307, `guld_2` 1308, `slinger` 1309, `exit` 1310,
`dø` 1311, `kill_fetter` 1314, `kill_pige` 1315, `bilstyr` 1317, button 1318 (keys Z/H), `vej_ting` 1319,
`pigemc` 1325, `showcool` 1326, `showcoolpige` 1327, `hornlyd` 1328, music 1330.

### 2.5 End screens [D]

```as
// frame 529 "status"
myStatus = "Du fikk " add cool add " street cred points.";
if (cool < 200) gotoAndStop(530);                    // "Grønnsakshandler-assistent"
if (cool > 199  && cool < 600)  gotoAndStop(534);    // "Underbetalt dop-pusher"
if (cool > 599  && cool < 1200) gotoAndStop(539);    // "Gjeng-prospect"
if (cool > 1199 && cool < 2500) gotoAndStop(544);    // "Etnisk player/byvanker"
if (cool > 2499) gotoAndStop(549);                   // "Top dawg gangsta-boss"
// 530/534/539/544/549 set bk_afsenderStatus, myTypePrint = 1..5, bk_Status = "statusN.swf"
// buttons there: 659 → gotoAndPlay(616) (highscore), 660 → call("makeGameOverDescription"); gotoAndStop(600) (print)
```
Level-complete buttons: 640 (at 483) `_root.goto_label="bane2_start"; gotoAndPlay(755)`;
643 (at 492) `_root.goto_label="bane3_start"; gotoAndPlay(755)`; 646 (at 502) `gotoAndStop(529)`.
Incomplete button 656 (at 523) → `gotoAndStop(529)`.

**Unreachable result frames** [D by exhaustive search of all 998 sites; I that they are dead]:
338 `nørrebro` (sets `level_complete = "LEVEL " add tilbane add " COMPLETE"`, shows
`fetterStatusText`/`pigeStatusText`/`bimmerpointText` via sprites 505/511/514), 347, 357, 518 `crash`
("GAME OVER … DU KJØRTE GALT I DIN BMW!", same score breakdown), 524 `complete`. No goto, label goto
or `call` reaches them (338 is not reachable by nextFrame either: the instructions pages 330–337 have no
"next" on 334–337). They look like leftovers from the previous game. The score-breakdown formulas they
show are: `fettercount x 10 x bil_cool`, `danskpige x 20 x bil_cool`, BMW cool factor `bil_cool`.

---

## 3. The drive itself

### 3.1 Character ids and roles (drive frames 794–809)

| id | instance | depth | role | evidence |
|---|---|---|---|---|
| 951 | — | 2 | road background (grey asphalt + sidewalks), static shape | D placement, I visual |
| 955 | `vejstriber` | 3 | scrolling centre dashes + sidewalk tiles (dash period 139 px, tile period 34 px) | D code, I measured |
| 957 | `vej_1` | 56 | zebra crossing ("vej_over"), spawned x 252, y −150 | D |
| 959 | `vej_2` | 59 | second road marking ("vej_krys"), spawned x 262, y −300 | D |
| 972 | `burner` | 62 | burn-out smoke/skid + `topTime` clock; contains button 960 (key B) | D |
| 975 | `kondom` | 66 | condom pickup (2 frames) | D |
| 1072 | `person` | 71 | pedestrian; frame = district label; 8 variant sprites 1008/1021/1041/1047/1067/1069/1070/1071 | D |
| 1081 | `fetter` | 73 | the cousin (77 frames: walk 1–11, greet 14–41, `hej` 44–70, `splat` 73) | D |
| 1082 | `NØRREBRO` | 106 | invisible: per-level speed, energi reset, repairok | D |
| 1090 | `pige` | 108 | blonde girl (walk 1–9, 10 stop, `splat` 13) | D |
| 1150 | `bil` | 124 | the player's BMW (top view, scale 0.6, start 314.55,358.7); children `hjul` 1095, `farve` 1098, `vinduer` 1104, `soltag` 1107, `heks` 1120 (spoiler), `forrude` 1125, `volla` 1133 (greet anim), `pige` 1149 (girl-in-car anim); label `boom` = frame 4 | D |
| 1159 | `domi` | 261 | Domino's pizza moped (child `domi` 1157, 3 looks; frame 2 crash sound) | D, I "Domino's" from art |
| 1197 | `dyr` | 285 | other car; frame = district label; car sprites 1171/1178/1185/1188/1191/1194/1195/1196 | D |
| 1204 | — | 307 | "GET READY TO CRUISE!" intro panel | D |
| 1205 / 1330 | — | 318 | music (sound 60 / sound 1329; 1330 branches on `speaker_woofer>0`) | D |
| 1231 | `info` | 320 | HUD bar (see 3.9) | D |
| 1295 | `carCam` | 348 | BMW-CAM in-car clip (`knep1..9`), seats by `indtraek` | D |
| 7 | — | 973 | invisible full-stage button (`ljhljhg=1/0`), click shield | D code, I purpose |
| 1296–1301 | — | 975–980 | debug edit texts `/control:L`, `dansk_pige`, `fetter`, `danskpige`, `kondom`, `speed` at x≈512 (off-stage) | D |
| 649 | `tjeck` | 981 | anti-cheat watchdog for `cool`/`penge` | D |
| 1302 | `control` | 211 | world scroll + spawns (labels `move`=5, `tilbage`=12) | D |
| 1303 | `move` | 213 | 2-frame main loop driver | D |
| 1306 / 1308 | `guld` / `guld_2` | 215 / 234 | gold chain money pickups (11 frames) | D |
| 1307 | `sub` | 232 | collision routines (labels `bmw` 6, `initObjects` 10, `checkCollision` 20, `domivsbil` 33, `kondom` 43, `dyr` 51, `person` 56, `pige` 65, `fetter` 72) | D |
| 1309 | `slinger` | 251 | moped swerve (27-frame x wobble) | D |
| 1310 | `exit` | 253 | end-of-level drive-off | D |
| 1311 | `dø` | 255 | crash sequence (14 frames, crash sound 1158) | D |
| 1314 / 1315 | `kill_fetter` / `kill_pige` | 257 / 259 | "−25" popup (`show_cool=-25`, 25 frames) | D |
| 1317 | `bilstyr` | 287 | steering integrator; contains key button 1316 (arrows) | D |
| 1318 | — | 289 | key button: Z (greet), H (horn) | D |
| 1319 | `vej_ting` | 291 | random encounter roller | D |
| 1325 | `pigemc` | 293 | girl pick-up sequence; contains button 1323 (X) | D |
| 1326 / 1327 | `showcool` / `showcoolpige` | 301 / 303 | "+N" popups (`int(bil_cool*10)` / `int(bil_cool*20)`) | D |
| 1328 | `hornlyd` | 305 | horn sounds 887/888/889 by `_root.horn` | D |

Sounds [D]: 1329 drive music, 1158 crash (domi hit, dø), 971 burn-out, 1079 cousin greeting, 1131 `volla` shout, 887–889 horns.

### 3.2 Per-tick loop (12 fps)

```as
// move (1303) — frame 1
call("/sub:checkCollision");
// move (1303) — frame 2
call("/control:move");
rykket += ../:speed;
if (rykket > 139) { call("/control:tilbage"); rykket = 0; }   // tilbage: /vejstriber._y -= /move:rykket
../:koert += ../:speed;                                       // koert is never read anywhere [D]
if (../:speed > 5) {
  if (count == 12) {
    /info/di._x += 1;           // distance marker
    afstand += 1;
    if (afstand > 80) { call("../:afslut1"); ../:speed = 0; stop(); }
    count = 0;
  }
  count += 1;
}
gotoAndPlay(1);
```
[I] Because frame 2 jumps back to frame 1 every tick, both the move step and the collision step run
once per 12-fps tick. **Level length** = 81 distance ticks × 12 frames with `speed > 5` = **972 frames ≈ 81 s**
(time spent at speed ≤ 5 during a pick-up does not count) [D constants, I timing].

Road scroll: `/vejstriber._y += speed` every tick and snaps back by the accumulated `rykket` once
it exceeds 139 → returns exactly to its start y (224.5). With speed 22 the snap happens after 154 px,
so the 139-px dash pattern visibly jumps ~15 px once per wrap [D code, I visual consequence].

### 3.3 Input and car motion [D]

Key buttons (SWF key codes: 1 = ←, 2 = →, 14 = ↑, 15 = ↓, 98 = 'b', 104 = 'h', 120 = 'x', 122 = 'z'):

```as
// button1316 (inside bilstyr 1317) — each keyPress event
key →  : if (horzSpeed < 0) horzSpeed = (horzSpeed < -12) ? horzSpeed + 12 : 0;  else horzSpeed += 4;
key ←  : if (horzSpeed > 0) horzSpeed = (horzSpeed >  12) ? horzSpeed - 12 : 0;  else horzSpeed -= 4;
key ↑  : if (vertSpeed > 0) vertSpeed = (vertSpeed >  12) ? vertSpeed - 12 : 0;  else vertSpeed -= 4;
key ↓  : if (vertSpeed < 0) vertSpeed = (vertSpeed < -12) ? vertSpeed + 12 : 0;  else vertSpeed += 4;
// button1318 (root, depth 289)
key z  : if (fetter == 1) tellTarget("/bil/volla") play();      // greet the cousin
key h  : tellTarget("hornlyd") play();                         // horn (cosmetic)
// button1323 (inside pigemc), cond release OR key x
key x  : if (../:dansk_pige == 1) play();                       // pigemc → pick up the girl
// button960 (inside burner 972)
key b  : if (_root.dansk_pige == 1) {} else {
           bil_y = ../bil._y; newTime = _root.topTime - lastBurnTime;
           if (newTime > 10 && bil_y > 50 && bil_y < 380) { lastBurnTime = _root.topTime; gotoAndPlay(4); } }
```
[I] keyPress button events fire on the OS key-repeat, so holding an arrow adds ±4 per repeat.
There is **no velocity cap** [D: no clamp exists]. Z/X have **no proximity test** — only the
state flag (cousin/girl currently on screen and not yet handled).

```as
// bilstyr 1317 frame 1 — friction: every 4th tick each axis decays by 1 toward 0
if (count == 3) { count = 0;
  if (horzSpeed < 0 && /bil._x) horzSpeed += 1;  if (horzSpeed > 0) horzSpeed -= 1;
  if (vertSpeed > 0) vertSpeed -= 1;             if (vertSpeed < 0) vertSpeed += 1;
} else count += 1;
// bilstyr frame 2 — integrate (only while ../:speed > 5)
if (../:speed > 5) {
  if (bily + vertSpeed > 60 && bily + vertSpeed < 440) /bil._y += vertSpeed; else vertSpeed = 0;
  if (bilx + horzSpeed > 60 && bilx + horzSpeed < 440) /bil._x += horzSpeed; else horzSpeed = 0;
}
gotoAndPlay(1);
```
The car moves freely in x,y ∈ (60, 440). **The player cannot change the road `speed`** — it is
fixed per level (22/24/26) and only lowered by scripted sequences (girl pick-up) [D].

### 3.4 Spawning

```as
// control 1302, label "move" (frame 5) — every tick, after `speed = ../:speed`
if (speed < 5) L += 0.5; else L = int(L + 1);                          // L = spawn clock (debug text 1296)
if (L == fetter_1 || L == fetter_2 || L == fetter_3 || L == fetter_4) {
  /fetter._y = -30; /fetter._x = random(2)==0 ? 35 : 470; /fetter._visible = 1;
  ../:fetter = 1; /fetter.gotoAndPlay(1);
}
if (L == pige_1 || L == pige_2 || L == pige_3) {
  /pige._y = -30; /pige._x = random(2)==0 ? 35 : 470; /pige._visible = 1;
  /pige.gotoAndPlay(1); ../:dansk_pige = 1;
}
if (L == 90 && vej_kondom != 1) { /kondom._y = -30; /kondom._x = random(200)+150; vej_kondom = 1; gummiSafe = 1; }
// scrolling of world objects
guld_2, guld: if (_y > 650) { _x = int(random(500)); _y = -20 } else _y += speed;
kondom:       if (_y > 650) vej_kondom = 0; else _y += speed;
dyr: vej_dyr==1 → _y += speed + speed/3;  vej_dyr==2 → _y += speed/3;
     either: if (_y > 720) { _y = -400; _x = random(100)+120; call("/dyr:bil"); vej_dyr = 0; }
vej_1: if (_y > 650) vej_over = 0  else _y += speed;      vej_2: if (_y > 750) vej_over2 = 0 else _y += speed;
pige:   if (_y > 520 || _y < -50)  dansk_pige = 0; else if (dansk_pige 1|2) _y += speed - 5;
fetter: if (_y > 520 || _y < -150) fetter = 0;     else if (fetter 1|2)    _y += speed + 5;
vejstriber._y += speed;
if (burnerMc == 1) { if (/burner._y > 700) burnerMc = 0; /burner._y += speed; }
```
Spawn clock values (frame 794): cousin at L = 200–299, 500–699, 800–999, 900–1099; girl at
L = 200–399, 600–749, 900–999; condom forced at L = 90. Since a level is ≈ 972 ticks, the last
cousin/girl often never appears [D constants, I consequence]. Fetter/pige move faster/slower than
the road (±5 px/tick) — they "walk" along the sidewalk [I].

```as
// vej_ting 1319 frame 1
domino = 1;
if (_root.level == 1) gotoAndPlay(10); else if (_root.level == 2) gotoAndPlay(17); else play();
// each table: roll `ting = random(100)` 2 frames into the cycle, evaluate 2 frames later, loop (5-frame cycle)
```

| roll value(s) | table A (frames 2–6, **level 3** and other) | table B (frames 10–14, **level 1**) | table C (frames 17–21, **level 2**) |
|---|---|---|---|
| `vej_over` (crossing) | 80, 40 | 80, 40 | 80, 40 |
| `vej_krys` | 15, 16 | 15, 16 | 15, 16 |
| `kondom` | 35 | 35 | 35 |
| `dyr` (oncoming car) | 8,68,48,25,58,38,78,88 | same | 1–49 |
| `dyrbak` (slow car ahead) | 21,61,31,71 | +81, 91 | 41–79 |
| `person` | 21,61,31,71 | same | 21,61,31,71 |
| `domi` (moped from behind) | 7, 97 | 7, 97, 61 | 61–89 |
| `domibak` (oncoming moped) | 19, 29 | 19, 29, 99, 59 | 11–39 |

Call order is dyr, dyrbak, (person,) domi, domibak (table C: dyr, dyrbak, domibak, domi, person); each
handler only spawns if its slot is free, so the first one that fires wins the slot [D]. [I] Level 2 is by
far the densest; level 3 uses the sparsest table — looks unintended but is what the bytes say.

Spawn handlers [D]:
```as
vej_over (27): if (vej_over == 0 && vej_over2 == 0) { vej_over = 1;  /vej_1._x = 252; /vej_1._y = -150; }
vej_krys (51): if (vej_over == 0 && vej_over2 == 0) { vej_over2 = 1; /vej_2._x = 262; /vej_2._y = -300; }
kondom   (34): if (vej_kondom == 0) { vej_kondom = 1; /kondom._y = -30; /kondom._x = random(360)+70; }
domi     (40): if (vej_domi == 0) { vej_domi = 1;
                 if (domino == 0) { /domi._rotation = 0; domino = 1; _root.domi.domi.gotoAndStop(random(3)+1); }
                 /domi._y = 600; /domi._x = random(40)+360; /domi.gotoAndStop(1); /slinger.play(); }
domibak  (64): if (vej_domi == 0) { vej_domi = 2; if (domino == 1) { /domi._rotation = 180; domino = 0; }
                 /domi._y = -100; /domi._x = 90; _root.domi.domi.gotoAndStop(1); /slinger.play(); }
dyr      (46): if (vej_dyr == 0) { vej_dyr = 1; call("/dyr/bil:bil"); /dyr._rotation = 0;   /dyr._y = -400; /dyr._x = random(80)+140; }
dyrbak   (58): if (vej_dyr == 0) { /dyr._rotation = 180; call("/dyr/bil:bil"); vej_dyr = 2; /dyr._y = -400; /dyr._x = random(100)+250; }
person   (71): if (vej_person == 0) { vej_person = 1; /person._y = -30; }   // x never changes: 466.55 (right sidewalk)
```
`dyr/bil:bil` picks a random look of the district's car sprite (e.g. 1171: `b = random(3)+1` → frame 1/3/5) [D].
`slinger` 1309 frames 2–25 nudge `/domi._x` by +0.5…+2 then −0.5…−2 (a swerve), loop to 2 [D].

### 3.5 Collision test (sub 1307) [D]

Half-sizes are measured from the clips at `initObjects` (frame 10; also re-called by domi/dyr variants):
`guld_h* = _width/2,_height/2`; `kondom_h*` same; `domi_hwidth = _width/2 − 2`, `domi_hheight = _height/2 − 5`;
`mod_bil_h* = dyr._width/2 − 7`, `_height/2 − 7`; `person_h*` = /2. `bil_hwidth/hheight = /bil._width/2,_height/2`
(frame 6 `bmw`). **`pige_hwidth/hheight` and `fetter_hwidth/hheight` are never assigned** → 0, i.e. the girl
and cousin are tested as a point [D absence, I effect].

Test pattern for every object `o` against car box `[bil_x1,bil_x2]×[bil_y1,bil_y2]`:
```as
left  = bil_x1 <= o_x1 <= bil_x2;  right  = bil_x1 <= o_x2 <= bil_x2;
top   = bil_y1 <= o_y1 <= bil_y2;  bottom = bil_y1 <= o_y2 <= bil_y2;
hit   = (left&&top) || (right&&top) || (left&&bottom) || (right&&bottom);   // a corner of o inside the car box
```
Typos in the original: dyr test uses `right_hit`/`left_hit` (the gold flags, already reset to "0") in two
terms → only the (left,top) and (right,bottom) corners count; fetter uses `bottom_hit8` (girl flag) in its
last term → 3 corners [D]. Approximate rendered sizes at frame 1 [I]: car 94×152, dyr 110×148,
domi 50×92, fetter 50×46, pige 45×33, kondom 18×48, guld 48×54, person 35×82.

`checkCollision` (frame 20) order: `call dyr, domivsbil, person, pige, fetter, kondom`, then recompute the car
box and test `guld` and `guld_2` inline [D].

### 3.6 Encounters [D unless marked]

**Gold chains `guld`/`guld_2` (money).** Always cycling. On hit and `guld_ok == 1`:
`ran = random(120)+100; guld_ok = 0; ../:penge += ran; /guld:guld = ran; /guld.play()`. guld frame 2 shows
`scor` and plays `/info/penge`; frame 11 respawns at x `random(460)+20`, y −20; frame 1 sets
`/sub:guld_ok = 1; stop()`. Same for `guld_2` with `ran1`/`guld_ok2`. No effect on `cool`.

**Condom `kondom`.** On hit while `vej_kondom == 1` and `kondom < 3`: `/kondom.play(); /info/kondom.nextFrame();
/kondom._y = 600; kondom += 1; vej_kondom = 0`. HUD `info/kondom` (1230) labels `0gummi..3gummi`.

**Cousin `fetter`.** Greeting: Z while `fetter == 1` → `/bil/volla` (1133) frame 11 → `/fetter.gotoAndPlay(14)`:
```as
../:cool += int(../:bil_cool * 10); ../:fettercount += 1; ../:fetter = 2;
/showcool at fetter pos (y clamped to ≤ 450) .play();  /info/respect.gotoAndPlay(2);
if (/fetter._x > /bil._x) gotoAndPlay(44);   // "hej" facing variant
```
Run over (fetter 1|2, hit, **and `speed > 3`**): `/kill_fetter` to fetter pos, `gotoLabel("2"); play()` (−25 popup);
`/fetter.gotoLabel("splat")` → frame 73: `/blod.play(); ../:cool -= 25;` ; `fetter = 3` → then `_y += speed`.
Leaves screen (`_y < -30 || > 530`) → `fetter = 0; _visible = 0`.

**Girl `pige` (dansk pige / blondine).** Run over (dansk_pige 1|2, hit, no speed condition): `/kill_pige` popup,
`/pige.gotoLabel("splat")` → frame 13: `stop(); ../:cool -= 25;`; `dansk_pige = 3` → `_y += speed`.
Off-screen (`_y < -30 || > 530`) → `dansk_pige = 0; _visible = 0`.
Pick-up: X while `dansk_pige == 1` → `pigemc` (1325) plays:
```as
2:  area = pige above car ? (pige left ? 1 : 3) : (pige left ? 2 : 4);
3:  lastspeed = ../:speed; ../:dansk_pige = "0"; ../:pickup = 1; /slinger.stop(); ../:speed = int(speed/2);
6, 9: ../:speed = int(speed/2);   12: ../:speed = 0; _root.slinger.stop();
14: area 1|3 → r180.play(); stop()  (girl turns) ; else gotoAndPlay(20)
16-17 loop: pige._y += 10 until pige_y + 10 >= bil_y → 23      20-21 loop: pige._y -= 10 until ≤ bil_y → 23
23: turn ±90 (r-90 for 1,4; r+90 for 2,3)
25-26 loop (left side): pige._x += 10 until pige_x + 10 >= bil_x − bil_w/2 − 10 → 32
29-30 loop (right side): pige._x -= 10 until pige_x − 10 <= bil_x + bil_w/2 + 10 → 32
32: if (../:kondom == 0) { /bil/pige.gotoLabel("flipper"); play(); set_respect = 0; }      // rejected
    else { /info/kondom.prevFrame(); set_respect = 1; /pige._visible = 0; ../:danskpige += 1; ../:kondom -= 1;
           /bil/pige.gotoLabel(area 3|4 ? "ok" : "ok2"); play(); }
    stop();          // resumed by /bil/pige (1149) calling /pigemc.play() at its frames 125/202/205/221
33: /pige._visible = 1;
34: r180.play(); if (set_respect == 1) { /info/respect anim; /showcoolpige at pige pos .play();
                                          ../:cool += int(../:bil_cool * 20); set_respect = 0; } stop();
35 → 39; 40 loop: walk back to sidewalk (x→475 for area 3|4, x→35 otherwise) 10 px/frame; 42/46 turn; 44/47 dansk_pige = 2
51: /pige._rotation = 0; ../:dansk_pige = 2; /pige._visible = 1;
54: ../:speed = lastspeed/4; /slinger.play();   57, 60: speed += lastspeed/4
63: speed += lastspeed/4; ../:pickup = 0; _root.slinger.play(); gotoAndStop(1);
```
In-car anim `/bil/pige` (1149): `ok` 2, `ok2` 28 → frame 56 `censur`: `if (_root.Cam == 1) gotoAndPlay(127 "cam_on")`
(→ `_root.carCam.gotoAndPlay(2)`: random `knep1..9` clip, seat fabric by `indtraek`) else continue; `flipper`/`skrid` 206.
`Cam` is set by the BMW-CAM workshop purchase (button 915: −6000 kr, `bil_cool += 0.7`, `cam = 1`).
After the girl returns to the sidewalk `dansk_pige = 2`, so she can still be run over (−25) [D].

**Moped `domi`.** Movement (sub `domivsbil`, frame 33): `vej_domi == 1` → `_y -= speed/3` (overtakes from behind);
`vej_domi == 2` → `_y += speed + speed/3` (oncoming). Leaving (`_y < -100 || > 650`) → `vej_domi = 0;
/slinger.gotoAndStop(1)`. On hit:
```as
../:vej_domi = 0; domi = "2";
if (../:energi + 15 > 80) call("../:slut");          // crash → game over
../info/en._x += 15; ../:energi += 15; /domi.play(); // domi frame 7: _y = 600; gotoAndStop(1)
// while domi == 2: _y += speed + speed/3 until off-screen, then domi = "1"
```
Initial `vej_domi = 1` with domi at y 826 → immediately reset to 0 on the first tick [D/I].

**Other car `dyr`.** On hit (vej_dyr 1|2): `tellTarget("/dyr/bil") play()` → the stopped "look" frame advances to the
next frame which does `call("minus30"); gotoAndPlay(boom)` (BISLET set 1194 looks 4–5 call `minus10`):
```as
// minus30 (e.g. sprite1185 frame 21)                    // minus10 identical with 10
if (_root.energi + 30 > 80) call("../../:slut");
_root.info.en._x += 30; _root.energi += 30;
// after the boom anim: _root.vej_dyr = 0; ../../dyr._y = 700; call("bil");   (re-roll look)
```
In **sprite 1171 (GRUNERLØKKA)** the crash call is `call(eval("../../:slut"))` — it calls the frame *named by the
value* of root variable `slut` (undefined) → no crash is ever triggered there [D bytes, I no-op semantics].

**Pedestrian `person`.** Sub frame 56, only while `vej_person == 1`: `_y += speed − speed4` (`speed4` undefined → 0);
hit → `/person/person.play()` (blood anim `blod`), `vej_person = 2` → `_y += speed`; off-screen → `vej_person = 0`.
The variant sprite's last frame (e.g. 1008 frame 29): `vej_person = 0; /person._y = 600; random look`.
**No score, money or damage effect** [D: no such writes in any person sprite].

**Burn-out `burner` (B).** Frame 4: `call("b"); bspeed = 10; burnerMc = 1;` tyre marks by `daek`; frames 5–12 `call("b")`
(`b` = frame 118: `if (/bil._y < 440) /bil._y += bspeed`) → car pushed down 10 px/frame for 9 frames; frame 15:
`call("s")`, burner placed at the car, frames 16–28 `call("s")` (`s` = 119: `if (/bil._y > 60) /bil._y -= bspeed`) →
car shoots forward ~140 px; smoke scrolls with the road (`burnerMc`); frame 117 parks it at (−50,−50). 10-s cooldown via
`topTime = int(getTimer()/1000)` (updated by burner frames 1–2). Cosmetic: no cool/money [D]. Frames 124–167 (speed
ramp) are never reached [D: no goto targets them].

**Horn (H).** `hornlyd`: `standard` → frame 5 (sound 887), `kompressor` → 13 (888), `multitone` → 40 (889). Cosmetic.

### 3.7 Scoring summary

| event | `cool` | `penge` | `energi` | counters |
|---|---|---|---|---|
| greet cousin (Z) | `+int(bil_cool*10)` | | | `fettercount++` |
| pick up girl with condom (X) | `+int(bil_cool*20)` | | | `danskpige++`, `kondom--` |
| girl without condom | 0 ("flipper") | | | |
| run over cousin (speed>3) / girl | −25 | | | |
| gold chain | | `+100..219` | | |
| condom | | | | `kondom++` (max 3) |
| moped hit | | | +15 | |
| car hit | | | +30 (+10 BISLET looks 4–5) | |
| person hit, burn-out, horn | — | — | — | — |
| garage, `energi == 0` after a drive → "respect" dialog JA | +15 | | | |
| garage repair JA | | `−energi*20` | → 0 | |

`bil_cool` starts 1.0 and grows with workshop parts (+0.1…+0.7 each). [D]

Anti-cheat `tjeck` (649): snapshots `breakc = cool`, `breakp = penge`; every cycle (frames 2–3 loop) if either
changed, frame 8: `if (breakc + 150 < cool /*local, undefined*/) cool = breakc else breakc = cool`; frame 11:
`if (breakp + 500 < penge) penge = breakp else breakp = penge` [D]. The cool check reads an undefined local so never
fires [I]; a money jump > 500 within one cycle is reverted [D].

### 3.8 How a drive ends [D]

1. **Distance reached** (`afstand > 80`): `call("../:afslut1")` (root 808) → `/exit.play()`, `/slinger.stop()`,
   `/move.stop()` (collisions, scrolling and distance stop; `speed = 0` also disables steering; `vej_ting` keeps
   rolling but nothing moves [I]);
   `exit` 1310 frames 2–3 loop: each frame `/bil._y -= 22`, `c += 1` once per 2-frame loop; when `c > 22` (≈23 loops,
   ≈46 frames ≈ 3.8 s, car leaves through the top) → frame 4 `call("..:afslut")` (root 809):
   `level1|level2|level3` → map level-complete frame 483/492/502; otherwise `gotoAndPlay(755)` → garage arrival →
   721 → 722 (repair/respect dialog because `repairok = 1`).
2. **Crash** (`energi + damage > 80`): `call("../:slut")` (root 807) → `/dø.play()`, `/bil.gotoLabel("boom")`,
   burner hidden. The damage is still added after the call and the loop keeps running [D]; `dø` frame 14
   `call("..:slutbane")` (root 810) → `gotoAndPlay(523)` "GAME OVER / HVA SKAL DU MED BMW?" → button → 529 status tier →
   highscore/print. **A crash ends the whole game**, not just the level.
3. There is no timer-based end and no fuel; `topTime` is only the burn-out cooldown clock, `koert` is write-only.

### 3.9 HUD (`info` 1231 at 337.05,197.35, x-scale 1.01) [D]

| element | binding | meaning |
|---|---|---|
| 1209 `penge` → edit 1208 | `../../:penge` | PENGER (gold-chain pop anim) |
| 1211 `respect` → edit 1210 | `../../:cool` | CRED |
| edit 1207 | `../:bil_cool` | BMW factor |
| edit 1221 / 1222 | `../:tilbane` / `../:level` | BANE/LVL |
| 1214 `en` (x-scale 1.5) at local x −167.8 | `_x += damage` | ENERGI bar slides right by damage; crash at > 80 |
| 1226 `di` at local x −161 | `_x += 1` per distance tick | DISTANSE marker, 81 px per level |
| 1230 `kondom` | frames `0gummi..3gummi` | condoms held |
| 1 (logo), 545 "BMW", 1216–1220 labels | — | static |

---

## 4. Route map / level select

Dispatcher, frame 368 first DoAction [D]:
```as
_quality = "MEDIUM";
if      (goto_label eq "bane1_start")         gotoAndStop(368);
else if (goto_label eq "bane1_grønland")      gotoAndStop(373);
else if (goto_label eq "bane1_grunerløkka")   gotoAndStop(378);
else if (goto_label eq "bane1_sinsen")        gotoAndStop(383);
else if (goto_label eq "bane2_start")         gotoAndStop(404);
else if (goto_label eq "bane2_grønland")      gotoAndStop(409);
else if (goto_label eq "bane2_rådhusplassen") gotoAndStop(414);
else if (goto_label eq "bane2_bislett")       gotoAndStop(419);
else if (goto_label eq "bane2_sinsen")        gotoAndStop(424);
else if (goto_label eq "bane3_start")         gotoAndStop(443);
else if (goto_label eq "bane3_grønland")      gotoAndStop(368);   // !! should be 448 (label there is misspelt "abne3_grønland")
else if (goto_label eq "bane3_rådhusplassen") gotoAndStop(453);
else if (goto_label eq "bane3_frogner")       gotoAndStop(458);
else if (goto_label eq "bane3_holmenkollen")  gotoAndStop(463);
else if (goto_label eq "bane3_sinsen")        gotoAndStop(469);
else if (goto_label eq "level1")              gotoAndStop(483);
else if (goto_label eq "level2")              gotoAndStop(492);
else if (goto_label eq "level3")              gotoAndStop(502);
// second DoAction: stop();
```

**Meaning of the variables** [D usage, I naming]:
- `goto_label` = the map state to show **after** the drive you just chose (it is written when you click a district,
  before driving). Because a finished drive returns to the garage, and KJØR! always goes 743 → 368, the next KJØR!
  lands on the map state "district X done".
- `tilbane` = the district being driven ("til bane" = to the track). Read by the intro ("LEVEL: …"), HUD, and by
  `dyr` (1197) / `person` (1072) `gotoAndStop(_root.tilbane)` to pick district-specific traffic and pedestrians.
- `level` (1/2/3) — only written at 202 (=1), 404 (=2), 443 (=3). Read by 1082 (speed 22/24/26, energi reset on L1)
  and by `vej_ting` (spawn table). It is shown in the HUD/map panel.
- `level_complete` — only written in unreachable frame 338; never shown in the live flow.
- `bane` — set to 0 at 794, never read. `bane_loop` — only used by unreachable button 521.

**What the player sees** (`assets/generated/drive/png/map-368.png` once installed): an illustrated Oslo
map; HUD panel 552 (BMW `bil_cool`, SPENN `penge`, RESPEKT `cool`, LEVEL, "CURENT LOCATION" `tilbane`); legend
"= DU ER HER / = TILGJENGELIG BANE / = INGEN ADGANG"; one rollover box per district (580/588/595 instances
`box_<district>` with `kort_rolllevel`, `kort_rollstatus`). Locked district buttons (561–565, 569, 570) only show
"INGEN ADGANG" on rollover; TØYEN (568) shows "DU ER HER!" (home). The single clickable district per state shows
"KLIKK FOR Å CRUISE HIT" and on release sets `goto_label`, `tilbane`, `gotoAndStop(794)` [D].

| map frame (label) | clickable button → sets `goto_label`, `tilbane` |
|---|---|
| 368 bane1_start | 566 → `bane1_grønland`, GRØNLAND |
| 373 bane1_grønland | 610 → `bane1_grunerløkka`, GRUNERLØKKA |
| 378 bane1_grunerløkka | 611 → `bane1_sinsen`, SINSEN |
| 383 bane1_sinsen | 615 → `level1`, TVEITA |
| 404 bane2_start (`level=2`) | 618 → `bane2_grønland`, GRØNLAND |
| 409 bane2_grønland | 619 → `bane2_rådhusplassen`, RÅDHUSPLASSEN |
| 414 bane2_rådhusplassen | 621 → `bane2_bislett`, BISLETT |
| 419 bane2_bislett | 624 → `bane2_sinsen`, SINSEN |
| 424 bane2_sinsen | 627 → `level2`, TVEITA |
| 443 bane3_start (`level=3`) | 628 → `bane3_grønland`, GRØNLAND |
| 448 abne3_grønland | 629 → `bane3_rådhusplassen`, RÅDHUSPLASSEN |
| 453 bane3_rådhusplassen | 631 → `bane3_frogner`, FROGNER |
| 458 bane3_frogner | 633 (rollover says HOLMENKOLLEN) → **`bane3_frogner`, FROGNER** (bug) |
| 463 bane3_holmenkollen | 624 (reused) → **`bane2_sinsen`, SINSEN** (bug) |
| 469 bane3_sinsen | 636 → `level3`, TVEITA |
| 483 level1 | 640 "next level" → `goto_label = "bane2_start"`; `gotoAndPlay(755)` (garage) |
| 492 level2 | 643 → `goto_label = "bane3_start"`; garage |
| 502 level3 | 646 → `gotoAndStop(529)` status / game end |

So: **Level 1** = Grønland → Grünerløkka → Sinsen → Tveita; **Level 2** = Grønland → Rådhusplassen → Bislett →
Sinsen → Tveita; **Level 3 (intended)** = Grønland → Rådhusplassen → Frogner → Holmenkollen → Sinsen → Tveita.
Each district is one drive; after each drive you are back in the garage (repair / shop), then KJØR! → map.

**As decoded, level 3 cannot be completed** [D bytes, I consequence]: after its first drive the dispatcher sends
`bane3_grønland` to frame 368 (the level-1 start map, `level` stays 3), restarting the level-1 route with
level-3 speed; and even via that route you would loop. The 458/463 buttons also loop (Frogner→Frogner,
Holmenkollen→level-2 Sinsen). A faithful rebuild must decide whether to replicate or fix (see open questions).

District-specific content via `tilbane` labels [D]: `dyr` 1197 labels GRUNERLØKKA, FROGNER, RÅDHUSPLASSEN,
SINSEN, TØYEN, GRØNLAND, **BISLET**, TVEITA, HOLMENKOLLEN (→ 1171, 1178, 1178, 1185, 1188, 1191, 1194, 1195, 1196);
`person` 1072 labels GRUNERLØKKA, GRØNLAND, SINSEN, RÅDHUSPLASSEN, BISLETT, HOLMENKOLLEN, TVEITA, FROGNER.
`tilbane = "BISLETT"` does not match label `BISLET` → [I] `gotoAndStop` to a missing label is a no-op, so Bislett
uses frame 1 (Grünerløkka car set).

---
