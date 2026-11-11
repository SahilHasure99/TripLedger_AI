# Design System & Motion Guide

## Tokens (inherited from the original TravelMate UI)
`--ink #142d29` · `--green #1f5748` · `--mint #e9f2e9` · `--paper #faf9f5` · `--gold #d7aa65`
**Accent palette added for the motion layer:** aqua `#14b8a6` · violet `#8b5cf6` · peach `#fb923c` · lime `#a3e635` · pink `#f472b6`.
Type: *Playfair Display* (display) + *DM Sans* (UI).

## Motion principles
1. **Purposeful** – animate state change, hierarchy and affordance, not decoration alone.
2. **Fast & springy** – one easing curve `cubic-bezier(.22,1,.36,1)`; entrances 0.45–0.7 s.
3. **Never block** – nothing waits on an animation to be usable.
4. **Accessible** – every animation is disabled under `prefers-reduced-motion`.

## Catalogue (`ui/theme.py`)
| Effect | Where | Technique |
|---|---|---|
| Aurora mesh background + film grain | whole app | fixed blurred radial gradients, SVG noise |
| Scroll-driven reveal | cards, stats, bento | `animation-timeline: view()` with load-time fallback |
| Animated gradient text | hero highlight, sidebar brand, page titles | `background-clip:text` + shifting gradient |
| Light-sweep hero | home hero | moving linear-gradient overlay |
| Lift + tilt + zoom cards | destinations, categories, features | transform + background-size |
| Shine-sweep, press-feedback buttons | all buttons | `::after` skewed gradient, `:active scale` |
| Glass sidebar, pill nav | sidebar | `backdrop-filter`, `:has(input:checked)` |
| Marquee ticker | home | duplicated track, `translateX(-50%)` loop, pause on hover |
| Count-up stats | home | `@property` integer animation (static fallback) |
| Bento grid with bobbing icons | home | CSS grid spans |
| Live status dot / sticker | sidebar, API health | ping keyframes |

## Browser support
Chromium/Edge/Safari: full effect. Firefox: scroll-driven reveals and count-up fall back to simple fades / static numbers. All content is readable without any animation.

## Adding a new animated component
1. Reuse tokens + easing; 2. add the selector to the reveal list in `theme.py`; 3. add it to the reduced-motion block; 4. escape any dynamic text with `html.escape`.
