# Phase 3 QA — Test Questions & Expected Answers

## Step 1: Upload the test documents

Upload these three files in this order:

| File | Document Type | Source Date |
|---|---|---|
| `test-data/blood_test_2025_06.txt` | `blood_test` | `2025-06-14` |
| `test-data/symptoms_2025.txt` | `journal` | `2025-07-01` |
| `test-data/supplements_2025.txt` | `supplement_list` | `2025-08-03` |

After uploading, check that the backend saved the data:
- `GET /lab-results` — should show a new test dated 2025-06-14 with ~14 markers
- `GET /symptom-entries` — should show fatigue, brain fog, muscle weakness, cold sensitivity entries
- `GET /supplement-entries` — should show Vitamin D, B12, Omega-3, Iron
- `GET /timeline` — should show events spanning 2025-06 through 2026-01

---

## Test Questions & Expected Answers

---

### 🔬 Lab Analysis

**Q: "What was my Vitamin D level in June 2025 and how does it compare to January 2026?"**

✅ Expected:
- June 2025: 24.1 nmol/L — **severely deficient** (below 50 nmol/L threshold)
- January 2026: 74.8 nmol/L — **normal range**
- Clear improvement of ~50 nmol/L over the 7-month period

---

**Q: "Is my Vitamin B12 high? Should I be worried?"**

✅ Expected:
- January 2026: 642 pmol/L — marked as **high** (reference ~200–950 depending on lab)
- The agent should note it's above the upper reference but may be explained by supplementation
- Should suggest discussing with a doctor but not be alarmist

---

**Q: "What were my iron levels?"**

✅ Expected:
- June 2025: Ferritin 18 ng/mL (low), Serum Iron 52 ug/dL (low), TIBC 390 (high)
- Together these indicate iron deficiency
- No iron data in January 2026 (supplement was stopped, no retest shown)

---

### 🔍 Pattern Detection

**Q: "Did my fatigue improve after I started taking supplements?"**

✅ Expected:
- Fatigue started in **July 2025**, described as persistent and heavy
- **August 3, 2025**: Started Vitamin D 2000 IU + B12 + Iron
- **September 2025**: Fatigue noticeably improving
- **October 2025**: Energy much better, no longer waking up tired
- The agent should connect: supplement start → gradual improvement timeline
- Should note this is a correlation, not proof of causation

---

**Q: "Is there a connection between my Vitamin D deficiency and my symptoms?"**

✅ Expected:
- June 2025: Vitamin D 24.1 nmol/L (severely deficient)
- July/August 2025: Fatigue, brain fog, cold sensitivity, muscle weakness — classic Vitamin D deficiency symptoms
- After supplementation: all symptoms resolved by October/November 2025
- The agent should flag this as a strong temporal correlation worth discussing with a doctor

---

**Q: "Why was I so tired in the summer of 2025?"**

✅ Expected:
- Two concurrent issues: Vitamin D deficiency (24.1 nmol/L) AND iron deficiency (ferritin 18, iron 52)
- Both are known causes of fatigue
- Both were treated starting August 2025
- Fatigue resolved by October 2025
- Agent should mention both deficiencies as possible contributors

---

**Q: "Did my B12 supplement affect my lab results?"**

✅ Expected:
- Started B12 1000 mcg daily on August 3, 2025 (B12 was normal at 248 pmol/L then)
- By January 2026: B12 is 642 pmol/L — **high**, likely from the high-dose supplementation
- The agent should connect: started high-dose B12 supplement → B12 level elevated in next test

---

### 📅 Timeline

**Q: "Give me a summary of my health in 2025"**

✅ Expected chronological narrative:
1. June 2025 — Blood test: Vitamin D deficient, iron deficient, MCV/MCH low
2. July 2025 — Fatigue, brain fog, cold sensitivity, muscle weakness
3. August 2025 — Started Vitamin D, B12, Iron supplements
4. September 2025 — Fatigue improving, muscle weakness resolved
5. October 2025 — Energy restored, symptoms largely gone
6. November 2025 — Feeling good, stopped iron supplement

---

**Q: "What health events happened between June and December 2025?"**

✅ Expected:
- Should list the blood test (June 14), symptom entries through the summer/autumn, and supplement changes
- Clear chronological order

---

**Q: "When did I start taking supplements and what were they for?"**

✅ Expected:
- August 3, 2025: Vitamin D 2000 IU (Vitamin D deficiency), B12 1000 mcg (preventive), Iron 65 mg (iron deficiency)
- March 2024: Omega-3 (cardiovascular health)
- Agent should connect supplements to the lab results that prompted them

---

### 🚨 Routing sanity checks

These test that the supervisor routes to the right agent:

| Question | Expected route | Wrong if... |
|---|---|---|
| "What is my hemoglobin?" | `lab_analysis` | Answer is vague or mentions searching documents |
| "What happened to my health this year?" | `timeline` | Just returns lab values without narrative |
| "Why was I tired in summer 2025?" | `pattern_detection` | Only returns lab values without connecting to symptoms |
| "What did my journal say about brain fog?" | `rag` | Returns structured data instead of document quotes |
