/**
 * GenoMAX² — V3 Figma Component Builder (Brand Signature)
 * =========================================================
 * Run via Figma MCP use_figma tool
 * File: IBBupwZ6yTT91Ccn02wKpK
 *
 * V3 CHANGES FROM V2:
 * - Brand ceiling: 2px accent line at top (full bleed)
 * - GenoMAX² tracking: 0.18em (engraved feel)
 * - Brand rule: 0.5px line beneath brand at 25% opacity
 * - Zone 7: dark inverted strip
 * - All weights escalated (400→500 min)
 * - Tighter spacing throughout
 */

function hexToRgb(hex) {
  return {
    r: parseInt(hex.slice(1,3),16)/255,
    g: parseInt(hex.slice(3,5),16)/255,
    b: parseInt(hex.slice(5,7),16)/255
  };
}

const C = {
  BG: hexToRgb("#F4F2EC"),
  PRI: hexToRgb("#1A1815"),
  SEC: hexToRgb("#4A4843"),
  TER: hexToRgb("#8A8880"),
  DIV: hexToRgb("#C5C2BA"),
  MXO: hexToRgb("#7A1E2E"),
  MXA: hexToRgb("#7A304A"),
  STRIP_BG: hexToRgb("#1A1815"),
  STRIP_TEXT: hexToRgb("#C5C2BA"),
};

const FONTS = [
  { family: "IBM Plex Mono", style: "Bold" },
  { family: "IBM Plex Mono", style: "Medium" },
  { family: "IBM Plex Mono", style: "Regular" },
  { family: "IBM Plex Sans Condensed", style: "Bold" },
  { family: "IBM Plex Sans Condensed", style: "SemiBold" },
  { family: "IBM Plex Sans", style: "Light" },
  { family: "IBM Plex Sans", style: "Medium" },
  { family: "IBM Plex Sans", style: "Regular" },
  { family: "IBM Plex Sans", style: "SemiBold" },
  { family: "Inter", style: "Bold" },
  { family: "Inter", style: "Regular" },
];

const FORMATS = {
  BOTTLE:  { w: 540, h: 225, nameSize: 26, narrow: false },
  JAR:     { w: 765, h: 180, nameSize: 22, narrow: false },
  POUCH:   { w: 450, h: 360, nameSize: 28, narrow: false },
  DROPPER: { w: 180, h: 360, nameSize: 14, narrow: true },
  STRIPS:  { w: 360, h: 585, nameSize: 30, narrow: false },
};

const SAMPLE = {
  maximo: {
    code: "CV-01", name: "OMEGA-3 EPA 180mg + DHA 120mg",
    desc: "Omega-3 EPA + DHA", sys: "CARDIOVASCULAR · LIPID METABOLISM",
    variant: "MAXimo²", form: "Softgels", func: "Lipid Metabolism",
    qty: "100 softgels", accent: C.MXO,
  },
  maxima: {
    code: "CV-01", name: "OMEGA-3 EPA 180mg + DHA 120mg",
    desc: "Omega-3 EPA + DHA", sys: "CARDIOVASCULAR · LIPID METABOLISM",
    variant: "MAXima²", form: "Softgels", func: "Lipid Metabolism",
    qty: "100 softgels", accent: C.MXA,
  },
};

function buildV3FrontPanel(formatName, format, data) {
  const W = format.w;
  const H = format.h;
  const cW = W - 28;
  const n = format.narrow;

  const front = figma.createFrame();
  front.name = `${data.variant.replace("²","2")}_${formatName}_v3_front`;
  front.resize(W, H);
  front.layoutMode = "VERTICAL";
  front.primaryAxisSizingMode = "FIXED";
  front.counterAxisSizingMode = "FIXED";
  front.paddingTop = 0;
  front.paddingBottom = 0;
  front.paddingLeft = 0;
  front.paddingRight = 0;
  front.itemSpacing = 0;
  front.fills = [{ type: "SOLID", color: C.BG }];
  front.strokes = [{ type: "SOLID", color: C.DIV }];
  front.strokeWeight = 0.5;
  front.clipsContent = true;

  // ── BRAND CEILING ──
  const ceiling = figma.createRectangle();
  ceiling.name = "brand_ceiling";
  ceiling.resize(W, 2);
  ceiling.fills = [{ type: "SOLID", color: data.accent }];
  front.appendChild(ceiling);

  // ── BRAND ZONE ──
  const brandZone = figma.createFrame();
  brandZone.name = "brand_zone";
  brandZone.layoutMode = "HORIZONTAL";
  brandZone.primaryAxisSizingMode = "FIXED";
  brandZone.counterAxisSizingMode = "AUTO";
  brandZone.resize(W, 16);
  brandZone.paddingLeft = 14;
  brandZone.paddingRight = 14;
  brandZone.paddingTop = 5;
  brandZone.primaryAxisAlignItems = "SPACE_BETWEEN";
  brandZone.counterAxisAlignItems = "BASELINE";
  brandZone.fills = [];

  const brand = figma.createText();
  brand.name = "brand_name";
  brand.fontName = { family: "IBM Plex Mono", style: "Bold" };
  brand.characters = "GenoMAX²";
  brand.fontSize = n ? 7 : 12;
  brand.letterSpacing = { value: 18, unit: "PERCENT" };
  brand.fills = [{ type: "SOLID", color: C.PRI }];
  brandZone.appendChild(brand);

  const modCode = figma.createText();
  modCode.name = "module_code";
  modCode.fontName = { family: "IBM Plex Mono", style: "Medium" };
  modCode.characters = data.code;
  modCode.fontSize = n ? 4 : 6;
  modCode.letterSpacing = { value: 12, unit: "PERCENT" };
  modCode.fills = [{ type: "SOLID", color: C.TER }];
  brandZone.appendChild(modCode);

  front.appendChild(brandZone);

  // Brand rule
  const brandRule = figma.createFrame();
  brandRule.name = "brand_rule_container";
  brandRule.layoutMode = "HORIZONTAL";
  brandRule.primaryAxisSizingMode = "FIXED";
  brandRule.counterAxisSizingMode = "AUTO";
  brandRule.resize(W, 1);
  brandRule.paddingLeft = 14;
  brandRule.paddingRight = 14;
  brandRule.fills = [];
  const ruleRect = figma.createRectangle();
  ruleRect.name = "brand_rule";
  ruleRect.resize(W - 28, 0.5);
  ruleRect.fills = [{ type: "SOLID", color: C.PRI, opacity: 0.25 }];
  brandRule.appendChild(ruleRect);
  front.appendChild(brandRule);

  // ── CONTENT ZONES ──
  const content = figma.createFrame();
  content.name = "content_zones";
  content.layoutMode = "VERTICAL";
  content.primaryAxisSizingMode = "AUTO";
  content.counterAxisSizingMode = "FIXED";
  content.resize(W, 10);
  content.paddingLeft = 14;
  content.paddingRight = 14;
  content.paddingTop = n ? 3 : 4;
  content.itemSpacing = 0;
  content.fills = [];

  // Helper
  function sp(h) {
    const f = figma.createFrame(); f.name="sp"; f.resize(cW, h); f.fills=[]; content.appendChild(f);
  }

  // Z2
  const z2 = figma.createText();
  z2.name = "biological_os_module";
  z2.fontName = { family: "IBM Plex Mono", style: "Medium" };
  z2.characters = "BIOLOGICAL OS MODULE";
  z2.fontSize = n ? 4 : 7;
  z2.letterSpacing = { value: 18, unit: "PERCENT" };
  z2.textAlignHorizontal = "CENTER";
  z2.fills = [{ type: "SOLID", color: C.SEC }];
  z2.resize(cW, z2.height); z2.textAutoResize = "HEIGHT";
  content.appendChild(z2);
  sp(n ? 2 : 3);

  // Z3
  const z3 = figma.createText();
  z3.name = "ingredient_name";
  z3.fontName = { family: "IBM Plex Sans Condensed", style: "Bold" };
  z3.characters = data.name;
  z3.fontSize = format.nameSize;
  z3.letterSpacing = { value: -2.5, unit: "PERCENT" };
  z3.textAlignHorizontal = "CENTER";
  z3.lineHeight = { value: 95, unit: "PERCENT" };
  z3.fills = [{ type: "SOLID", color: C.PRI }];
  z3.resize(cW, z3.height); z3.textAutoResize = "HEIGHT";
  content.appendChild(z3);
  sp(n ? 1 : 2);

  // Z4
  const z4d = figma.createText();
  z4d.name = "descriptor";
  z4d.fontName = { family: "IBM Plex Sans", style: "Light" };
  z4d.characters = data.desc;
  z4d.fontSize = n ? 5 : 8.5;
  z4d.letterSpacing = { value: 1, unit: "PERCENT" };
  z4d.textAlignHorizontal = "CENTER";
  z4d.fills = [{ type: "SOLID", color: C.SEC }];
  z4d.resize(cW, z4d.height); z4d.textAutoResize = "HEIGHT";
  content.appendChild(z4d);
  sp(1);

  const z4s = figma.createText();
  z4s.name = "biological_system";
  z4s.fontName = { family: "IBM Plex Mono", style: "Regular" };
  z4s.characters = data.sys;
  z4s.fontSize = n ? 3.5 : 6.5;
  z4s.letterSpacing = { value: 6, unit: "PERCENT" };
  z4s.textAlignHorizontal = "CENTER";
  z4s.fills = [{ type: "SOLID", color: C.TER }];
  z4s.resize(cW, z4s.height); z4s.textAutoResize = "HEIGHT";
  content.appendChild(z4s);
  sp(n ? 3 : 4);

  // Z5
  const z5n = figma.createText();
  z5n.name = "variant_name";
  z5n.fontName = { family: "IBM Plex Sans", style: "SemiBold" };
  z5n.characters = data.variant;
  z5n.fontSize = n ? 7 : 12;
  z5n.letterSpacing = { value: 1, unit: "PERCENT" };
  z5n.textAlignHorizontal = "CENTER";
  z5n.fills = [{ type: "SOLID", color: C.PRI }];
  z5n.resize(cW, z5n.height); z5n.textAutoResize = "HEIGHT";
  content.appendChild(z5n);
  sp(2);

  const accentWrap = figma.createFrame();
  accentWrap.name = "accent_rule_wrap";
  accentWrap.layoutMode = "HORIZONTAL";
  accentWrap.primaryAxisSizingMode = "FIXED";
  accentWrap.counterAxisSizingMode = "AUTO";
  accentWrap.resize(cW, 2);
  accentWrap.primaryAxisAlignItems = "CENTER";
  accentWrap.fills = [];
  const accent = figma.createRectangle();
  accent.name = "accent_rule";
  accent.resize(n ? 30 : 70, 2);
  accent.fills = [{ type: "SOLID", color: data.accent }];
  accentWrap.appendChild(accent);
  content.appendChild(accentWrap);
  sp(n ? 3 : 4);

  // Z6
  const z6 = figma.createFrame();
  z6.name = "zone_6_metadata";
  z6.layoutMode = n ? "VERTICAL" : "HORIZONTAL";
  z6.primaryAxisSizingMode = n ? "AUTO" : "FIXED";
  z6.counterAxisSizingMode = n ? "FIXED" : "AUTO";
  z6.resize(cW, 16);
  if (!n) z6.primaryAxisAlignItems = "SPACE_BETWEEN";
  z6.itemSpacing = n ? 3 : 0;
  z6.fills = [];

  const metas = [
    { l: "TYPE", v: data.form },
    { l: "FUNCTION", v: data.func },
    { l: "STATUS", v: "Active" },
  ];
  for (const m of metas) {
    const col = figma.createFrame();
    col.name = `meta_${m.l.toLowerCase()}`;
    col.layoutMode = n ? "HORIZONTAL" : "VERTICAL";
    col.primaryAxisSizingMode = "AUTO";
    col.counterAxisSizingMode = "AUTO";
    col.itemSpacing = n ? 4 : 1;
    col.counterAxisAlignItems = n ? "CENTER" : "CENTER";
    col.fills = [];

    const lbl = figma.createText();
    lbl.fontName = { family: "IBM Plex Mono", style: "Medium" };
    lbl.characters = m.l;
    lbl.fontSize = n ? 3.5 : 5.5;
    lbl.letterSpacing = { value: 10, unit: "PERCENT" };
    lbl.fills = [{ type: "SOLID", color: C.TER }];
    col.appendChild(lbl);

    const val = figma.createText();
    val.fontName = { family: "IBM Plex Sans", style: "Medium" };
    val.characters = m.v;
    val.fontSize = n ? 4 : 6.5;
    val.fills = [{ type: "SOLID", color: C.PRI }];
    col.appendChild(val);

    z6.appendChild(col);
  }
  content.appendChild(z6);

  front.appendChild(content);

  // Divider before Z7
  const divider = figma.createRectangle();
  divider.name = "zone_divider";
  divider.resize(W, 0.5);
  divider.fills = [{ type: "SOLID", color: C.DIV }];
  front.appendChild(divider);

  // ── ZONE 7: Dark Strip ──
  const z7 = figma.createFrame();
  z7.name = "zone_7_strip";
  z7.layoutMode = "HORIZONTAL";
  z7.primaryAxisSizingMode = "FIXED";
  z7.counterAxisSizingMode = "AUTO";
  z7.resize(W, 16);
  z7.paddingLeft = 14;
  z7.paddingRight = 14;
  z7.paddingTop = 4;
  z7.paddingBottom = 4;
  z7.primaryAxisAlignItems = n ? "CENTER" : "SPACE_BETWEEN";
  z7.counterAxisAlignItems = "CENTER";
  z7.fills = [{ type: "SOLID", color: C.STRIP_BG }];

  if (n) {
    z7.layoutMode = "VERTICAL";
    z7.primaryAxisAlignItems = "CENTER";
    z7.counterAxisAlignItems = "CENTER";
    z7.itemSpacing = 1;
  }

  const v7l = figma.createText();
  v7l.name = "version_info";
  v7l.fontName = { family: "IBM Plex Mono", style: "Regular" };
  v7l.characters = `v1.0 · ${data.code} · Clinical Grade`;
  v7l.fontSize = n ? 3.5 : 5.5;
  v7l.letterSpacing = { value: 3, unit: "PERCENT" };
  v7l.fills = [{ type: "SOLID", color: C.STRIP_TEXT }];
  z7.appendChild(v7l);

  const v7r = figma.createText();
  v7r.name = "net_quantity";
  v7r.fontName = { family: "IBM Plex Mono", style: "Regular" };
  v7r.characters = `DIETARY SUPPLEMENT · ${data.qty}`;
  v7r.fontSize = n ? 3.5 : 5.5;
  v7r.letterSpacing = { value: 3, unit: "PERCENT" };
  v7r.fills = [{ type: "SOLID", color: C.STRIP_TEXT }];
  z7.appendChild(v7r);

  front.appendChild(z7);

  return front;
}

async function buildAll() {
  for (const f of FONTS) {
    await figma.loadFontAsync(f);
  }

  const page = figma.root.children[1];
  await figma.setCurrentPageAsync(page);

  let xOffset = 0;
  let yOffset = 500;
  const GAP = 60;

  for (const [fmtName, fmt] of Object.entries(FORMATS)) {
    // MAXimo²
    const mxoFront = buildV3FrontPanel(fmtName, fmt, SAMPLE.maximo);
    const mxoComp = figma.createComponentFromNode(mxoFront);
    mxoComp.name = `MAXimo²/${fmtName}/V3-Front`;
    mxoComp.description = `V3 Brand Signature — MAXimo² ${fmtName} front panel`;
    mxoComp.x = xOffset;
    mxoComp.y = yOffset;

    // MAXima²
    const mxaFront = buildV3FrontPanel(fmtName, fmt, SAMPLE.maxima);
    const mxaComp = figma.createComponentFromNode(mxaFront);
    mxaComp.name = `MAXima²/${fmtName}/V3-Front`;
    mxaComp.description = `V3 Brand Signature — MAXima² ${fmtName} front panel`;
    mxaComp.x = xOffset;
    mxaComp.y = yOffset + fmt.h + GAP;

    xOffset += fmt.w + GAP;
  }

  return {
    status: "V3 components built",
    formats: Object.keys(FORMATS).length,
    total: Object.keys(FORMATS).length * 2,
  };
}

await buildAll();
