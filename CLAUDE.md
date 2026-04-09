# GenoMAX² — Project Context for AI Agents

> **חשוב לכל סוכן שמתחיל עבודה בפרויקט זה:** קרא קובץ זה תחילה לפני כל פעולה!

---

## מה הפרויקט הזה?
GenoMAX² הוא מערכת ייצור תוויות (Label Production System) לתוספי תזונה.
המערכת מייצרת תוויות JPG מוכנות לדפוס עבור 168 מוצרים בפורמטים שונים.

---

## ארכיטקטורה טכנית

### מנוע הרינדור — הכי חשוב!
- **שפה:** Python + ReportLab (⚠️ לא HTML/Playwright!)
- **סקריפט ייצור:** `scripts/render-production-v6.py` ← זו הגרסה הרשמית
- **פונט:** IBM Plex (Mono, Sans, Condensed) — `design-system/fonts/`
- **נתונים:** `design-system/data/production-labels-maximo-v4.json` + `production-labels-maxima-v4.json`
- **פלט:** `design-system/production-v6/` (FORMAT → SKU → front.jpg + back.jpg)

### GitHub Repositories
```
hemichaeli/genomax-renderer   → מנוע הרינדור (הראשי — כאן אנחנו עובדים)
hemichaeli/genomax2-api       → Backend API
hemichaeli/genomax2-frontend  → Frontend React/TypeScript
```

### פורמטי תווית
| Format  | גודל          | הערה                |
|---------|---------------|---------------------|
| BOTTLE  | 6" × 2.5"     | הנפוץ ביותר         |
| JAR     | 8.5" × 2"     | שוליים צרים (short) |
| POUCH   | 5" × 4"       | טקסט מצומצם 20%    |
| DROPPER | 2" × 4"       | צר מאוד (narrow)    |
| STRIPS  | 4" × 6.5"     | גבוה (tall)         |

---

## מה בוצע — V6 (אפריל 2026)

### בעיות שתוקנו בגרסת V6
- ✅ Text overflow — SAFE_MARGIN הועלה מ-12px ל-32px
- ✅ setCharSpace leak — ReportLab לא איפס tracking בין פסקאות (תוקן ב-`_d()`)
- ✅ QR collision — QR_TEXT_GAP הועלה מ-8px ל-24px
- ✅ Footer clipping — STRIP_H הועלה ל-16px עם floor protection
- ✅ Font shrink cascade — אוטומטי: tracking → font size → ellipsis
- ✅ Front column overlap — ucol הוקטן מ-`colw-4` ל-`colw-8`

### סטטוס הרינדור
- **168 SKUs רונדרו ✅ ללא שגיאות** (אפריל 2026)
- פלט מקומי: `design-system/production-v6/`
- Google Drive: `G:\My Drive\Work\GenoMAX²\Design\Lables\GenoMAX_V6_FINAL`

---

## פקודות עבודה

```bash
# רינדור אימות — 5 דוגמאות, אחת מכל פורמט (תמיד לפני full!)
python scripts\render-production-v6.py --validate

# רינדור מלא של כל 168 SKUs
python scripts\render-production-v6.py --full

# סנכרון עם GitHub
git pull origin main
git push origin main
```

---

## חוקי עיצוב מחייבים

1. **אין לגעת בתכנים** (טקסטים, צבעים, מיקומים) ללא אישור מפורש
2. **SAFE_MARGIN = 32** — לא לרדת ממספר זה לעולם
3. **floor = strip_top + SAFE_MARGIN** — טקסט לא חוצה גבול זה
4. **בדיקה חובה** אחרי כל שינוי: `--validate` לפני `--full`
5. **V6 היא הגרסה הרשמית היחידה** — לא לחזור ל-V5 ולא לשכתב logic עיצובי

---

## נושאים פתוחים
- [ ] אישור עיצוב סופי מהלקוח (נשלח לאישור אפריל 2026)
- [ ] רינדור MAXima לאחר אישור הלקוח
- [ ] אינטגרציה עם ה-API לאוטומציה מלאה

---

## פרויקטים קשורים (נפרדים)
- `C:\Projects\Sapir-CRM` — אוטומציית ביטולים, iCount
- `C:\Projects\QUANTUM` — CRM ו-Dashboard נדל"ן
