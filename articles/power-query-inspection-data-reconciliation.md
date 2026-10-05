# Power Query لتوحيد سجلات الفحص دون فقد المعنى

**احمد خلوي | Ahmed Khalawy**

![صورة شخصية لـاحمد خلوي](https://github.com/Ahmedhosny95/Ahmedhosny95/raw/main/ahmed-khalawy-portrait.jpeg)

دمج ملفات الفحص قد ينتج جدولًا مرتبًا، بينما تتغير هوية السجل أو معنى تاريخه ووحدته. هذا تمرين قابل للتنزيل لحماية هذه المعاني قبل إعداد التقرير. جميع بياناته مصطنعة؛ لا تمثل شركة أو نتيجة فحص فعلية، ولا تتضمن حدود قبول منتج.

## ملفات التدريب

نزّل الملفات في مجلد مستقل، واحتفظ بالمصدرين كما هما:

- [CSV المصدر A](https://github.com/Ahmedhosny95/Ahmedhosny95/raw/refs/heads/main/articles/assets/seo064/inspections_a.csv) و[CSV المصدر B](https://github.com/Ahmedhosny95/Ahmedhosny95/raw/refs/heads/main/articles/assets/seo064/inspections_b.csv): خمسة سجلات لكل ملف، بعناوين أعمدة مختلفة.
- [استعلام التوحيد M](https://github.com/Ahmedhosny95/Ahmedhosny95/raw/refs/heads/main/articles/assets/seo064/seo064-normalize.m) و[استعلام التسوية M](https://github.com/Ahmedhosny95/Ahmedhosny95/raw/refs/heads/main/articles/assets/seo064/seo064-reconciliation.m).
- [الصفوف المتوقعة CSV](https://github.com/Ahmedhosny95/Ahmedhosny95/raw/refs/heads/main/articles/assets/seo064/expected-normalized.csv)، [تسوية متوقعة CSV](https://github.com/Ahmedhosny95/Ahmedhosny95/raw/refs/heads/main/articles/assets/seo064/expected-reconciliation.csv) و[تعريف النتائج JSON](https://github.com/Ahmedhosny95/Ahmedhosny95/raw/refs/heads/main/articles/assets/seo064/expected-reconciliation.json).
- [تعليمات التشغيل والقيود](https://github.com/Ahmedhosny95/Ahmedhosny95/raw/refs/heads/main/articles/assets/seo064/README.md) و[مدقق الملفات Python](https://github.com/Ahmedhosny95/Ahmedhosny95/raw/refs/heads/main/articles/assets/seo064/validate_fixture.py).

## خطوات تمنع التحويل الصامت

**ابدأ بالمعنى.** المعرف `00123` نص، وليس الرقم `123`. اقرأ الحقول الخام كنص منذ المصدر؛ إعادة تنسيق رقم فقد أصفاره لا تعيد هويته الأصلية. الاكتشاف التلقائي لأنواع CSV يحتاج مراجعة، كما توضح [وثائق أنواع البيانات](https://learn.microsoft.com/en-us/power-query/data-types).

**عرّف كل مصدر قبل الجمع.** أعد تسمية الأعمدة إلى حقول موحدة، وأضف `SourceFile` و`SourceRow` قبل أي دمج أو ترشيح. رقم الصف هنا ترتيب سجل البيانات بعد العنوان، وليس رقم السطر الفيزيائي لكل CSV. الإلحاق يعتمد على أسماء الأعمدة؛ اختلاف الاسم قد ينشئ عمودًا آخر وقيمًا فارغة وفق [وثائق Append](https://learn.microsoft.com/en-us/power-query/append-queries).

**ثبّت التاريخ والثقافة.** المصدر A يعلن `dd/MM/yyyy` و`en-GB`، بينما B يعلن `MM/dd/yyyy` و`en-US`. لذلك `01/02/2026` يعني الأول من فبراير في A والثاني من يناير في B. استخدم `Date.FromText` مع `Format` و`Culture` معلومين؛ نجاح التحويل وحده لا يثبت صحة المعنى. راجع [خيارات الدالة](https://learn.microsoft.com/en-us/powerquery-m/date-fromtext).

**حوّل الوحدة مع إبقاء الأصل.** احتفظ بالقراءة والوحدة الخام، ثم أضف `ReadingMM`: قيمة `mm` تبقى كما هي، و`cm` تضرب في عشرة، استنادًا إلى [بادئات SI](https://www.nist.gov/pml/owm/metric-si-prefixes). الوحدة `inch` خارج سياسة الوحدتين في التمرين؛ لا تُحوّل بالتخمين ولا توصف بأنها وحدة باطلة.

**أظهر المشكلات دون حذف.** يحفظ الاستعلام القيم الخام، ويستخدم `try` لرصد أخطاء التاريخ والقراءة، ثم يسجل النقص والوحدة غير المدعومة والمعرف المكرر في `Issues`. التكرار سبب للمراجعة في هذا التمرين، وليس مبررًا تلقائيًا للحذف. راجع [معالجة الأخطاء](https://learn.microsoft.com/en-us/power-query/error-handling).

## تجربة وتسوية مقترحتان

أنشئ استعلامًا فارغًا باسم `SEO064_Normalized`، والصق ملف التوحيد في المحرر المتقدم. عدّل `InputFolder` إلى مجلد التدريب، ثم أضف استعلام التسوية. قارن القيم بعد ترتيب `SourceFile` و`SourceRow`، بما فيها التواريخ الفعلية وأصفار المعرفات.

| المصدر | المدخلات | الصفوف المحفوظة | جاهزة للتدريب | تحتاج مراجعة |
| --- | --- | --- | --- | --- |
| A | 5 | 5 | 1 | 4 |
| B | 5 | 5 | 1 | 4 |

التوقع: عشرة سجلات محفوظة، منها اثنان جاهزان وثمانية للمراجعة. تبقى وسوم المصدر ثمانية `Pass` وواحد `Fail` وواحد فارغ. `ready_for_demo` تعني اجتياز قواعد بيانات التمرين؛ لا تعني قبول المنتج، و`Pass` وصف من المصدر لا قرار محسوب من القراءة.

تحققت الملفات والنتائج المحددة مسبقًا في Python، بما يشمل الأعداد والأصفار والتواريخ والوحدات. **لم تُنفذ الاستعلامات في Power Query أو Excel؛ كود M مقترح للتجربة والمراجعة.** لا يعادل تحقق Python تشغيل محرك M. قبل الاستخدام الفعلي، راجع قواعد المصدر والصلاحيات ومواصفات القبول لدى جهتك.

---

احمد خلوي مهندس جودة أول بالرياض. أنظمة الجودة والتحسين المستمر وتحليل البيانات في التصنيع والإنشاءات.

[الموقع الشخصي](https://ahmedkhalawy.com/) · [LinkedIn](https://www.linkedin.com/in/ahmed-khalawy-513a271a1/)
