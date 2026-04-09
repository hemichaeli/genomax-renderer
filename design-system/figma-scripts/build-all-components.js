/**
 * GenoMAX² — Complete Figma Component Builder
 * ==============================================
 * Run this script via Figma MCP use_figma tool or Figma Plugin Console
 * File: IBBupwZ6yTT91Ccn02wKpK
 *
 * This script builds ALL label components for the GenoMAX² design system:
 * - 5 formats × 2 systems (MAXimo² + MAXima²) × 2 panels (Front + Back) = 20 components
 *
 * PREREQUISITES:
 * - Pages already created: 00_System_Tokens, 01_Label_Components, 02_System_Explanation
 * - Color variables already created (done in earlier step)
 * - Typography styles already created (done in earlier step)
 */

// ══════════════════════════════════════════════════════════════
// CONSTANTS
// ══════════════════════════════════════════════════════════════

function hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  return { r, g, b };
}

const COLORS = {
  BG: hexToRgb("#F4F2EC"),
  PRIMARY: hexToRgb("#1A1815"),
  SECONDARY: hexToRgb("#5C5A55"),
  TERTIARY: hexToRgb("#9A9890"),
  DIVIDER: hexToRgb("#C5C2BA"),
  MAXIMO: hexToRgb("#7A1E2E"),
  MAXIMA: hexToRgb("#7A304A"),
};

const FONTS = [
  { family: "IBM Plex Mono", style: "Bold" },
  { family: "IBM Plex Mono", style: "Regular" },
  { family: "IBM Plex Sans Condensed", style: "SemiBold" },
  { family: "IBM Plex Sans", style: "Light" },
  { family: "IBM Plex Sans", style: "Medium" },
  { family: "IBM Plex Sans", style: "Regular" },
];

// Format dimensions in pixels (at 72dpi, ~2x for Figma clarity)
const FORMATS = {
  BOTTLE:  { w: 540, h: 225, nameSize: 26, orientation: "horizontal" },
  JAR:     { w: 765, h: 180, nameSize: 22, orientation: "horizontal" },
  POUCH:   { w: 450, h: 360, nameSize: 28, orientation: "vertical" },
  DROPPER: { w: 180, h: 360, nameSize: 14, orientation: "vertical-narrow" },
  STRIPS:  { w: 360, h: 585, nameSize: 30, orientation: "vertical-tall" },
};

// Sample data (CV-01 from MAXimo Excel)
const SAMPLE_DATA = {
  maximo: {
    module_code: "CV-01",
    ingredient_name: "OMEGA-3 EPA 180mg + DHA 120mg",
    descriptor: "Omega-3 EPA + DHA",
    bio_system: "CARDIOVASCULAR LIPID METABOLISM",
    variant: "MAXimo²",
    type: "Softgels",
    function: "Lipid Metabolism",
    status: "Active",
    net_qty: "100 softgels",
    accent: COLORS.MAXIMO,
  },
  maxima: {
    module_code: "CV-01",
    ingredient_name: "OMEGA-3 EPA 180mg + DHA 120mg",
    descriptor: "Omega-3 EPA + DHA",
    bio_system: "CARDIOVASCULAR LIPID METABOLISM",
    variant: "MAXima²",
    type: "Softgels",
    function: "Lipid Metabolism",
    status: "Active",
    net_qty: "100 softgels",
    accent: COLORS.MAXIMA,
  },
};

// ══════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ══════════════════════════════════════════════════════════════

function createDivider(width) {
  const line = figma.createRectangle();
  line.name = "zone_divider";
  line.resize(width, 0.35);
  line.fills = [{ type: "SOLID", color: COLORS.DIVIDER }];
  return line;
}

function createSpacer(width, height) {
  const s = figma.createFrame();
  s.name = `spacer_${height}`;
  s.resize(width, height);
  s.fills = [];
  return s;
}

// ══════════════════════════════════════════════════════════════
// FRONT PANEL BUILDER
// ══════════════════════════════════════════════════════════════

function buildFrontPanel(formatName, format, data) {
  const W = format.w;
  const H = format.h;
  const contentW = W - 40;
  const isNarrow = format.orientation === "vertical-narrow";

  const front = figma.createFrame();
  front.name = `${data.variant.replace("²", "2")}_${formatName}_front`;
  front.resize(W, H);
  front.layoutMode = "VERTICAL";
  front.primaryAxisSizingMode = "FIXED";
  front.counterAxisSizingMode = "FIXED";
  front.paddingTop = 16;
  front.paddingBottom = 12;
  front.paddingLeft = 20;
  front.paddingRight = 20;
  front.itemSpacing = 0;
  front.fills = [{ type: "SOLID", color: COLORS.BG }];
  front.strokes = [{ type: "SOLID", color: COLORS.DIVIDER }];
  front.strokeWeight = 0.5;

  // ZONE 1: GenoMAX² + Module Code
  const zone1 = figma.createFrame();
  zone1.name = "zone_1_brand_module";
  zone1.layoutMode = "HORIZONTAL";
  zone1.primaryAxisSizingMode = "FIXED";
  zone1.counterAxisSizingMode = "AUTO";
  zone1.resize(contentW, 14);
  zone1.primaryAxisAlignItems = "SPACE_BETWEEN";
  zone1.counterAxisAlignItems = "CENTER";
  zone1.fills = [];

  const brand = figma.createText();
  brand.name = "brand_name";
  brand.fontName = { family: "IBM Plex Mono", style: "Bold" };
  brand.characters = "GenoMAX²";
  brand.fontSize = isNarrow ? 7 : 9.5;
  brand.fills = [{ type: "SOLID", color: COLORS.PRIMARY }];
  zone1.appendChild(brand);

  const modCode = figma.createText();
  modCode.name = "module_code";
  modCode.fontName = { family: "IBM Plex Mono", style: "Regular" };
  modCode.characters = data.module_code;
  modCode.fontSize = isNarrow ? 5.5 : 7;
  modCode.letterSpacing = { value: 0.8, unit: "PERCENT" };
  modCode.fills = [{ type: "SOLID", color: COLORS.SECONDARY }];
  zone1.appendChild(modCode);

  front.appendChild(zone1);
  front.appendChild(createSpacer(contentW, isNarrow ? 6 : 10));

  // ZONE 2: BIOLOGICAL OS MODULE
  const zone2 = figma.createFrame();
  zone2.name = "zone_2_os_module";
  zone2.layoutMode = "VERTICAL";
  zone2.primaryAxisSizingMode = "AUTO";
  zone2.counterAxisSizingMode = "FIXED";
  zone2.resize(contentW, 12);
  zone2.primaryAxisAlignItems = "CENTER";
  zone2.counterAxisAlignItems = "CENTER";
  zone2.fills = [];

  const osText = figma.createText();
  osText.name = "biological_os_module";
  osText.fontName = { family: "IBM Plex Mono", style: "Regular" };
  osText.characters = "BIOLOGICAL OS MODULE";
  osText.fontSize = isNarrow ? 5 : 7;
  osText.letterSpacing = { value: 0.8, unit: "PERCENT" };
  osText.textAlignHorizontal = "CENTER";
  osText.fills = [{ type: "SOLID", color: COLORS.SECONDARY }];
  zone2.appendChild(osText);

  front.appendChild(zone2);
  front.appendChild(createSpacer(contentW, isNarrow ? 4 : 6));

  // ZONE 3: PRODUCT NAME
  const zone3 = figma.createFrame();
  zone3.name = "zone_3_product_name";
  zone3.layoutMode = "VERTICAL";
  zone3.primaryAxisSizingMode = "AUTO";
  zone3.counterAxisSizingMode = "FIXED";
  zone3.resize(contentW, 34);
  zone3.counterAxisAlignItems = "CENTER";
  zone3.fills = [];

  const prodName = figma.createText();
  prodName.name = "ingredient_name";
  prodName.fontName = { family: "IBM Plex Sans Condensed", style: "SemiBold" };
  prodName.characters = data.ingredient_name;
  prodName.fontSize = format.nameSize;
  prodName.letterSpacing = { value: -0.1, unit: "PERCENT" };
  prodName.textAlignHorizontal = "CENTER";
  prodName.fills = [{ type: "SOLID", color: COLORS.PRIMARY }];
  zone3.appendChild(prodName);

  front.appendChild(zone3);
  front.appendChild(createSpacer(contentW, 4));

  // ZONE 4: Descriptor + Bio System
  const zone4 = figma.createFrame();
  zone4.name = "zone_4_descriptor";
  zone4.layoutMode = "VERTICAL";
  zone4.primaryAxisSizingMode = "AUTO";
  zone4.counterAxisSizingMode = "FIXED";
  zone4.resize(contentW, 24);
  zone4.counterAxisAlignItems = "CENTER";
  zone4.itemSpacing = 3;
  zone4.fills = [];

  const desc = figma.createText();
  desc.name = "descriptor";
  desc.fontName = { family: "IBM Plex Sans", style: "Light" };
  desc.characters = data.descriptor;
  desc.fontSize = isNarrow ? 6.5 : 8.5;
  desc.textAlignHorizontal = "CENTER";
  desc.fills = [{ type: "SOLID", color: COLORS.SECONDARY }];
  zone4.appendChild(desc);

  const bioSys = figma.createText();
  bioSys.name = "biological_system";
  bioSys.fontName = { family: "IBM Plex Mono", style: "Regular" };
  bioSys.characters = data.bio_system;
  bioSys.fontSize = isNarrow ? 4.5 : 6.5;
  bioSys.letterSpacing = { value: 0.4, unit: "PERCENT" };
  bioSys.textAlignHorizontal = "CENTER";
  bioSys.fills = [{ type: "SOLID", color: COLORS.TERTIARY }];
  zone4.appendChild(bioSys);

  front.appendChild(zone4);
  front.appendChild(createSpacer(contentW, 6));

  // ZONE 5: Variant + Accent Rule
  const zone5 = figma.createFrame();
  zone5.name = "zone_5_variant";
  zone5.layoutMode = "VERTICAL";
  zone5.primaryAxisSizingMode = "AUTO";
  zone5.counterAxisSizingMode = "FIXED";
  zone5.resize(contentW, 22);
  zone5.counterAxisAlignItems = "CENTER";
  zone5.itemSpacing = 3;
  zone5.fills = [];

  const varName = figma.createText();
  varName.name = "variant_name";
  varName.fontName = { family: "IBM Plex Sans", style: "Medium" };
  varName.characters = data.variant;
  varName.fontSize = isNarrow ? 8 : 11;
  varName.textAlignHorizontal = "CENTER";
  varName.fills = [{ type: "SOLID", color: COLORS.PRIMARY }];
  zone5.appendChild(varName);

  const accent = figma.createRectangle();
  accent.name = "accent_rule";
  accent.resize(isNarrow ? 40 : 60, 1.5);
  accent.fills = [{ type: "SOLID", color: data.accent }];
  zone5.appendChild(accent);

  front.appendChild(zone5);
  front.appendChild(createSpacer(contentW, 6));

  // ZONE 6: Metadata (TYPE / FUNCTION / STATUS)
  const zone6 = figma.createFrame();
  zone6.name = "zone_6_metadata";
  zone6.layoutMode = isNarrow ? "VERTICAL" : "HORIZONTAL";
  zone6.primaryAxisSizingMode = isNarrow ? "AUTO" : "FIXED";
  zone6.counterAxisSizingMode = isNarrow ? "FIXED" : "AUTO";
  zone6.resize(contentW, 20);
  if (!isNarrow) zone6.primaryAxisAlignItems = "SPACE_BETWEEN";
  zone6.itemSpacing = isNarrow ? 4 : 0;
  zone6.fills = [];

  const metaFields = [
    { label: "TYPE", value: data.type },
    { label: "FUNCTION", value: data.function },
    { label: "STATUS", value: data.status },
  ];

  for (const mf of metaFields) {
    const col = figma.createFrame();
    col.name = `meta_${mf.label.toLowerCase()}`;
    col.layoutMode = isNarrow ? "HORIZONTAL" : "VERTICAL";
    col.primaryAxisSizingMode = "AUTO";
    col.counterAxisSizingMode = "AUTO";
    col.itemSpacing = isNarrow ? 6 : 2;
    col.counterAxisAlignItems = isNarrow ? "CENTER" : "CENTER";
    col.fills = [];

    const lbl = figma.createText();
    lbl.name = `${mf.label.toLowerCase()}_label`;
    lbl.fontName = { family: "IBM Plex Mono", style: "Regular" };
    lbl.characters = mf.label;
    lbl.fontSize = isNarrow ? 4.5 : 5.5;
    lbl.letterSpacing = { value: 0.6, unit: "PERCENT" };
    lbl.textAlignHorizontal = "CENTER";
    lbl.fills = [{ type: "SOLID", color: COLORS.TERTIARY }];
    col.appendChild(lbl);

    const val = figma.createText();
    val.name = `${mf.label.toLowerCase()}_value`;
    val.fontName = { family: "IBM Plex Sans", style: "Regular" };
    val.characters = mf.value;
    val.fontSize = isNarrow ? 5 : 6.5;
    val.textAlignHorizontal = "CENTER";
    val.fills = [{ type: "SOLID", color: COLORS.PRIMARY }];
    col.appendChild(val);

    zone6.appendChild(col);
  }

  front.appendChild(zone6);
  front.appendChild(createSpacer(contentW, 6));
  front.appendChild(createDivider(contentW));
  front.appendChild(createSpacer(contentW, 4));

  // ZONE 7: Version Strip
  const zone7 = figma.createFrame();
  zone7.name = "zone_7_version";
  zone7.layoutMode = isNarrow ? "VERTICAL" : "HORIZONTAL";
  zone7.primaryAxisSizingMode = isNarrow ? "AUTO" : "FIXED";
  zone7.counterAxisSizingMode = isNarrow ? "FIXED" : "AUTO";
  zone7.resize(contentW, 10);
  if (!isNarrow) zone7.primaryAxisAlignItems = "SPACE_BETWEEN";
  zone7.counterAxisAlignItems = isNarrow ? "CENTER" : "CENTER";
  zone7.itemSpacing = isNarrow ? 2 : 0;
  zone7.fills = [];

  const verLeft = figma.createText();
  verLeft.name = "version_info";
  verLeft.fontName = { family: "IBM Plex Mono", style: "Regular" };
  verLeft.characters = `v1.0 | ${data.module_code} | Clinical Grade`;
  verLeft.fontSize = isNarrow ? 4 : 5.5;
  verLeft.letterSpacing = { value: 0.2, unit: "PERCENT" };
  verLeft.fills = [{ type: "SOLID", color: COLORS.TERTIARY }];
  zone7.appendChild(verLeft);

  const verRight = figma.createText();
  verRight.name = "net_quantity";
  verRight.fontName = { family: "IBM Plex Mono", style: "Regular" };
  verRight.characters = `DIETARY SUPPLEMENT | NET QTY: ${data.net_qty}`;
  verRight.fontSize = isNarrow ? 4 : 5.5;
  verRight.letterSpacing = { value: 0.2, unit: "PERCENT" };
  verRight.fills = [{ type: "SOLID", color: COLORS.TERTIARY }];
  zone7.appendChild(verRight);

  front.appendChild(zone7);

  return front;
}

// ══════════════════════════════════════════════════════════════
// BACK PANEL BUILDER
// ══════════════════════════════════════════════════════════════

function buildBackPanel(formatName, format, data) {
  const W = format.w;
  const H = format.h;
  const contentW = W - 40;
  const isNarrow = format.orientation === "vertical-narrow";
  const fontSize = isNarrow ? 4.5 : 5.5;

  const back = figma.createFrame();
  back.name = `${data.variant.replace("²", "2")}_${formatName}_back`;
  back.resize(W, H);
  back.layoutMode = "VERTICAL";
  back.primaryAxisSizingMode = "FIXED";
  back.counterAxisSizingMode = "FIXED";
  back.paddingTop = 12;
  back.paddingBottom = 12;
  back.paddingLeft = 20;
  back.paddingRight = 20;
  back.itemSpacing = 8;
  back.fills = [{ type: "SOLID", color: COLORS.BG }];
  back.strokes = [{ type: "SOLID", color: COLORS.DIVIDER }];
  back.strokeWeight = 0.5;

  // Supplement Facts Header
  const sfHeader = figma.createFrame();
  sfHeader.name = "supplement_facts_header";
  sfHeader.layoutMode = "VERTICAL";
  sfHeader.primaryAxisSizingMode = "AUTO";
  sfHeader.counterAxisSizingMode = "FIXED";
  sfHeader.resize(contentW, 28);
  sfHeader.paddingTop = 4;
  sfHeader.paddingBottom = 4;
  sfHeader.paddingLeft = 8;
  sfHeader.paddingRight = 8;
  sfHeader.fills = [{ type: "SOLID", color: COLORS.PRIMARY }];

  const sfTitle = figma.createText();
  sfTitle.name = "supplement_facts_title";
  sfTitle.fontName = { family: "IBM Plex Sans", style: "Medium" };
  sfTitle.characters = "Supplement Facts";
  sfTitle.fontSize = isNarrow ? 7 : 10;
  sfTitle.fills = [{ type: "SOLID", color: COLORS.BG }];
  sfHeader.appendChild(sfTitle);

  const sfServing = figma.createText();
  sfServing.name = "serving_info";
  sfServing.fontName = { family: "IBM Plex Sans", style: "Regular" };
  sfServing.characters = "Serving Size: 2 Softgels | Servings Per Container: 50";
  sfServing.fontSize = isNarrow ? 4 : 5.5;
  sfServing.fills = [{ type: "SOLID", color: { r: 0.85, g: 0.83, b: 0.8 } }];
  sfHeader.appendChild(sfServing);

  back.appendChild(sfHeader);

  // Supplement Facts placeholder
  const sfBody = figma.createText();
  sfBody.name = "supplement_facts_body";
  sfBody.fontName = { family: "IBM Plex Sans", style: "Regular" };
  sfBody.characters = "Amount Per Serving                                      %DV\n────────────────────────────────────────\n[Ingredient rows populated from supplement facts data]";
  sfBody.fontSize = fontSize;
  sfBody.fills = [{ type: "SOLID", color: COLORS.PRIMARY }];
  back.appendChild(sfBody);

  // Other Ingredients
  const otherIng = figma.createText();
  otherIng.name = "other_ingredients";
  otherIng.fontName = { family: "IBM Plex Sans", style: "Regular" };
  otherIng.characters = "Other Ingredients: [from product data]";
  otherIng.fontSize = fontSize;
  otherIng.fills = [{ type: "SOLID", color: COLORS.SECONDARY }];
  back.appendChild(otherIng);

  back.appendChild(createDivider(contentW));

  // Directions
  const dirLabel = figma.createText();
  dirLabel.name = "directions_label";
  dirLabel.fontName = { family: "IBM Plex Mono", style: "Regular" };
  dirLabel.characters = "DIRECTIONS";
  dirLabel.fontSize = isNarrow ? 5 : 6;
  dirLabel.letterSpacing = { value: 0.6, unit: "PERCENT" };
  dirLabel.fills = [{ type: "SOLID", color: COLORS.TERTIARY }];
  back.appendChild(dirLabel);

  const dirText = figma.createText();
  dirText.name = "directions_text";
  dirText.fontName = { family: "IBM Plex Sans", style: "Regular" };
  dirText.characters = "As a dietary supplement, take with meals, or as directed by a healthcare professional.";
  dirText.fontSize = fontSize;
  dirText.fills = [{ type: "SOLID", color: COLORS.PRIMARY }];
  back.appendChild(dirText);

  back.appendChild(createDivider(contentW));

  // Safety
  const safeLabel = figma.createText();
  safeLabel.name = "safety_label";
  safeLabel.fontName = { family: "IBM Plex Mono", style: "Regular" };
  safeLabel.characters = "SAFETY";
  safeLabel.fontSize = isNarrow ? 5 : 6;
  safeLabel.letterSpacing = { value: 0.6, unit: "PERCENT" };
  safeLabel.fills = [{ type: "SOLID", color: COLORS.TERTIARY }];
  back.appendChild(safeLabel);

  const safeText = figma.createText();
  safeText.name = "safety_text";
  safeText.fontName = { family: "IBM Plex Sans", style: "Regular" };
  safeText.characters = "Consult a healthcare professional if pregnant, nursing, taking medication, or with a medical condition. Keep out of reach of children.";
  safeText.fontSize = fontSize;
  safeText.fills = [{ type: "SOLID", color: COLORS.PRIMARY }];
  back.appendChild(safeText);

  back.appendChild(createDivider(contentW));

  // Manufacturer
  const mfgLabel = figma.createText();
  mfgLabel.name = "manufacturer_label";
  mfgLabel.fontName = { family: "IBM Plex Mono", style: "Regular" };
  mfgLabel.characters = "MANUFACTURED FOR";
  mfgLabel.fontSize = isNarrow ? 5 : 6;
  mfgLabel.letterSpacing = { value: 0.6, unit: "PERCENT" };
  mfgLabel.fills = [{ type: "SOLID", color: COLORS.TERTIARY }];
  back.appendChild(mfgLabel);

  const mfgName = figma.createText();
  mfgName.name = "manufacturer_name";
  mfgName.fontName = { family: "IBM Plex Sans", style: "Medium" };
  mfgName.characters = "Genomax LLC";
  mfgName.fontSize = isNarrow ? 5 : 6;
  mfgName.fills = [{ type: "SOLID", color: COLORS.PRIMARY }];
  back.appendChild(mfgName);

  const mfgAddr = figma.createText();
  mfgAddr.name = "manufacturer_address";
  mfgAddr.fontName = { family: "IBM Plex Sans", style: "Regular" };
  mfgAddr.characters = "95 Newfield Avenue, Suite A\nEdison, NJ 08837 USA\nwww.genomax.ai | support@genomax.ai";
  mfgAddr.fontSize = isNarrow ? 4 : 5.5;
  mfgAddr.fills = [{ type: "SOLID", color: COLORS.SECONDARY }];
  back.appendChild(mfgAddr);

  // FDA Disclaimer
  const fda = figma.createText();
  fda.name = "fda_disclaimer";
  fda.fontName = { family: "IBM Plex Sans", style: "Regular" };
  fda.characters = "This statement has not been evaluated by the Food and Drug Administration. This product is not intended to diagnose, treat, cure, or prevent any disease.";
  fda.fontSize = isNarrow ? 3.5 : 4.5;
  fda.fills = [{ type: "SOLID", color: COLORS.TERTIARY }];
  back.appendChild(fda);

  return back;
}

// ══════════════════════════════════════════════════════════════
// MAIN EXECUTION
// ══════════════════════════════════════════════════════════════

async function buildAllComponents() {
  // Load all fonts
  for (const f of FONTS) {
    await figma.loadFontAsync(f);
  }

  const page = figma.root.children[1]; // 01_Label_Components
  await figma.setCurrentPageAsync(page);

  let xOffset = 0;
  let yOffset = 0;
  const GAP = 40;

  for (const [formatName, format] of Object.entries(FORMATS)) {
    // MAXimo² Front
    const maximoFront = buildFrontPanel(formatName, format, SAMPLE_DATA.maximo);
    const maximoFrontComp = figma.createComponentFromNode(maximoFront);
    maximoFrontComp.name = `MAXimo²/${formatName}/Front`;
    maximoFrontComp.description = `MAXimo² ${formatName} front panel — 7-zone label system`;
    maximoFrontComp.x = xOffset;
    maximoFrontComp.y = yOffset;

    // MAXimo² Back
    const maximoBack = buildBackPanel(formatName, format, SAMPLE_DATA.maximo);
    const maximoBackComp = figma.createComponentFromNode(maximoBack);
    maximoBackComp.name = `MAXimo²/${formatName}/Back`;
    maximoBackComp.description = `MAXimo² ${formatName} back panel`;
    maximoBackComp.x = xOffset + format.w + GAP;
    maximoBackComp.y = yOffset;

    // MAXima² Front
    const maximaFront = buildFrontPanel(formatName, format, SAMPLE_DATA.maxima);
    const maximaFrontComp = figma.createComponentFromNode(maximaFront);
    maximaFrontComp.name = `MAXima²/${formatName}/Front`;
    maximaFrontComp.description = `MAXima² ${formatName} front panel — 7-zone label system`;
    maximaFrontComp.x = xOffset;
    maximaFrontComp.y = yOffset + format.h + GAP;

    // MAXima² Back
    const maximaBack = buildBackPanel(formatName, format, SAMPLE_DATA.maxima);
    const maximaBackComp = figma.createComponentFromNode(maximaBack);
    maximaBackComp.name = `MAXima²/${formatName}/Back`;
    maximaBackComp.description = `MAXima² ${formatName} back panel`;
    maximaBackComp.x = xOffset + format.w + GAP;
    maximaBackComp.y = yOffset + format.h + GAP;

    // Move to next column
    xOffset += (format.w * 2) + (GAP * 3);
  }

  return {
    status: "All components built",
    formats: Object.keys(FORMATS).length,
    total_components: Object.keys(FORMATS).length * 4, // 2 systems × 2 panels
  };
}

// Execute
await buildAllComponents();
