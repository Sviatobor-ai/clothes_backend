"""Prompt templates and randomization utilities for the leatherwear assistant."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

ASSISTANT_SYSTEM = """
You are a fashion prompt generator specialized in tasteful, SFW women’s leatherwear. Provide exactly one vivid text-to-image prompt for each request. Describe the outfit, the model, and the scene with an editorial tone that highlights leather materials, textures, construction, and styling details. Mention pose, lighting, and camera mood without dictating rigid settings. Avoid brand names and copyrighted characters. Keep every depiction mature and safe-for-work. Respond with a single paragraph of plain text and no additional framing.
""".strip()


@dataclass(frozen=True)
class WeightedItem:
    """Simple helper structure for weighted random selection."""

    value: str
    weight: float = 1.0


def _weighted_choice(options: Sequence[WeightedItem]) -> str:
    weights = [max(option.weight, 0.0) for option in options]
    if not any(weights):
        weights = [1.0] * len(options)
    return random.choices([option.value for option in options], weights=weights, k=1)[0]


def _weighted_sample(options: Sequence[WeightedItem], *, k: int) -> list[str]:
    k = max(0, min(k, len(options)))
    pool = list(options)
    selected: list[str] = []
    for _ in range(k):
        choice = _weighted_choice(pool)
        selected.append(choice)
        pool = [item for item in pool if item.value != choice]
        if not pool:
            break
    return selected


HEADWEAR = (
    WeightedItem("a sculpted leather beret", 1.0),
    WeightedItem("a structured leather cap", 0.9),
    WeightedItem("a softly draped hood", 0.7),
    WeightedItem("a cropped leather flight hood", 0.4),
    WeightedItem("no headwear", 1.5),
    WeightedItem("a ribbed knit beanie with leather piping", 0.5),
)

HAIR = (
    WeightedItem("sleek low ponytail", 1.1),
    WeightedItem("soft brushed-out waves", 1.2),
    WeightedItem("sharp blunt bob", 0.9),
    WeightedItem("braided crown", 0.7),
    WeightedItem("wet-look sculpted hair", 0.6),
    WeightedItem("glossy side-parted lob", 0.8),
)

NECKLINES = (
    WeightedItem("turtleneck"),
    WeightedItem("stand collar"),
    WeightedItem("notch lapel"),
    WeightedItem("shawl collar"),
    WeightedItem("mandarin collar"),
    WeightedItem("halter neckline", 0.7),
    WeightedItem("sweetheart neckline", 0.8),
)

OUTERWEAR = (
    WeightedItem("cropped biker jacket"),
    WeightedItem("tailored blazer with structured shoulders"),
    WeightedItem("storm-flap trench coat", 0.9),
    WeightedItem("belted trench coat with epaulets", 0.8),
    WeightedItem("flying jacket with shearling lining", 0.6),
    WeightedItem("minimalist leather duster", 0.5),
    WeightedItem("no outer layer", 1.2),
)

CORSETRY = (
    WeightedItem("structured corset"),
    WeightedItem("contoured bustier"),
    WeightedItem("sleek waist cincher"),
    WeightedItem("leather harness"),
    WeightedItem("boned bustier top"),
)

TOPS = (
    WeightedItem("fitted leather shirt"),
    WeightedItem("ribbed knit underlayer"),
    WeightedItem("camisole with leather trim", 0.8),
    WeightedItem("matte leather bodysuit"),
    WeightedItem("structured bustier top"),
    WeightedItem("tube top with leather edging", 0.6),
)

DRESSES = (
    WeightedItem("sheath dress"),
    WeightedItem("A-line mini dress"),
    WeightedItem("pencil midi dress"),
    WeightedItem("slip-inspired dress with tonal lining"),
    WeightedItem("wrap dress"),
    WeightedItem("panelled shirt dress"),
)

BOTTOMS = (
    WeightedItem("high-waist pencil skirt"),
    WeightedItem("A-line skirt"),
    WeightedItem("knife-pleated skirt"),
    WeightedItem("tailored trousers"),
    WeightedItem("cigarette pants"),
    WeightedItem("flared trousers"),
    WeightedItem("opaque leather leggings", 0.8),
)

HOSIERY = (
    WeightedItem("opaque tights"),
    WeightedItem("fishnet underlayer tights", 0.6),
    WeightedItem("thigh-high socks", 0.7),
    WeightedItem("leather-paneled leggings", 0.5),
    WeightedItem("no hosiery", 1.1),
)

FOOTWEAR = (
    WeightedItem("ankle boots"),
    WeightedItem("knee-high boots"),
    WeightedItem("over-the-knee boots"),
    WeightedItem("platform boots"),
    WeightedItem("heeled sandals with leather straps"),
    WeightedItem("pointed-toe pumps"),
)

GLOVES_AND_SMALL_GOODS = (
    WeightedItem("opera-length gloves", 0.6),
    WeightedItem("sleek driving gloves", 0.8),
    WeightedItem("fingerless gloves", 0.5),
    WeightedItem("structured mini bag"),
    WeightedItem("belt bag with polished hardware"),
)

ACCESSORIES = (
    WeightedItem("slim belt with a statement buckle"),
    WeightedItem("choker necklace"),
    WeightedItem("cuff bracelet"),
    WeightedItem("layered chain necklaces"),
    WeightedItem("minimal drop earrings"),
    WeightedItem("sculptural ear cuffs", 0.6),
)

LEATHER_FINISHES = (
    WeightedItem("full-grain leather with a softly burnished surface"),
    WeightedItem("top-grain leather with subtle sheen"),
    WeightedItem("aniline leather that feels plush"),
    WeightedItem("semi-aniline leather with a gentle glow"),
    WeightedItem("patent leather with high-gloss reflectivity", 0.7),
    WeightedItem("lacquered leather with mirror shine", 0.5),
    WeightedItem("matte nubuck leather"),
    WeightedItem("buttery nappa leather"),
    WeightedItem("pebble-grain leather"),
    WeightedItem("suede with velvety touch"),
    WeightedItem("embossed crocodile leather"),
    WeightedItem("embossed snakeskin leather"),
    WeightedItem("embossed lizard texture", 0.7),
    WeightedItem("quilted leather panels", 0.6),
    WeightedItem("perforated leather sections", 0.5),
)

COLOR_PALETTE = (
    WeightedItem("deep black"),
    WeightedItem("oxblood"),
    WeightedItem("cognac"),
    WeightedItem("forest green"),
    WeightedItem("midnight blue"),
    WeightedItem("ivory"),
    WeightedItem("charcoal"),
    WeightedItem("steel gray"),
    WeightedItem("burgundy"),
    WeightedItem("bone"),
    WeightedItem("camel"),
)

HARDWARE = (
    WeightedItem("two-way zipper"),
    WeightedItem("asymmetric zip"),
    WeightedItem("polished D-rings"),
    WeightedItem("snap closures"),
    WeightedItem("riveted straps"),
    WeightedItem("hook-and-eye set"),
    WeightedItem("grommet lacing"),
    WeightedItem("buckled tabs"),
)

DETAILING = (
    WeightedItem("precise paneling"),
    WeightedItem("contoured darting"),
    WeightedItem("corsetry boning"),
    WeightedItem("lacing that cinches the waist"),
    WeightedItem("pick-stitched edges"),
    WeightedItem("tonal topstitching"),
    WeightedItem("quilted channels"),
    WeightedItem("piping that traces the seams"),
    WeightedItem("welt pockets"),
    WeightedItem("vent detailing"),
    WeightedItem("articulated sleeves"),
    WeightedItem("storm flaps"),
    WeightedItem("gusset inserts"),
)

FIT_AND_SILHOUETTE = (
    WeightedItem("tailored silhouette"),
    WeightedItem("bodycon fit"),
    WeightedItem("relaxed drape", 0.8),
    WeightedItem("boxy proportion", 0.6),
    WeightedItem("cinched waist"),
    WeightedItem("hourglass emphasis"),
    WeightedItem("column line"),
    WeightedItem("A-line flare"),
    WeightedItem("flared hem"),
    WeightedItem("structured shoulders"),
)

POSES = (
    WeightedItem("a confident contrapposto pose"),
    WeightedItem("a mid-turn movement"),
    WeightedItem("a walking stride"),
    WeightedItem("a seated edge pose"),
    WeightedItem("a hand-in-pocket stance"),
    WeightedItem("an adjusting-the-lapel gesture", 0.8),
)

SCENES = (
    WeightedItem("studio seamless backdrop"),
    WeightedItem("textured plaster wall"),
    WeightedItem("concrete loft interior"),
    WeightedItem("moody runway reflection"),
    WeightedItem("city rooftop at dusk"),
    WeightedItem("modern corridor"),
    WeightedItem("gallery space"),
)

LIGHTING = (
    WeightedItem("soft daylight"),
    WeightedItem("rim light accents"),
    WeightedItem("moody chiaroscuro"),
    WeightedItem("diffused key light"),
    WeightedItem("subtle backlight glow"),
)

CAMERA_AND_LENS = (
    WeightedItem("85mm portrait perspective"),
    WeightedItem("gentle film grain"),
    WeightedItem("shallow depth of field"),
    WeightedItem("medium-format clarity"),
    WeightedItem("slight motion blur"),
)

STYLE_DIRECTION = (
    WeightedItem("minimalist"),
    WeightedItem("sculptural"),
    WeightedItem("refined"),
    WeightedItem("bold"),
    WeightedItem("modern noir"),
    WeightedItem("neo-romantic"),
    WeightedItem("cyber-chic"),
    WeightedItem("retro-futurist"),
    WeightedItem("utility-luxe"),
)


def _needs_polished_layers(outerwear: str) -> bool:
    return "trench" in outerwear or "tailored" in outerwear


def _select_finish() -> tuple[str, bool]:
    finish = _weighted_choice(LEATHER_FINISHES)
    dramatic = any(keyword in finish for keyword in ("patent", "lacquer", "high-gloss", "mirror"))
    return finish, dramatic


def _select_lighting(dramatic_finish: bool) -> str:
    if dramatic_finish:
        dramatic_choices = [item for item in LIGHTING if "rim" in item.value or "moody" in item.value or "backlight" in item.value]
        if dramatic_choices:
            return _weighted_choice(dramatic_choices)
    return _weighted_choice(LIGHTING)


def _select_scene(dramatic_finish: bool) -> str:
    if dramatic_finish:
        reflective_choices = [item for item in SCENES if "runway" in item.value or "rooftop" in item.value]
        if reflective_choices and random.random() < 0.6:
            return _weighted_choice(reflective_choices)
    return _weighted_choice(SCENES)


def _select_primary_layers(polished: bool) -> dict[str, str]:
    outfit_plan: dict[str, str] = {}
    if random.random() < 0.45:
        dress = _weighted_choice(DRESSES)
        neckline = _weighted_choice(NECKLINES)
        outfit_plan["dress"] = f"{dress} with a {neckline}"
    else:
        top = _weighted_choice(TOPS)
        if polished and "tube" in top:
            top = "matte leather bodysuit"
        neckline = _weighted_choice(NECKLINES)
        outfit_plan["top"] = f"{top} featuring a {neckline}"
        bottom = _weighted_choice(BOTTOMS)
        outfit_plan["bottom"] = bottom
    return outfit_plan


def _maybe_add_corsetry(polished: bool, outerwear: str, layers: dict[str, str]) -> str | None:
    if random.random() < 0.55:
        corset = _weighted_choice(CORSETRY)
        if polished and "harness" in corset:
            corset = "structured corset"
        base_reference = "dress" if "dress" in layers else "top"
        if outerwear != "no outer layer" and random.random() < 0.6:
            return f"a {corset} cinched over the {layers[base_reference]} and anchored beneath the {outerwear}"
        fitted_phrase = random.choice(("over a fitted base layer", "over a fine-gauge knit", "over the tonal underlayer"))
        if base_reference == "dress":
            return f"a {corset} defining the waist {fitted_phrase}"
        return f"a {corset} layered {fitted_phrase}"
    return None


def _build_layer_sentences(layers: dict[str, str], outerwear: str, corsetry: str | None, finish: str, color: str, detailing: list[str], hardware: list[str], fit: str) -> list[str]:
    sentences: list[str] = []
    waist_synonym = random.choice(("cinched waist", "waist emphasis", "belted silhouette"))
    if outerwear != "no outer layer":
        outer_sentence = f"She shrugs into a {outerwear} crafted in {color} {finish}, its {random.choice(detailing)} and {random.choice(hardware)} adding {waist_synonym}."
        sentences.append(outer_sentence)
    if "dress" in layers:
        dress_sentence = f"Underneath sits a {layers['dress']} rendered in {color} {finish}, carrying {', '.join(detailing[:2])} for {fit}."
        sentences.append(dress_sentence)
    else:
        top_sentence = f"The {layers['top']} is cut from {color} {finish}, balanced by {fit} lines."
        sentences.append(top_sentence)
        bottom_sentence = f"She pairs it with a {layers['bottom']} tailored in the same {color} tone, finished with {random.choice(detailing)} and accented by {random.choice(hardware)}."
        sentences.append(bottom_sentence)
    if corsetry:
        sentences.append(f"Completing the midsection is {corsetry}, ensuring the look stays impeccably SFW while highlighting structure.")
    return sentences


def _build_accessory_sentences(hosiery: str, footwear: str, gloves: list[str], accessories: list[str]) -> list[str]:
    sentences: list[str] = []
    if hosiery != "no hosiery":
        sentences.append(f"Layered beneath, {hosiery} bring texture continuity down the legs.")
    footwear_sentence = f"{random.choice(('Grounding the look,', 'Anchoring the stance,', 'She finishes with', 'Balancing it below,'))} {footwear} maintain the leather narrative."
    sentences.append(footwear_sentence)
    if gloves:
        glove_sentence = f"Small leather goods include {', '.join(gloves)}."
        sentences.append(glove_sentence)
    if accessories:
        accessories_sentence = f"Jewelry and accents stay {random.choice(('considered', 'refined', 'purposeful'))} with {', '.join(accessories)}."
        sentences.append(accessories_sentence)
    return sentences


def _build_environment_sentence(scene: str, lighting: str, camera: list[str], pose: str, style: str) -> list[str]:
    sentences: list[str] = []
    camera_phrase = ", ".join(camera)
    sentences.append(
        f"She holds {pose} within a {scene}, channeling a {style} attitude."
    )
    sentences.append(
        f"{lighting.capitalize()} and {camera_phrase} shape the frame with editorial clarity."
    )
    return sentences


def _build_headwear_sentence(headwear: str, hair: str, outerwear: str) -> str:
    if headwear == "no headwear":
        descriptor = random.choice(("slick", "refined", "luminous"))
        return f"Her {hair} stays {descriptor}, echoing the lines of the {outerwear if outerwear != 'no outer layer' else 'look'}."
    texture_phrase = random.choice(("mirrors", "contrasts", "echoes"))
    return f"{headwear.capitalize()} {texture_phrase} the leather story while her {hair} keeps the profile precise."


def _select_detailing(count: int, polished: bool) -> list[str]:
    options = list(DETAILING)
    if polished:
        options = [item for item in options if "storm flaps" not in item.value or "trench" in item.value]
    return _weighted_sample(options, k=count)


def _select_hardware(count: int) -> list[str]:
    return _weighted_sample(HARDWARE, k=count)


def build_randomized_user_prompt() -> str:
    outerwear = _weighted_choice(OUTERWEAR)
    polished_layers = _needs_polished_layers(outerwear)
    headwear = _weighted_choice(HEADWEAR)
    hair = _weighted_choice(HAIR)
    finish, dramatic_finish = _select_finish()
    color = _weighted_choice(COLOR_PALETTE)
    detailing = _select_detailing(count=random.choice((2, 3)), polished=polished_layers)
    hardware = _select_hardware(count=2)
    fit = _weighted_choice(FIT_AND_SILHOUETTE)
    layers = _select_primary_layers(polished_layers)
    corsetry = _maybe_add_corsetry(polished_layers, outerwear, layers)
    hosiery = _weighted_choice(HOSIERY)
    footwear = _weighted_choice(FOOTWEAR)
    gloves = _weighted_sample(GLOVES_AND_SMALL_GOODS, k=random.choice((0, 1, 2)))
    accessories = _weighted_sample(ACCESSORIES, k=random.choice((1, 2)))
    pose = _weighted_choice(POSES)
    scene = _select_scene(dramatic_finish)
    lighting = _select_lighting(dramatic_finish)
    camera = _weighted_sample(CAMERA_AND_LENS, k=2)
    style = _weighted_choice(STYLE_DIRECTION)

    sentences: list[str] = []
    sentences.append(_build_headwear_sentence(headwear, hair, outerwear))
    sentences.extend(_build_layer_sentences(layers, outerwear, corsetry, finish, color, detailing, hardware, fit))
    sentences.extend(_build_accessory_sentences(hosiery, footwear, gloves, accessories))
    sentences.extend(_build_environment_sentence(scene, lighting, camera, pose, style))

    intro_sentence = "Craft a single SFW text-to-image prompt in English for a women's leather fashion image, blending outfit, model, setting, and atmosphere into one flowing paragraph."
    sfw_sentence = "Keep the description mature, tasteful, and focused on leather craftsmanship without mentioning brands or explicit content."

    core_sentences = sentences
    random.shuffle(core_sentences)
    paragraph_parts = [intro_sentence, sfw_sentence, *core_sentences]
    return " ".join(paragraph_parts)

