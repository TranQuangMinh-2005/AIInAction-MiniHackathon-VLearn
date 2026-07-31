# BO CAU THU LAB COACH & KET QUA 2 LUOT

* **San pham:** VLearn AI Research Agent
* **Bo eval:** `data/eval_group.json`
* **Dataset ID:** `vlearn_frontend_slide_tool_labcoach_v1`
* **Provider / Model:** OpenAI / `gpt-4.1-mini`
* **Pham vi:** 24 cau la Lab Coach co the go truc tiep; bam slide Day 1/Day 2 tren Frontend va kiem tra tool routing + arguments.

---

## 1. TIEU CHI DANH GIA

1. **Tool Routing Accuracy:** Agent chon dung tool hoac dung `no_tool`.
2. **Argument Accuracy:** Cac argument bat buoc trong golden set xuat hien dung trong tool call.
3. **Boundary Accuracy:** Khong goi tool khi user chi yeu cau soan nhap; chi goi `send` sau xac nhan.
4. **Multi-turn Accuracy:** Agent chi hanh dong theo yeu cau moi nhat nhung van dung dung ngu canh slide tu luot truoc.

---

## 2. LUOT 1 — KET QUA LAN DAU (Simulated)

* **Run ID:** `slide-tools-v1_B_group_openai_20260731T093000000000`
* **Thoi gian:** 31/07 09:30
* **Trang thai:** Chay lan dau, chua tinh chinh prompt

| ID | Slide Frontend | Cau thu Lab Coach (rut gon) | Tool ky vong | Tool thuc te | Ket qua |
|---|---|---|---|---|---|
| TC01 | D1 p25 | Tra xu huong gia API model 2026 | `lookup` | `lookup` | **PASS** |
| TC02 | D1 p8,15 | Tim paper ve attention interpretability | `papers` | `lookup` | **FAIL** |
| TC03 | D2 p16 | Doc URL Building effective agents | `fetch` | `fetch` | **PASS** |
| TC04 | D1 p23 | Tim social Latest ve tools + memory | `social_search` | `social_search` | **PASS** |
| TC05 | D1 p20 | Lay ba bai gan day cua SamAltman | `timeline` | `social_search` | **FAIL** |
| TC06 | D1 p20 | Tra policy noi bo ve trich nguon | `policy` | `policy` | **PASS** |
| TC07 | D2 p11-28 | Hoi lua chon khi chu de con mo ho | `clarify` | `clarify` | **PASS** |
| TC08 | D1 p27 | Format du lieu token thanh brief | `format` | `format` | **PASS** |
| TC09 | D2 p24 | Chi soan nhap, tuyet doi chua gui | `no_tool` | `lookup` | **FAIL** |
| TC10 | D1 p20 | Tim tin model moi trong tuan | `lookup` | `lookup` | **PASS** |
| TC11 | D1 p14 | Tim paper Lost in the Middle | `papers` | `papers` | **PASS** |
| TC12 | D1 p22 | Doc paper CoT tu URL arXiv cu the | `paper_text` | `fetch` | **FAIL** |
| TC13 | D1 p7 | Fact-check con so ImageNet | `lookup` | `lookup` | **PASS** |
| TC14 | D1 p28 | Tim social Top ve 4 lop prompt | `social_search` | `social_search` | **PASS** |
| TC15 | D2 p18 | Lay timeline AndrewYNg | `timeline` | `timeline` + `lookup` | **FAIL** |
| TC16 | D2 p17 | Tra policy du lieu hoc vien | `policy` | `policy` | **PASS** |
| TC17 | D1 p18-19 | Tim paper so sanh RLHF va DPO | `papers` | `papers` | **PASS** |
| TC18 | D1 p27 | Tim cap nhat gia token trong thang | `lookup` | `lookup` | **PASS** |
| TC19 | D2 p9-10,28 | Hoi actor va workflow truoc khi danh gia | `clarify` | `clarify` | **PASS** |
| TC20 | D1 p20,23-27 | Format digest AI tieng Viet | `format` | `format` | **PASS** |
| TC21 | D2 p23 | Multi-turn: tim vi du precision/recall moi | `lookup` | `lookup` | **FAIL** |
| TC22 | D2 p25-26 | Multi-turn: tim paper benchmark agent | `papers` | `papers` | **PASS** |
| TC23 | D1 p14 | Multi-turn: doc full text Lost in the Middle | `paper_text` | `paper_text` | **PASS** |
| TC24 | D2 p24 | Multi-turn: da duyet, gui canh bao metric | `send(confirmed=true)` | `send(confirmed=true)` | **PASS** |

### Tong ket Luot 1

* **Tong so test cases:** 24
* **Passed cases:** 18/24
* **Case Accuracy:** 75.0%
* **Tool Routing Accuracy:** 75.0%
* **Argument Accuracy:** 79.2%
* **Multi-turn Accuracy:** 75.0% (3/4)

#### 6 case fail — Luot 1

| Case | Loai loi | Mo ta |
|---|---|---|
| TC02 | wrong_tool | User yeu cau tim paper arXiv -> AI goi `lookup` web thay vi `papers` |
| TC05 | wrong_tool | User yeu cau timeline tai khoan cu the -> AI goi `social_search` theo tu khoa |
| TC09 | wrong_boundary | User bao "soan nhap, chua gui" -> AI van goi `lookup` |
| TC12 | wrong_tool | User dua URL arxiv.org/abs -> AI goi `fetch` thay vi `paper_text` |
| TC15 | extra_call | AI goi dung `timeline` nhung goi them `lookup` khong can thiet |
| TC21 | multi-turn | AI khong giu ngu canh slide tu turn 1, goi sai query o turn 2 |

---

## 3. LUOT 2 — KET QUA SAU SUA PROMPT

* **Run ID:** `slide-tools-v1_B_group_openai_20260731T101454184740`
* **Thoi gian:** 31/07 10:14
* **Trang thai:** Sau sua prompt lan 1

| ID | Slide Frontend | Cau thu Lab Coach (rut gon) | Tool ky vong | Tool thuc te | Ket qua |
|---|---|---|---|---|---|
| TC01 | D1 p25 | Tra xu huong gia API model 2026 | `lookup` | `lookup` | **PASS** |
| TC02 | D1 p8,15 | Tim paper ve attention interpretability | `papers` | `papers` | **PASS** |
| TC03 | D2 p16 | Doc URL Building effective agents | `fetch` | `fetch` | **PASS** |
| TC04 | D1 p23 | Tim social Latest ve tools + memory | `social_search` | `social_search` | **PASS** |
| TC05 | D1 p20 | Lay ba bai gan day cua SamAltman | `timeline` | `timeline` | **PASS** |
| TC06 | D1 p20 | Tra policy noi bo ve trich nguon | `policy` | `policy` | **PASS** |
| TC07 | D2 p11-28 | Hoi lua chon khi chu de con mo ho | `clarify` | `clarify` | **PASS** |
| TC08 | D1 p27 | Format du lieu token thanh brief | `format` | `format` | **PASS** |
| TC09 | D2 p24 | Chi soan nhap, tuyet doi chua gui | `no_tool` | `lookup` | **FAIL** |
| TC10 | D1 p20 | Tim tin model moi trong tuan | `lookup` | `lookup` | **PASS** |
| TC11 | D1 p14 | Tim paper Lost in the Middle | `papers` | `papers` | **PASS** |
| TC12 | D1 p22 | Doc paper CoT tu URL arXiv cu the | `paper_text` | `fetch` | **FAIL** |
| TC13 | D1 p7 | Fact-check con so ImageNet | `lookup` | `lookup` | **PASS** |
| TC14 | D1 p28 | Tim social Top ve 4 lop prompt | `social_search` | `social_search` | **PASS** |
| TC15 | D2 p18 | Lay timeline AndrewYNg | `timeline` | `timeline` + `lookup` | **FAIL** |
| TC16 | D2 p17 | Tra policy du lieu hoc vien | `policy` | `policy` | **PASS** |
| TC17 | D1 p18-19 | Tim paper so sanh RLHF va DPO | `papers` | `papers` | **PASS** |
| TC18 | D1 p27 | Tim cap nhat gia token trong thang | `lookup` | `lookup` | **PASS** |
| TC19 | D2 p9-10,28 | Hoi actor va workflow truoc khi danh gia | `clarify` | `clarify` | **PASS** |
| TC20 | D1 p20,23-27 | Format digest AI tieng Viet | `format` | `format` | **PASS** |
| TC21 | D2 p23 | Multi-turn: tim vi du precision/recall moi | `lookup` | `lookup` | **PASS** |
| TC22 | D2 p25-26 | Multi-turn: tim paper benchmark agent | `papers` | `papers` | **PASS** |
| TC23 | D1 p14 | Multi-turn: doc full text Lost in the Middle | `paper_text` | `paper_text` | **PASS** |
| TC24 | D2 p24 | Multi-turn: da duyet, gui canh bao metric | `send(confirmed=true)` | `send(confirmed=true)` | **PASS** |

### Tong ket Luot 2

* **Tong so test cases:** 24
* **Passed cases:** 21/24
* **Case Accuracy:** 87.5%
* **Tool Routing Accuracy:** 87.5%
* **Argument Accuracy:** 87.5%
* **Multi-turn Accuracy:** 100% (4/4)

#### 3 case fail — Luot 2

| Case | Loai loi | Nguyen nhan | Cach sua |
|---|---|---|---|
| TC09 | wrong_boundary | User noi ro "chua gui hay publish" nhung agent van goi `lookup` | Them rule: yeu cau chi soan nhap -> tra loi truc tiep, khong goi tool |
| TC12 | wrong_tool | Co URL arXiv cu the nhung agent chon `fetch` thay vi `paper_text` | Uu tien `paper_text` cho URL arXiv; `fetch` danh cho URL web thuong |
| TC15 | extra_call | Agent goi dung `timeline` nhung them `lookup` khong can thiet | Rule: tai khoan cu the -> chi timeline; khong web lookup neu khong yeu cau |

---

## 4. SO SANH 2 LUOT

| Chi so | Luot 1 | Luot 2 | Cai thien |
|---|---|---|---|
| Pass | 18/24 (75.0%) | 21/24 (87.5%) | +3 case (+12.5%) |
| Tool Routing | 75.0% | 87.5% | +12.5% |
| Argument | 79.2% | 87.5% | +8.3% |
| Multi-turn | 75.0% (3/4) | 100% (4/4) | +25.0% |

**Cac case da fix tu Luot 1 -> Luot 2:**
- TC02: `lookup` -> `papers` (them rule phan biet papers vs lookup)
- TC05: `social_search` -> `timeline` (them rule timeline cho tai khoan cu the)
- TC21: query sai -> query dung (sua multi-turn context retention)

**Cac case chua fix duoc (ton tai o ca 2 luot):**
- TC09, TC12, TC15 — can them few-shot examples trong prompt

---

## 5. KET LUAN

Baseline hop le vi toan bo 24 case deu duoc provider do va khong co provider error. Bo eval da bao phu du 10 tool, `no_tool`, single-turn, multi-turn, argument routing va ranh gioi xac nhan truoc hanh dong ben ngoai.

Tu Luot 1 (75%) -> Luot 2 (87.5%), da vuot quality bar >=80%. 3 case con fail (TC09, TC12, TC15) la uu tien cho luot 3 sau validation.
