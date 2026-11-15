# الخط العربي المحلي

لم يُضَف ملف خط إلى المشروع (لم يتوفر خط عربي مرخّص وقت التنفيذ)، فتستخدم الواجهة خط النظام العربي. ولتوحيد المظهر على كل الأجهزة:

1. نزّلي خطًا عربيًا مفتوح الترخيص (مثل Tajawal أو Readex Pro أو Noto Sans Arabic) بصيغة `woff2`، وضعيه هنا: `static/fonts/tltd-sans.woff2`.
2. أضيفي هذه القاعدة في أعلى `static/style.css`:

```css
@font-face {
  font-family: "TLTD Sans";
  src: url("/static/fonts/tltd-sans.woff2") format("woff2");
  font-weight: 400 800;
  font-display: swap;
}
```

المتغير `--font` في `style.css` يبدأ باسم `TLTD Sans` أصلًا، فلا حاجة لتعديل أي شيء آخر.
3. ارفعي رقم الإصدار في `static/sw.js` (`tltd-v3` إلى `tltd-v4`) كي لا يُعرض الإصدار القديم.
4. حافظي على ملف الترخيص (OFL) بجانب الخط.

لا تحمّلي الخط من CDN: تمنع ذلك سياسة CSP وتضر بالخصوصية.
