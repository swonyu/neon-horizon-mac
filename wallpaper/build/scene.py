"""The stylesheet and document template.

Read the companion notes in docs/WALLPAPER.md before changing any number here.
The three rules that keep this scene from degenerating back into a screensaver:

  1. ONE camera law. .camera is a static overscale; .world translates; the near
     plane is the only scale animation in the file.
  2. COPRIME PERIODS. No two large-area elements share a prime factor, so the
     frame does not return to a previous state inside ~39 minutes.
  3. NO DWELL ON ANYTHING LARGE. Every large-area animation — the camera drift,
     the near-plane dolly, the three haze bands, the boat bob — is asymmetric
     with per-keyframe timing functions, so it never decelerates to a stop twice
     a cycle. Small accent elements (glint flare, lamps, emitters, smears) keep a
     plain symmetric ease on purpose: at their size and contrast the dwell is
     below threshold, and the periods are coprime so they never dwell together.

Durations all route through calc(var(--t)*...) so the calm tier (#calm) is one
variable rather than a duplicated block.
"""
from string import Template

CSS = Template(r'''
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#100d22}
:root{--t:1;--city-image:url("${CITY}");--boat-image:url("${BOAT}");
  --city-blur:url("${CITYBLUR}")}
body.calm{--t:3}

.scene{position:fixed;inset:0;overflow:hidden}

/* The camera no longer animates. A continuously animating scale() never lands
   on a stable sample grid, so every fine edge in a 2.3x-upsampled painting
   crawls; a static overscale lets the rasteriser settle. */
.camera{container-type:size;position:absolute;inset:-2% -2% -.8%;
  transform:scale(1.012);transform-origin:50% 100%}
.world{position:absolute;bottom:0;left:50%;width:max(100cqw,150cqh);aspect-ratio:3/2;
  transform:translate3d(-50.22%,.06%,0);
  animation:drift calc(var(--t)*233s) linear infinite;will-change:transform}
.city{position:absolute;inset:0;background:var(--city-image) center/100% 100% no-repeat}

/* translateX(-50%) is folded into the keyframe literals: a calc() here and a
   transform there would fight, and the scene would shove half a world right.
   Four unequal stops, per-keyframe easing, so there is no dwell. */
@keyframes drift{
  0%{transform:translate3d(-50.22%,.06%,0);animation-timing-function:cubic-bezier(.36,0,.66,1)}
  34%{transform:translate3d(-49.86%,-.02%,0);animation-timing-function:linear}
  61%{transform:translate3d(-49.78%,-.06%,0);animation-timing-function:cubic-bezier(.3,0,.7,1)}
  100%{transform:translate3d(-50.22%,.06%,0)}}

/* ---- depth: the near promenade is its own plane -------------------------- */
/* Same image, same CachedImage, bounded to the wet stone and scaled against the
   camera.
   The boundary is a FEATHERED MASK, not a clip-path. A hard clip was tried and
   fails: the plane and the base are the same picture at different scales, so a
   hard edge butts two copies that are offset by ~13px at the dolly extreme, and
   the parapet visibly steps. Feathering cross-dissolves them instead, and the
   offset disappears into the ramp.
   Layer 1 is a half-plane whose transition is centred on the painted parapet.
   Its 31.1deg angle and 31.35% stop centre are derived, not eyeballed: .world's
   aspect-ratio is pinned at 3/2, so the parapet's two endpoints (24%,62%) and
   (66%,100%) both project to 31.35% along a 31.1deg gradient line on EVERY
   display. Layer 2 trims the top of the left terrace, where the promenade edge
   is nearly horizontal rather than following the parapet. Intersected. */
.plane-near{position:absolute;inset:0;background:var(--city-image) center/100% 100% no-repeat;
  transform-origin:50% 100%;transform:scale(1.012);will-change:transform;
  -webkit-mask-image:linear-gradient(31.1deg,#000 27.4%,transparent 35.3%),
                    linear-gradient(to bottom,transparent 52%,#000 62%);
  -webkit-mask-composite:source-in;
  mask-image:linear-gradient(31.1deg,#000 27.4%,transparent 35.3%),
             linear-gradient(to bottom,transparent 52%,#000 62%);
  mask-composite:intersect;
  animation:dolly calc(var(--t)*233s) linear infinite}
@keyframes dolly{
  0%{transform:scale(1.012);animation-timing-function:cubic-bezier(.4,0,.72,1)}
  43%{transform:scale(1.040);animation-timing-function:linear}
  69%{transform:scale(1.027);animation-timing-function:cubic-bezier(.3,0,.6,1)}
  100%{transform:scale(1.012)}}

/* ---- bloom: the single biggest change ------------------------------------ */
/* contrast(2.6) IS the threshold: CSS contrast is out = 2.6*in - 0.8, crossing
   zero at in=.308, so after brightness(1.5) everything originally below ~.205
   luma goes hard black and contributes nothing under screen. Only clipped light
   sources bleed; the painting's darks are protected.
   Rendering at 25% and scaling 4x makes blur(5px) an effective 20px radius at
   1/16 the kernel cost. translateZ(0)+backface-visibility pin the raster scale. */
.bloom-wrap{position:absolute;inset:0;overflow:hidden;mix-blend-mode:screen;
  pointer-events:none;opacity:.2;
  animation:bloom calc(var(--t)*89s) ease-in-out infinite;will-change:opacity}
.bloom{position:absolute;top:0;left:0;width:25%;height:25%;
  transform:scale(4) translateZ(0);transform-origin:0 0;backface-visibility:hidden;
  background:var(--city-image) 0 0/100% 100% no-repeat;
  filter:brightness(1.5) contrast(2.6) saturate(1.25) blur(5px)}
@keyframes bloom{0%,100%{opacity:.15}43%{opacity:.25}71%{opacity:.19}}

/* ---- the focal point: the sun's specular column -------------------------- */
/* The painting's own subject. It had no animation within 15% in any direction,
   which is why the eye had to go hunting in the dark corner for movement. */
.sunpath{position:absolute;left:50.8%;top:31%;width:9%;height:42%;
  transform:translateX(-50%) scaleX(.88);mix-blend-mode:screen;pointer-events:none;
  background:linear-gradient(to bottom,#ffc8ee3d 0,#ff7fd026 44%,#ff7fd00d 76%,transparent);
  -webkit-mask-image:linear-gradient(to right,transparent,#000 30%,#000 70%,transparent);
  mask-image:linear-gradient(to right,transparent,#000 30%,#000 70%,transparent);
  animation:sunpath calc(var(--t)*167s) cubic-bezier(.42,0,.58,1) infinite;
  will-change:transform,opacity}
@keyframes sunpath{
  0%,100%{transform:translateX(-50%) scaleX(.88);opacity:.62}
  37%{transform:translateX(-48.6%) scaleX(1.12);opacity:1}
  68%{transform:translateX(-51%) scaleX(.96);opacity:.78}}

/* Two counter-beating gradient ladders, not 22 sparkle elements. Translating
   exactly one tile period is what makes the crawl seamless. The soft
   transparent->colour->transparent ramp is deliberate: hard sub-pixel bars
   moire against the device grid under a slowly changing scale. */
.glit{position:absolute;inset:18% 8% 0;mix-blend-mode:screen;pointer-events:none;
  background:repeating-linear-gradient(0deg,transparent 0,#ffd6e4 1.1px,transparent 2.2px,transparent 3.4px);
  -webkit-mask-image:radial-gradient(ellipse at 50% 0,#000 12%,transparent 78%);
  mask-image:radial-gradient(ellipse at 50% 0,#000 12%,transparent 78%);
  opacity:.22;animation:crawl calc(var(--t)*1.9s) linear infinite;will-change:transform}
.glit.b{opacity:.14;transform:scaleX(.68);
  animation:crawl2 calc(var(--t)*2.9s) linear infinite}
@keyframes crawl{to{transform:translateY(3.4px)}}
/* scaleX must appear in BOTH stops: a transform keyframe replaces the base
   value outright, so declaring it only on the element loses it during the run. */
@keyframes crawl2{from{transform:scaleX(.68)}to{transform:scaleX(.68) translateY(3.4px)}}

/* ---- glints -------------------------------------------------------------- */
/* Reflected light on chopped water shivers along the viewer-to-source axis,
   which here is vertical — the shipped glints slid sideways. Height is a
   percentage, not a fixed 0.65px, so they scale with the world and survive a
   Retina change. */
.glint{position:absolute;height:var(--gh,.28%);border-radius:50%;
  background:linear-gradient(to bottom,transparent,var(--c),transparent);
  transform-origin:50% 50%;opacity:.13;
  animation:flare calc(var(--t)*var(--gt)) ease-in-out infinite;
  animation-delay:calc(var(--t)*var(--delay));will-change:transform,opacity}
@keyframes flare{0%,100%{transform:scaleY(.5);opacity:.05}50%{transform:scaleY(1.5);opacity:.22}}

/* ---- wet promenade ------------------------------------------------------- */
.wet{position:absolute;inset:0;pointer-events:none;
  -webkit-mask-image:linear-gradient(to top,#000 70%,transparent);
  mask-image:linear-gradient(to top,#000 70%,transparent)}
/* The river copy lives in .world, not .plane-near, so it escapes the parapet
   mask that would otherwise erase it. It also drops .wet's fade, which exists
   to die toward the promenade's parapet and means nothing on open water. */
.wet.river{-webkit-mask-image:none;mask-image:none}
/* Paired bright-inner / dark-outer edge. A single hairline at .2 alpha over
   ground whose p95 is L=169 lifts luminance ~7% — below threshold, which is why
   the old rings appeared only over dark pavement and read as broken arcs. The
   dark outer edge doubles local contrast at zero cost. */
.sp{position:absolute;width:var(--w);height:var(--h);border-radius:50%;box-sizing:border-box;
  transform:translate(-50%,-50%) scale(.06);
  box-shadow:inset 0 0 0 .7px var(--c), 0 0 0 .5px #140d2b73, 0 0 3px .5px #d9c4ff26;
  animation:sp calc(var(--t)*var(--p)) cubic-bezier(.1,.7,.3,1) infinite;
  animation-delay:calc(var(--t)*var(--d))}
@keyframes sp{0%{transform:translate(-50%,-50%) scale(.06);opacity:0}
  8%{opacity:.55}
  100%{transform:translate(-50%,-50%) scale(1);opacity:0}}

/* Painted reflection columns, breathing. These are tuned against the graded
   image, never the pre-knockdown one. */
.smear{position:absolute;width:.8%;transform:translateX(-50%) scaleY(1.02);
  background:linear-gradient(transparent,var(--c),transparent);
  /* mean of the .12<->.26 keyframes, so the frozen frame is not the floor */
  transform-origin:50% 0;opacity:.19;
  animation:smear calc(var(--t)*var(--st)) ease-in-out infinite;
  animation-delay:calc(var(--t)*var(--d));will-change:transform,opacity}
@keyframes smear{0%,100%{transform:translateX(-50%) scaleY(.82);opacity:.12}
  50%{transform:translateX(-50%) scaleY(1.22);opacity:.26}}

/* ---- boats --------------------------------------------------------------- */
/* Two, both verified over open water. The three that were cut included one
   parked on a rooftop and two too small to read at all. */
.boat-anchor{position:absolute;transform:translate(-50%,-50%)}
.boat-art{position:relative;aspect-ratio:3/1;background:var(--boat-image) center/contain no-repeat}
.boat-drift{position:relative;will-change:transform;
  animation:sail calc(var(--t)*var(--sail-time)) ease-in-out infinite;
  animation-delay:calc(var(--t)*var(--phase))}
.boat-bob{position:relative;will-change:transform;
  animation:bob calc(var(--t)*var(--bob-time)) linear infinite;
  animation-delay:calc(var(--t)*var(--phase))}
/* transform-origin:50% 0 with top:78% puts the mirrored box at the waterline.
   The shipped top:55%/height:100% scaled about its own centre, landing the
   reflection at 80-130% and overlapping the bottom fifth of the hull. */
.boat-reflection{position:absolute;left:0;top:78%;width:100%;height:100%;
  background:var(--boat-image) center/contain no-repeat;
  transform:scaleY(-.46);transform-origin:50% 0;opacity:.18;
  animation:reflection calc(var(--t)*var(--bob-time)) ease-in-out infinite;
  animation-delay:calc(var(--t)*(var(--phase) + var(--bob-time)/2));will-change:opacity}
/* A vertical light column is what every other light source in this painting
   does, and unlike a wake it has no direction to contradict. */
.boat-glow{position:absolute;left:38%;top:78%;width:22%;height:360%;transform-origin:50% 0;
  transform:scaleY(.86);
  background:linear-gradient(180deg,#ff5fd2cc,#ff5fd233 45%,transparent);
  filter:blur(1.6px);opacity:.5;
  animation:colshimmer calc(var(--t)*3.4s) ease-in-out infinite;
  animation-delay:calc(var(--t)*var(--phase))}
/* Travel expressed in boat-lengths on the near river's actual downstream axis.
   The shipped +/-18% resolved against the boat's own ~66px box: 16px of
   ping-pong over half a minute. */
/* Y is 126%, not 42%: translateX% resolves against the box WIDTH and
   translateY% against its HEIGHT, and .boat-art is aspect-ratio:3/1, so the
   box is three times wider than tall. To track the near river's measured
   0.6 slope the Y percentage must be 3x the naive value, or the boats cut
   across the current at half the bank's angle. */
@keyframes sail{0%,100%{transform:translate(-70%,-126%)}50%{transform:translate(70%,126%)}}
@keyframes bob{0%{transform:translateY(-.7px) rotate(-.35deg);animation-timing-function:cubic-bezier(.36,0,.66,1)}
  31%{transform:translateY(.35px) rotate(.12deg);animation-timing-function:linear}
  47%{transform:translateY(.7px) rotate(.35deg);animation-timing-function:cubic-bezier(.3,0,.7,1)}
  68%{transform:translateY(-.2px) rotate(-.1deg);animation-timing-function:linear}
  100%{transform:translateY(-.7px) rotate(-.35deg)}}
/* The negative scaleY must be in BOTH stops or the sprite flips upright. */
@keyframes reflection{0%,100%{opacity:.13;transform:scaleY(-.46)}50%{opacity:.28;transform:scaleY(-.6)}}
@keyframes colshimmer{0%,100%{transform:scaleY(.86);opacity:.38}50%{transform:scaleY(1.14);opacity:.6}}

/* ---- falls --------------------------------------------------------------- */
.cascade{position:absolute;overflow:hidden;opacity:.21;
  -webkit-mask-image:linear-gradient(transparent,#000 16%,#000 78%,transparent);
  mask-image:linear-gradient(transparent,#000 16%,#000 78%,transparent);
  clip-path:polygon(12% 0,100% 0,89% 100%,0 100%);
  animation:fallpulse calc(var(--t)*1.9s) ease-in-out infinite}
.cascade::before{content:"";position:absolute;inset:-128px 0 0;
  background-image:url("${FALLTILE}");background-size:64px 128px;
  animation:fall calc(var(--t)*1.4s) linear infinite;will-change:transform}
.cascade.second{animation-duration:calc(var(--t)*2.9s)}
.cascade.second::before{animation-duration:calc(var(--t)*2.2s)}
@keyframes fall{to{transform:translateY(128px)}}
@keyframes fallpulse{0%,100%{opacity:.18}50%{opacity:.26}}
/* Retargeted: the shipped .spray sat at left:68%/width:15% against falls that
   are 2.7-3.3% wide, and drifted across the tower district and the hologram
   banner. `linear`, not ease — an ease curve makes the plume hesitate at the
   top of its rise, which is the sliding-gradient read being fixed. */
.spray{position:absolute;left:70.1%;top:62.6%;width:6.2%;height:5.2%;pointer-events:none;
  background:radial-gradient(ellipse at 30% 60%,#aab7ec33,transparent 58%),
             radial-gradient(ellipse at 64% 37%,#c5b9f526,transparent 62%);
  animation:plume calc(var(--t)*15s) linear infinite;will-change:transform,opacity}
.spray.b{left:68.6%;top:63.6%;animation-delay:calc(var(--t)*-7.5s)}
@keyframes plume{0%{transform:translateY(6%) scale(.86);opacity:0}
  18%{opacity:.5}55%{opacity:.42}100%{transform:translateY(-16%) scale(1.3);opacity:0}}
/* Mist rises where the painter banked it. No filter:blur() — a widened
   transparent stop gives the same softness for free, and a filter on a
   permanently animating layer is real per-frame GPU work. */
.steam{position:absolute;left:83.5%;top:43%;width:15%;height:23%;pointer-events:none;
  background:radial-gradient(ellipse at 42% 84%,#b9aee03d,transparent 66%);
  animation:rise calc(var(--t)*34s) linear infinite}
@keyframes rise{0%{transform:translateY(2%) scale(.92);opacity:0}
  18%{opacity:.38}62%{opacity:.3}100%{transform:translateY(-4.5%) scale(1.22);opacity:0}}

/* ---- traffic ------------------------------------------------------------- */
/* ONE blend operation against the city image instead of nineteen. */
.traffic{position:absolute;inset:0;mix-blend-mode:screen;pointer-events:none}
.lane{position:absolute;height:.7%;transform-origin:0 50%;overflow:visible;
  -webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;
  -webkit-mask-size:100% 100%;mask-size:100% 100%}
.car,.flyer i{position:absolute;top:50%;height:1.6px;margin-top:-.8px;border-radius:1px;
  filter:blur(.4px)}
.car{background:linear-gradient(90deg,transparent,#ffcf9e 60%,#fff3e2 82%,transparent);
  opacity:.62;width:inherit;
  animation:run calc(var(--t)*var(--ct)) linear infinite;
  animation-delay:calc(var(--t)*var(--d))}
.car.tail{background:linear-gradient(90deg,#ff5a76 8%,#ff3355 22%,transparent 70%);
  opacity:.5;animation-direction:reverse}
.flyer{position:absolute;top:0;height:100%;
  animation:run calc(var(--t)*var(--ct)) linear infinite;
  animation-delay:calc(var(--t)*var(--d))}
.flyer.rev{animation-direction:reverse}
/* An inner element bobs so the craft rides air instead of sliding on a rail. */
.flyer i{left:0;width:100%;
  background:linear-gradient(90deg,transparent,#ffb1f7 70%,#fff0fb);
  animation:bobAir calc(var(--t)*9s) ease-in-out infinite}
/* Percent translate resolves against the CAR's box, not the lane, so the travel
   distance is 100*(100+w)/w of itself. Because car length is a fraction of lane
   length, the near causeway automatically gets a longer streak than the far
   viaduct — which is correct. */
@keyframes run{to{transform:translateX(var(--tv))}}
/* px, NOT %: a percentage in translateY resolves against the element's own
   border box, and .flyer i is 1.6px tall, so the original +/-.15% moved it
   0.005px — six permanently running animations producing no pixels. */
@keyframes bobAir{0%,100%{transform:translateY(-1px)}50%{transform:translateY(1px)}}

/* ---- discrete light events ----------------------------------------------- */
/* The only non-sinusoidal motion in the scene, and the reason someone glances up
   because the city changed while they weren't looking. `linear` across these
   tight stops is what makes each step SNAP. */
.ballast{position:absolute;pointer-events:none;mix-blend-mode:screen;
  background:radial-gradient(closest-side,var(--c),transparent 75%);
  opacity:.3;will-change:opacity;
  animation:ballast calc(var(--t)*var(--bt)) linear infinite;
  animation-delay:calc(var(--t)*var(--d))}
@keyframes ballast{0%,88.9%{opacity:.30}89.0%{opacity:.04}89.25%{opacity:.44}
  89.4%{opacity:.06}89.8%{opacity:.40}90.0%{opacity:.05}90.6%{opacity:.30}100%{opacity:.30}}
/* Additive only: a patch can make a painted window brighter, never darker, so
   every event is a light coming ON and later fading out. */
.win{position:absolute;width:.28%;height:.42%;opacity:0;background:#ffb765;
  will-change:opacity;
  animation:win calc(var(--t)*var(--wt)) linear infinite;
  animation-delay:calc(var(--t)*var(--d))}
.win.cool{background:#cfe8ff;animation-timing-function:step-end}
@keyframes win{0%,.3%{opacity:0}.6%,61%{opacity:.5}61.4%,100%{opacity:0}}
.lamp{position:absolute;aspect-ratio:1;transform:translate(-50%,-50%);border-radius:50%;
  background:radial-gradient(circle,#ffb463,#ff8a3a55 40%,transparent 68%);
  filter:blur(.9px);opacity:.62;
  animation:lamp calc(var(--t)*var(--lt)) ease-in-out infinite;
  animation-delay:calc(var(--t)*var(--d))}
.lamp-streak{position:absolute;width:.35%;height:3%;transform:translateX(-50%);
  background:linear-gradient(180deg,#ff8a3a44,transparent);opacity:.62;
  animation:lamp calc(var(--t)*var(--lt)) ease-in-out infinite;
  animation-delay:calc(var(--t)*var(--d))}
@keyframes lamp{0%,100%{opacity:.45}50%{opacity:.78}}

/* ---- atmosphere ---------------------------------------------------------- */
/* .light is now a STATIC grade inside .world, so its percentages are painting
   coordinates and it crops with the image. Only the 8s oscillation was fatiguing;
   the gradients themselves tie the frame together. */
.light{position:absolute;left:8%;top:14%;width:60%;height:52%;
  opacity:calc(var(--storm)*.5);
  background:radial-gradient(ellipse at 36% 40%,#ff16a926,transparent 43%),
             radial-gradient(ellipse at 72% 54%,#30c1ff17,transparent 28%);
  mix-blend-mode:screen;pointer-events:none}
/* Four local emitters anchored on real painted sources. No emitter's swing
   exceeds .18: four glows swinging as hard as the old global throb would be the
   same sin redistributed. */
.emit{position:absolute;transform:translate(-50%,-50%);border-radius:50%;
  mix-blend-mode:screen;pointer-events:none;will-change:opacity;
  background:radial-gradient(closest-side,var(--c),transparent 72%);
  /* A declared base is REQUIRED, not cosmetic: under Reduce Motion the
     animation is removed and the element renders its declared value. With no
     opacity declared that is 1, and each emitter becomes a solid blob. The
     midpoint is the time-weighted mean of the keyframes. */
  opacity:calc((var(--lo) + var(--hi))/2);
  animation:emit calc(var(--t)*var(--et)) ease-in-out infinite;
  animation-delay:calc(var(--t)*var(--d))}
@keyframes emit{0%,100%{opacity:var(--lo)}50%{opacity:var(--hi)}}
/* Screen is justified on airlight because it can never darken: a wash
   compositing 24/7 must not be able to muddy the painting's blacks. The falls
   band is condensate, not airlight, so it uses normal alpha and RISES. */
.haze{position:absolute;pointer-events:none;mix-blend-mode:screen}
.haze.h{left:-6%;width:112%;top:26%;height:9%;opacity:calc(var(--storm)*.78);
  background:linear-gradient(transparent,#e9a6b412 40%,transparent);
  animation:haze-h calc(var(--t)*173s) linear infinite}
.haze.m{left:-6%;width:112%;top:40%;height:18%;opacity:calc(var(--storm)*.7);
  background:linear-gradient(transparent,#8fa0d80d 50%,transparent);
  animation:haze-m calc(var(--t)*127s) linear infinite}
.haze.f{left:60%;width:22%;top:50%;height:16%;opacity:calc(var(--storm)*.68);mix-blend-mode:normal;
  background:radial-gradient(ellipse at 50% 80%,#a9a7c414,transparent 65%);
  animation:haze-f calc(var(--t)*71s) linear infinite}
@keyframes haze-h{
  0%{transform:translateX(-3%);opacity:calc(var(--storm)*.70);animation-timing-function:cubic-bezier(.4,0,.7,1)}
  41%{transform:translateX(3%);opacity:calc(var(--storm)*.85);animation-timing-function:linear}
  67%{transform:translateX(.4%);opacity:calc(var(--storm)*.76);animation-timing-function:cubic-bezier(.3,0,.6,1)}
  100%{transform:translateX(-3%);opacity:calc(var(--storm)*.70)}}
@keyframes haze-m{
  0%{transform:translateX(2%);opacity:calc(var(--storm)*.60);animation-timing-function:cubic-bezier(.35,0,.7,1)}
  37%{transform:translateX(-2%);opacity:calc(var(--storm)*.80);animation-timing-function:linear}
  72%{transform:translateX(.6%);opacity:calc(var(--storm)*.67);animation-timing-function:cubic-bezier(.3,0,.65,1)}
  100%{transform:translateX(2%);opacity:calc(var(--storm)*.60)}}
@keyframes haze-f{
  0%{transform:translateY(0);opacity:calc(var(--storm)*.55);animation-timing-function:cubic-bezier(.3,0,.75,1)}
  46%{transform:translateY(-15%);opacity:calc(var(--storm)*.80);animation-timing-function:linear}
  74%{transform:translateY(-6%);opacity:calc(var(--storm)*.64);animation-timing-function:cubic-bezier(.3,0,.6,1)}
  100%{transform:translateY(0);opacity:calc(var(--storm)*.55)}}

/* ---- rain ---------------------------------------------------------------- */
/* -25vh, not -22%: the bleed must scale with HEIGHT because the skew displaces
   proportional to height. With a width-proportional bleed the corners go bare
   on any tall display once the gust reaches -22deg. */
.rain{position:absolute;inset:-80px -25vh;pointer-events:none;
  -webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;
  -webkit-mask-size:100% 100%;mask-size:100% 100%;
  transform:skewX(-9deg);
  animation:gust calc(var(--t)*47s) linear infinite}
.rain::before{content:"";position:absolute;inset:-1536px 0 0;background-size:1536px 1536px;
  /* The fallback is load-bearing, not defensive style. A .rain variant that
     omits --speed makes this SHORTHAND invalid-at-computed-value-time, which
     silently resets every longhand it sets — animation-name included — and
     that layer's drops freeze while the rule still looks live in DevTools. */
  animation:rainfall-lg var(--speed,calc(var(--t)*4.6s)) linear infinite;
  will-change:transform}
/* Arrival fast, decay slow. A symmetric sine here would be another breath, not
   wind. Propagated front-to-back so the shear reaches the distance first. */
@keyframes gust{0%{transform:skewX(-9deg)}9%{transform:skewX(-20deg)}16%{transform:skewX(-22deg)}
  44%{transform:skewX(-13deg)}72%{transform:skewX(-7deg)}100%{transform:skewX(-9deg)}}
@keyframes gust-near{0%{transform:skewX(-12deg)}9%{transform:skewX(-23deg)}16%{transform:skewX(-25deg)}
  44%{transform:skewX(-16deg)}72%{transform:skewX(-10deg)}100%{transform:skewX(-12deg)}}
@keyframes rainfall-lg{to{transform:translate3d(0,1536px,0)}}
@keyframes rainfall-sm{to{transform:translate3d(0,768px,0)}}

.rain.far{opacity:.15;--speed:calc(var(--t)*5.8s);animation-delay:calc(var(--t)*-2.8s),0s;
  animation-name:gust,squall-a;animation-duration:calc(var(--t)*47s),calc(var(--t)*79s);
  animation-timing-function:linear,ease-in-out;animation-iteration-count:infinite,infinite;
  -webkit-mask-image:linear-gradient(180deg,#000 0 46%,#0007 74%,transparent 96%);
  mask-image:linear-gradient(180deg,#000 0 46%,#0007 74%,transparent 96%)}
.rain.far::before{inset:-768px 0 0;background-size:768px 768px;
  background-image:url("${RAIN_FAR}");animation-name:rainfall-sm}
.rain.mid{opacity:.31;--speed:calc(var(--t)*4.4s);animation-delay:calc(var(--t)*-1.4s),0s;
  animation-name:gust,squall-b;animation-duration:calc(var(--t)*47s),calc(var(--t)*97s);
  animation-timing-function:linear,ease-in-out;animation-iteration-count:infinite,infinite;
  -webkit-mask-image:linear-gradient(180deg,#0005 0 10%,#000 42% 88%,#0008 100%);
  mask-image:linear-gradient(180deg,#0005 0 10%,#000 42% 88%,#0008 100%)}
.rain.mid::before{background-image:url("${RAIN_MID}")}
/* Near rain is absent from the sky entirely: 1.5px near-plane drops falling
   across the painted sun read as dirt on the lens. Its defocus is baked into
   the tile, never applied with filter:blur() — a filter here would re-apply
   every frame forever, on battery. */
.rain.near{opacity:.30;--speed:calc(var(--t)*4.6s);
  animation-name:gust-near,squall-c;animation-duration:calc(var(--t)*47s),calc(var(--t)*113s);
  animation-timing-function:linear,ease-in-out;animation-iteration-count:infinite,infinite;
  -webkit-mask-image:linear-gradient(180deg,transparent 0 22%,#000 58%);
  mask-image:linear-gradient(180deg,transparent 0 22%,#000 58%)}
.rain.near::before{background-image:url("${RAIN_NEAR}")}
/* Lamp-throw rain. A TALL ellipse — a lamp throw is a cone, not a puddle of
   light. Lives inside .world so its mask percentage is in painting space. */
/* Its own envelope, not squall-c: an animation on `opacity` overrides the
   declared base outright, so borrowing .rain.near's squall would render this
   lamp throw at .16-.32 instead of the .13 it is specified at — twice as bright
   as intended. Same shape and period, scaled to its own range. */
.rain.warm{position:absolute;inset:auto;left:26%;top:64%;width:14%;height:26%;opacity:.13;
  /* Uses the near tile geometry and sits at near depth, so it falls at the
     near layer's rate. */
  --speed:calc(var(--t)*4.6s);
  animation-name:gust-near,squall-warm;animation-duration:calc(var(--t)*47s),calc(var(--t)*113s);
  animation-timing-function:linear,ease-in-out;animation-iteration-count:infinite,infinite;
  -webkit-mask-image:radial-gradient(ellipse 50% 60% at 50% 55%,#000 0 30%,transparent 78%);
  mask-image:radial-gradient(ellipse 50% 60% at 50% 55%,#000 0 30%,transparent 78%)}
.rain.warm::before{inset:-1536px 0 0;background-image:url("${RAIN_WARM}")}
/* Three differently SHAPED envelopes, not one curve at three speeds. */
@keyframes squall-a{0%,100%{opacity:.13}41%{opacity:.27}67%{opacity:.18}}
@keyframes squall-b{0%,100%{opacity:.22}29%{opacity:.38}58%{opacity:.26}81%{opacity:.34}}
@keyframes squall-c{0%,100%{opacity:.16}53%{opacity:.32}76%{opacity:.21}}
@keyframes squall-warm{0%,100%{opacity:.09}53%{opacity:.17}76%{opacity:.12}}

/* ---- the storm clock ----------------------------------------------------- */
/* 433 is prime. 437 = 19x23 and 23 is already a period in this file, so they
   would phase-lock once per cycle — the opposite of the intent.
   Two clocks on two elements so nothing silently cancels: the squalls animate
   each .rain layer's own opacity, the storm animates the wrappers. */
.storm-rain-wrap{position:absolute;inset:0;pointer-events:none;
  animation:storm-haze calc(var(--t)*433s) ease-in-out infinite}
@keyframes storm-haze{0%,100%{opacity:.75}38%{opacity:1}64%{opacity:.85}}
/* The rain layers above blend normally, so wrapping them in an opacity
   animation is harmless. .light and the haze bands do NOT: an element with an
   opacity animation is an isolated group, and mix-blend-mode inside it can no
   longer see the painting. Driving a registered custom property instead leaves
   the wrapper fully opaque and un-isolated, so their screen blends still reach
   the backdrop. The initial value is the time-weighted mean, which makes the
   Reduce-Motion still correct for free. */
@property --storm{syntax:"<number>";inherits:true;initial-value:0.85}
.storm-wrap{position:absolute;inset:0;pointer-events:none;
  animation:storm-var calc(var(--t)*433s) ease-in-out infinite}
@keyframes storm-var{0%,100%{--storm:.75}38%{--storm:1}64%{--storm:.85}}
/* Normal alpha, not soft-light: the corners measure luminance 10.7-48.4 against
   a 255 peak, and soft-light over near-black barely moves them — so it fails at
   the one thing a squall look requires, lifting blacks. */
.grade{position:fixed;inset:0;pointer-events:none;
  background:linear-gradient(#141a3a,#2a1030);opacity:.05;
  animation:storm calc(var(--t)*433s) ease-in-out infinite}
@keyframes storm{0%,100%{opacity:.05}38%{opacity:.16}64%{opacity:.09}}

/* Lightning. The ellipse radii are sized so the gradient reaches transparent
   INSIDE the element box: a radius that overruns the box gets clipped by the
   box edge and draws a hard horizontal line across the sky.
   Gated to the storm peak, masked inside the world so it crops with
   the painting, and deliberately soft: a wallpaper rewards a glance, it must
   never demand one. Two flashes per 433s cycle, alternating 196s and 237s
   apart, each a 4.3s event whose visible energy is front-loaded into the first
   ~0.5s, at an amplitude that lifts the cloud bank rather than strobing the
   desktop. */
.bolt{position:absolute;left:0;width:100%;top:0;height:44%;pointer-events:none;
  mix-blend-mode:screen;opacity:0;
  background:radial-gradient(ellipse 58% 56% at 62% 46%,#cfd6ff,transparent 76%);
  -webkit-mask-image:linear-gradient(to bottom,#000 62%,transparent);
  mask-image:linear-gradient(to bottom,#000 62%,transparent);
  animation:bolt calc(var(--t)*433s) linear infinite}
.bolt.b{background:radial-gradient(ellipse 46% 50% at 28% 52%,#e6dcff,transparent 78%);
  animation-delay:calc(var(--t)*-196s)}
@keyframes bolt{0%,35.9%{opacity:0}36.05%{opacity:.36}36.3%{opacity:.07}
  36.5%{opacity:.26}36.9%{opacity:0}100%{opacity:0}}

/* ---- frame --------------------------------------------------------------- */
/* Upper-right only. That corner is the BRIGHTER of the two top corners (45.8 vs
   38.5) and lacks a dark repoussoir mass, so darkening it creates contrast. A
   lower-left lobe would eat the wet-promenade reflections — the best passage in
   the painting. */
.frame{position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 55% 45% at 92% 4%,#12082466,transparent 70%)}
/* Screen-space, static, three stops per band — a 2-stop ramp over ~90px
   Mach-bands across the smooth dark sky. No blend mode: any blend here drags
   .light's screen group into a per-frame full-viewport flatten. */
.chrome{position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(to bottom,#0a082047 0,#0a08201f 2.6%,transparent 6.5%),
             linear-gradient(to top,#0a08201f 0,#0a082014 3.5%,transparent 9%)}

/* ---- crop discipline ----------------------------------------------------- */
/* Past 1.85:1 the world stops growing with the viewport and is pillarboxed
   against a 64x43 plate of itself — the browser's upscale IS the blur, so no
   filter pass is needed. Without this an ultrawide throws the entire sky, the
   sun and the focal column off the top; with it the whole painting survives and
   the animated area SHRINKS on the widest, most expensive displays. */
.pillar{position:absolute;inset:0;background:var(--city-blur) center/cover;
  filter:brightness(.42) saturate(.65);transform:scale(1.08)}
/* .world is bottom-anchored, so every pixel of overflow is thrown off the TOP:
   6.25% at 16:10, 15.6% at 16:9, 35.7% at 21:9. The painted sun ends up jammed
   under the menu bar on a 4K external. Split the overflow instead. */
@container (min-aspect-ratio:3/2) and (max-aspect-ratio:185/100){
  .world{bottom:calc(-1 * min(.9cqh,(66.67cqw - 100cqh) * .3))}}
@container (min-aspect-ratio:185/100){
  /* At this width the world's height is exactly 100cqh, so the painting fills
     the camera box vertically and the drift keeps its overscan. */
  .world{width:150cqh;box-shadow:0 0 140px 60px #0a0820}}

/* ---- states -------------------------------------------------------------- */
.paused *,.paused *::before,.paused *::after{animation-play-state:paused!important}

/* The accessible path was the worst frame in the file: dimmer than every frame
   of the animated path, and it deleted the rain from a wallpaper called Rain on
   the River. Frozen values are time-weighted MEANS, not floors. */
@media(prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none!important}
  .rain.mid,.rain.near,.rain.warm{display:none}
  .rain.far{opacity:.17}
  .rain.far::before{transform:translate3d(0,384px,0)}
  .sp,.ballast,.win,.traffic,.bolt{display:none}
  .light{opacity:.68}
  .haze.h{opacity:.78}.haze.m{opacity:.70}.haze.f{opacity:.68}
  .spray{opacity:.32}.spray.b{opacity:.26}
  .steam{opacity:.24}
  .bloom-wrap{opacity:.22}
  .sunpath{opacity:.8}
  .grade{opacity:.09}
  .boat-reflection{opacity:.18}
}
''')

DOC = Template('''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Neon Horizon — Rain on the River</title>
<!--
  Neon Horizon, animated wallpaper. One self-contained file: no network, no
  audio, no tracking. Pauses when the host reports the page hidden and honours
  Reduce Motion.

  Load index.html#calm to run every animation at one third speed for battery.
  Pair it with Plash's own deactivate-on-battery setting.

  Regenerate with: python3 build/build.py   (see build/scene.py for the rules)
-->
<style>$CSS</style></head>
<body>
<main class="scene" aria-label="A cyberpunk city at dusk in the rain: traffic crosses the bridges, rain lands across the wet promenade and the river, the sun's reflection shifts on the water, and boats move downstream">
<div class="pillar"></div>
<div class="camera"><div class="world">
<div class="city"></div>
<div class="bloom-wrap"><div class="bloom"></div></div>
<div class="plane-near"><div class="wet">$IMPACT</div>$SMEARS</div>
<div class="wet river">$RIVER</div>
$GLINTS
<div class="sunpath"><div class="glit"></div><div class="glit b"></div></div>
$BOATS
<div class="cascade" style="left:70.3%;top:52.2%;width:2.7%;height:12%"></div>
<div class="cascade second" style="left:73.2%;top:52%;width:3.3%;height:14%"></div>
<div class="spray"></div><div class="spray b"></div>
<div class="steam"></div>
<div class="traffic">$TRAFFIC</div>
$LAMPS
$BALLAST
$WINDOWS
$EMITTERS
<div class="bolt"></div><div class="bolt b"></div>
<div class="storm-wrap">
<div class="light"></div>
<div class="haze h"></div><div class="haze m"></div><div class="haze f"></div>
</div>
<div class="rain warm"></div>
</div></div>
<div class="storm-rain-wrap">
<div class="rain far"></div><div class="rain mid"></div><div class="rain near"></div>
</div>
<div class="frame"></div><div class="chrome"></div>
</main>
<div class="grade"></div>
<script>
function syncVisibility(){document.body.classList.toggle('paused',document.hidden)}
document.addEventListener('visibilitychange',syncVisibility);syncVisibility();
if(location.hash==='#calm')document.body.classList.add('calm');
</script>
</body></html>
''')
