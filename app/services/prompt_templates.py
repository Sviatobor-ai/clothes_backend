"""Prompt templates and randomization utilities for the leatherwear assistant."""

from __future__ import annotations

import random
from typing import Iterable, Sequence

ASSISTANT_SYSTEM = """
You are a fashion prompt generator specialized in SFW women’s leatherwear. Produce exactly one polished text-to-image prompt per request. Describe both the clothing and the model in a neutral, tasteful way, covering materials, construction, silhouette, details, and the model’s attitude, pose, hair, and makeup. Keep the framing vertical portrait with the full outfit visible; suggest a 1024×1536 target size when relevant. Avoid brand names and copyrighted characters. Stay SFW with no nudity and no minors. Prefer concrete, material-centric vocabulary, such as leather types, finishes, stitching, hardware, closures, fit, and drape. Lighting and camera hints like soft daylight, an 85 mm lens look, or shallow depth of field are welcome. Output only the final prompt text with no preamble or markdown.
""".strip()

SILHOUETTES: Sequence[str] = (
    "tailored leather suit with sharp shoulders",
    "structured trench coat with cinched waist",
    "sleek bodycon midi dress",
    "A-line leather mini dress",
    "fitted sheath dress with paneled leather",
    "biker jacket paired with high-waist mini skirt",
    "corset top layered over high-waist pencil skirt",
    "streamlined leather jumpsuit",
    "peplum jacket with tapered trousers",
    "sculpted moto jacket over column skirt",
)

GARMENTS: Sequence[str] = (
    "double-breasted trench coat",
    "tailored blazer",
    "structured corset",
    "panelled bodycon dress",
    "wrap dress",
    "high-waist pencil skirt",
    "tapered trousers",
    "mini skirt",
    "moto jacket",
    "fitted sheath dress",
)

LEATHER_TYPES: Sequence[str] = (
    "full-grain leather with a soft matte finish",
    "buttery aniline leather",
    "semi-aniline leather with gentle sheen",
    "patent leather with mirror gloss",
    "high-gloss lacquered leather",
    "pebble-grain leather",
    "nubuck leather",
    "velvety suede leather",
    "embossed crocodile leather",
    "embossed snakeskin leather",
)

COLORS: Sequence[str] = (
    "deep black",
    "oxblood red",
    "cognac brown",
    "forest green",
    "midnight blue",
    "ivory",
    "steel grey",
    "charcoal",
    "deep burgundy",
    "ink navy",
)

DETAILING: Sequence[str] = (
    "hand-stitched seams",
    "tonal topstitching",
    "corsetry boning channels",
    "lace-up side panels",
    "quilted shoulder panels",
    "articulated sleeves",
    "asymmetric front zip",
    "polished rivet hardware",
    "matte snap buttons",
    "belt with statement buckle",
)

ACCESSORIES: Sequence[str] = (
    "structured mini bag",
    "sleek leather gloves",
    "minimal choker",
    "thin waist belt",
    "polished metallic cuff",
    "delicate drop earrings",
)

FOOTWEAR: Sequence[str] = (
    "ankle boots",
    "knee-high boots",
    "over-the-knee boots",
    "heeled sandals with leather straps",
    "block-heel boots",
)

MODEL_DESCRIPTORS: Sequence[str] = (
    "poised expression",
    "confident stance",
    "calm gaze",
    "sleek low ponytail",
    "soft waves",
    "chin-length bob",
    "natural glow makeup",
    "classic eyeliner",
    "soft matte lips",
    "defined cheekbones",
)

POSES: Sequence[str] = (
    "three-quarter stance",
    "contrapposto pose",
    "walking stride",
    "seated edge pose with straight posture",
    "mid-step turn",
)

SCENES: Sequence[str] = (
    "studio seamless backdrop",
    "concrete loft interior",
    "minimal set with textured wall",
    "moody runway reflection",
    "modern city rooftop",
    "architectural atrium",
)

LIGHTING: Sequence[str] = (
    "soft daylight glow",
    "moody chiaroscuro lighting",
    "rim light accent",
    "diffused key light",
    "golden-hour backlight",
)

CAMERA: Sequence[str] = (
    "vertical portrait framing",
    "85 mm lens look",
    "shallow depth of field",
    "subtle film grain",
    "fine-grain medium format look",
)

MOODS: Sequence[str] = (
    "elevated mood",
    "modern and refined",
    "bold yet composed",
    "sculptural elegance",
    "minimalist confidence",
)


def _sample(items: Sequence[str], *, k: int) -> list[str]:
    if k <= 0:
        return []
    k = min(k, len(items))
    return random.sample(list(items), k=k)


def _choose(items: Sequence[str]) -> str:
    return random.choice(list(items))


def _select_lighting(leather: str) -> str:
    dramatic_keywords = ("patent", "high-gloss", "mirror gloss", "lacquered")
    if any(keyword in leather for keyword in dramatic_keywords):
        dramatic_lighting = [
            option
            for option in LIGHTING
            if "chiaroscuro" in option or "rim light" in option or "backlight" in option
        ]
        if dramatic_lighting:
            return random.choice(dramatic_lighting)
    return _choose(LIGHTING)


def _select_scene(leather: str) -> str:
    dramatic_keywords = ("patent", "high-gloss", "mirror gloss", "lacquered")
    if any(keyword in leather for keyword in dramatic_keywords):
        reflective_scenes = [
            option for option in SCENES if "runway" in option or "rooftop" in option
        ]
        if reflective_scenes:
            return random.choice(reflective_scenes)
    return _choose(SCENES)


def _build_layering_note(garments: Iterable[str]) -> str:
    for garment in garments:
        if "corset" in garment.lower():
            return (
                "Layer the corset over a fitted base or under a structured blazer to maintain a tasteful, SFW presentation."
            )
    return ""


def build_randomized_user_prompt() -> str:
    silhouette = _choose(SILHOUETTES)
    garment_count = 1 if random.random() < 0.5 else 2
    garments = _sample(GARMENTS, k=garment_count)
    leather = _choose(LEATHER_TYPES)
    color = _choose(COLORS)
    detailing = _sample(DETAILING, k=2)
    accessories = _sample(ACCESSORIES, k=1)
    footwear = _choose(FOOTWEAR)
    model_descriptors = _sample(MODEL_DESCRIPTORS, k=2)
    pose = _choose(POSES)
    scene = _select_scene(leather)
    lighting = _select_lighting(leather)
    camera = _sample(CAMERA, k=2)
    mood = _choose(MOODS)

    layering_note = _build_layering_note(garments)

    if "trench" in silhouette or any("trench" in garment.lower() for garment in garments):
        mood = "modern and refined"

    prompt_parts = [
        "Generate exactly one SFW text-to-image prompt in English for a women's leather outfit.",
        f"Silhouette focus: {silhouette}.",
        f"Primary garments: {', '.join(garments)}.",
        f"Leather material emphasis: {leather} in {color}.",
        f"Detailing cues: {', '.join(detailing)}.",
        f"Accessories: {', '.join(accessories)}." if accessories else "",
        f"Footwear: {footwear}.",
        f"Model styling notes: {', '.join(model_descriptors)}.",
        f"Pose direction: {pose}.",
        f"Scene inspiration: {scene}.",
        f"Lighting direction: {lighting}.",
        f"Camera and framing: {', '.join(camera)}.",
        f"Overall mood: {mood}.",
        layering_note,
        (
            "Ensure the final prompt highlights leather as the central material, keeps everything SFW, and avoids brand names or copyrighted references."
        ),
        (
            "State clearly that the composition uses vertical portrait framing with the full outfit visible and evokes a 1024x1536 aspect ratio feel."
        ),
        "Include vivid yet concise sensory cues about texture, stitching, and movement without exceeding roughly 150 words.",
        "Output only the final polished prompt text with no lists, headings, or quotation marks.",
    ]

    filtered_parts = [part for part in prompt_parts if part]
    return " ".join(filtered_parts)
