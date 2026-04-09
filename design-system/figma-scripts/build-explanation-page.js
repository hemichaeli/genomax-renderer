/**
 * GenoMAX² — System Explanation Page Builder
 * Run via Figma MCP after components are built
 * File: IBBupwZ6yTT91Ccn02wKpK
 */

async function buildExplanationPage() {
  function hexToRgb(hex) {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    return { r, g, b };
  }

  const PRIMARY = hexToRgb("#1A1815");
  const SECONDARY = hexToRgb("#5C5A55");
  const TERTIARY = hexToRgb("#9A9890");

  await figma.loadFontAsync({ family: "IBM Plex Mono", style: "Bold" });
  await figma.loadFontAsync({ family: "IBM Plex Mono", style: "Regular" });
  await figma.loadFontAsync({ family: "IBM Plex Sans", style: "Medium" });
  await figma.loadFontAsync({ family: "IBM Plex Sans", style: "Regular" });

  const page = figma.root.children[2]; // 02_System_Explanation
  await figma.setCurrentPageAsync(page);

  const frame = figma.createFrame();
  frame.name = "system_explanation";
  frame.resize(900, 2000);
  frame.layoutMode = "VERTICAL";
  frame.primaryAxisSizingMode = "AUTO";
  frame.counterAxisSizingMode = "FIXED";
  frame.paddingTop = 60;
  frame.paddingBottom = 60;
  frame.paddingLeft = 60;
  frame.paddingRight = 60;
  frame.itemSpacing = 32;
  frame.fills = [{ type: "SOLID", color: { r: 1, g: 1, b: 1 } }];

  function addHeading(text) {
    const t = figma.createText();
    t.fontName = { family: "IBM Plex Mono", style: "Bold" };
    t.characters = text;
    t.fontSize = 24;
    t.fills = [{ type: "SOLID", color: PRIMARY }];
    frame.appendChild(t);
  }

  function addSubheading(text) {
    const t = figma.createText();
    t.fontName = { family: "IBM Plex Sans", style: "Medium" };
    t.characters = text;
    t.fontSize = 14;
    t.fills = [{ type: "SOLID", color: PRIMARY }];
    frame.appendChild(t);
  }

  function addBody(text) {
    const t = figma.createText();
    t.fontName = { family: "IBM Plex Sans", style: "Regular" };
    t.characters = text;
    t.fontSize = 11;
    t.fills = [{ type: "SOLID", color: SECONDARY }];
    t.resize(780, t.height);
    t.textAutoResize = "HEIGHT";
    frame.appendChild(t);
  }

  function addCode(text) {
    const t = figma.createText();
    t.fontName = { family: "IBM Plex Mono", style: "Regular" };
    t.characters = text;
    t.fontSize = 9;
    t.fills = [{ type: "SOLID", color: TERTIARY }];
    t.resize(780, t.height);
    t.textAutoResize = "HEIGHT";
    frame.appendChild(t);
  }

  // ── CONTENT ──
  addHeading("GenoMAX² — Design System v1.0");
  addBody("Unified visual system for product labels, website PDPs, Amazon listings, and catalog. Built for 100+ SKUs across 5 formats and 2 independent product systems.");

  addSubheading("SYSTEM AUTHORITY");
  addBody("All structural decisions derive from genomax2_master_label_template.pdf. The 7-zone front panel layout, IBM Plex typography system, and restricted color palette are non-negotiable.");

  addSubheading("7-ZONE FRONT PANEL LAYOUT");
  addCode(
    "Zone 1  GenoMAX² + Module Code (e.g. CV-01)\n" +
    "Zone 2  BIOLOGICAL OS MODULE — IBM Plex Mono, centered, uppercase\n" +
    "Zone 3  Product Name — LARGEST element. IBM Plex Sans Condensed SemiBold\n" +
    "Zone 4  Descriptor + Biological System name\n" +
    "Zone 5  MAXimo² / MAXima² + single thin accent rule beneath\n" +
    "Zone 6  Metadata: TYPE · FUNCTION · STATUS (3 columns)\n" +
    "Zone 7  v1.0 | Module Code | Clinical Grade / NET QTY"
  );

  addSubheading("TYPOGRAPHY SYSTEM");
  addCode(
    "IBM Plex Mono Bold 700      9.5pt    GenoMAX² header\n" +
    "IBM Plex Mono Regular 400   7pt      Zone 2 header (UPPERCASE, tracked)\n" +
    "IBM Plex Sans Cond SemiBold 26pt     Product name (Zone 3)\n" +
    "IBM Plex Sans Light 300     8.5pt    Descriptor line\n" +
    "IBM Plex Mono Regular       6.5pt    Bio system name (UPPERCASE)\n" +
    "IBM Plex Sans Medium 500    11pt     Variant name (MAXimo²/MAXima²)\n" +
    "IBM Plex Mono Regular       5.5pt    Metadata labels (UPPERCASE)\n" +
    "IBM Plex Sans Regular       6.5pt    Metadata values\n" +
    "IBM Plex Mono Regular       5.5pt    Version strip\n\n" +
    "NO serif fonts. NO italic. NO decorative typefaces."
  );

  addSubheading("COLOR SYSTEM");
  addCode(
    "#F4F2EC  background     Off-white clinical\n" +
    "#1A1815  text/primary    Graphite / near-black\n" +
    "#5C5A55  text/secondary  Muted graphite\n" +
    "#9A9890  text/tertiary   Zone separators, version strip\n" +
    "#C5C2BA  divider         Hairline 0.3-0.4pt\n" +
    "#7A1E2E  accent/maximo   Deep muted red — accent rule ONLY\n" +
    "#7A304A  accent/maxima   Muted rose — accent rule ONLY\n\n" +
    "Accent rule placement: Under MAXimo²/MAXima² ONLY. NOT under GenoMAX².\n" +
    "No badges. No color blocks. No gradients."
  );

  addSubheading("MAXimo² / MAXima² RULE");
  addBody(
    "These are NOT dynamic variants of each other. They are SEPARATE product systems sourced from independent Excel files:\n\n" +
    "  • GENOMAX_MAXimo_LABEL_READY_v2.xlsx → 84 SKUs\n" +
    "  • GENOMAX_MAXima_LABEL_READY_v2.xlsx → 84 SKUs\n\n" +
    "NEVER merge. NEVER create variant columns. NEVER infer logic between them.\n" +
    "Each file = independent product system with its own component tree."
  );

  addSubheading("FORMAT DIMENSIONS");
  addCode(
    "BOTTLE   6.0\" × 2.5\"   (152.4 × 63.5mm)   38-39 SKUs\n" +
    "JAR      8.5\" × 2.0\"   (215.9 × 50.8mm)   20 SKUs\n" +
    "POUCH    5.0\" × 4.0\"   (127.0 × 101.6mm)  12 SKUs\n" +
    "DROPPER  2.0\" × 4.0\"   (50.8 × 101.6mm)   2 SKUs\n" +
    "STRIPS   4.0\" × 6.5\"   (101.6 × 165.1mm)  11-12 SKUs\n\n" +
    "All formats: 0.125\" bleed + 0.125\" safe zone"
  );

  addSubheading("DATA SOURCE RULES");
  addBody(
    "• Ingredient name ONLY from 'Ingredient Name (Label)' — no interpretation, no fallback\n" +
    "• Units: mg, g, IU — do NOT uppercase\n" +
    "• Brand: always GenoMAX² — exact casing with superscript ²\n" +
    "• 30 fields per SKU mapped to component layers (see field-mapping.json)"
  );

  addSubheading("LAYER NAMING CONVENTION");
  addCode(
    "Front Panel Layers:\n" +
    "  brand_name, module_code, biological_os_module,\n" +
    "  ingredient_name, descriptor, biological_system,\n" +
    "  variant_name, accent_rule,\n" +
    "  type_label, type_value, function_label, function_value,\n" +
    "  status_label, status_value,\n" +
    "  version_info, net_quantity\n\n" +
    "Back Panel Layers:\n" +
    "  supplement_facts_title, serving_info,\n" +
    "  ingredient_row_N, other_ingredients, dv_footnote,\n" +
    "  directions_label, directions_text,\n" +
    "  safety_label, safety_text,\n" +
    "  manufacturer_label, manufacturer_name, manufacturer_address,\n" +
    "  fda_disclaimer"
  );

  addSubheading("DEVELOPER HANDOFF FILES");
  addCode(
    "design-system/\n" +
    "  tokens/\n" +
    "    colors.json          Color variables (DTCG format)\n" +
    "    typography.json      Typography styles with field mappings\n" +
    "    spacing.json         Spacing tokens + format dimensions\n" +
    "    tokens.css           CSS custom properties ready for web\n" +
    "  components/\n" +
    "    component-spec.json  Component tree + format adaptations\n" +
    "  data/\n" +
    "    field-mapping.json   Excel → Component field mapping\n" +
    "  figma-scripts/\n" +
    "    build-all-components.js    Builds all 20 components\n" +
    "    build-explanation-page.js  Builds this page"
  );

  frame.x = 0;
  frame.y = 0;

  return { status: "Explanation page built" };
}

await buildExplanationPage();
