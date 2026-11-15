#!/usr/bin/env bash
# يحمّل مكتبتي الحركة مرة واحدة إلى static/vendor ليخدمهما خادمكِ نفسه (دون أي اتصال بطرف ثالث من المتصفح).
set -euo pipefail
cd "$(dirname "$0")/../static" && mkdir -p vendor
curl -fsSL https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js -o vendor/gsap.min.js
curl -fsSL https://cdn.jsdelivr.net/npm/lenis@1.1.13/dist/lenis.min.js -o vendor/lenis.min.js
echo "تم. أعيدي تشغيل الخدمة: sudo systemctl restart tltd"
