# معمارية مُطابق الصور

يتبع التطبيق فصلًا واضحًا بين العرض والخدمات والتخزين. `main.py` يملك `QApplication` ومرجع `MainWindow` طوال event loop. الصفحات لا تنفذ I/O طويلًا؛ `CopyWorker` يعمل داخل `QThread` ويرسل بيانات فقط عبر إشارات Qt.

تسلسل العملية:

1. تبني صفحة العملية `ProcessingSettings` وتطلب المعاينة.
2. تنشئ النافذة رقم عملية وعاملًا وخيطًا محفوظي المرجع.
3. تنفذ `ProcessingService` القراءة والفهرسة والمطابقة والفحص والنسخ والتقرير.
4. يصدر العامل إشارة نهائية واحدة تحمل رقم العملية، ثم `worker_finished`.
5. يتوقف الخيط ويُحذف العامل والخيط بـ`deleteLater`؛ بعدها فقط تعرض النافذة النتيجة دون event loop متداخل.
6. يتجاهل حارس النهاية أي إشارة مكررة أو قديمة.

الحالة تنتقل عبر `OperationState`: IDLE، VALIDATING، SCANNING، MATCHING، COPYING، GENERATING_REPORT، FINALIZING، ثم COMPLETED أو PARTIAL_SUCCESS أو FAILED أو CANCELLED. الأزرار مشتقة من الحالة.

SQLite في `%LOCALAPPDATA%\MutabiqAlSuwar\data\mutabiq.db`. المعاملات قصيرة، WAL مفعّل، والاتصال يُغلق حتميًا على Windows. المنشور JSON هو مرجع Undo، ولا يسمح التراجع بمسار خارج الوجهة أو ملف تغير حجمه/تاريخه/هاشه.

الثيم مصدره `ui/theme.py`: لوحة semantic tokens واحدة تولّد `QPalette` للمكونات الأصلية وQSS للمكونات المخصصة. `utils/contrast.py` يدقق أزواج النص والخلفية. الجداول تستخدم `QAbstractTableModel` وproxy للتصفية.
