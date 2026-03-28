# EMP Cloud — Business Rules V3 (Deep Compliance, Edge Cases & Production Scenarios)

Continuation of BUSINESS_RULES.md (~200 rules) and BUSINESS_RULES_V2.md (~150 rules). This document adds 680+ rules covering Indian labor law compliance, international HR, edge cases, integrations, security, accessibility, and real-world production scenarios that commonly break.

**Grand total across all 3 documents: 1,030+ business rules**

Each should be tested and categorized as: ENFORCED / NOT ENFORCED / NOT IMPLEMENTED / PARTIAL

---

## 31. INDIAN LABOR LAW — SHOPS & ESTABLISHMENTS ACT

| # | Rule | Priority |
|---|------|----------|
| SEA001 | Maximum working hours must not exceed 9 hours/day and 48 hours/week (state-specific variations apply) | CRITICAL |
| SEA002 | Spread-over of work including rest intervals must not exceed 10.5 hours in a day | HIGH |
| SEA003 | Every employee must receive at least one full day off per week (Sunday or designated day) | CRITICAL |
| SEA004 | Opening and closing hours of the establishment must be configurable per state registration | MEDIUM |
| SEA005 | Women employees — working hours restricted after 9 PM in states where night shift rules apply (unless exempted) | HIGH |
| SEA006 | System must track Shop & Establishment registration number per location/branch | HIGH |
| SEA007 | Annual leave entitlement per S&E Act must be minimum as per state rule (e.g., 15 days in Maharashtra, 12 in Karnataka) | HIGH |
| SEA008 | Sick leave entitlement per S&E Act (e.g., 7 days paid sick leave in some states) | HIGH |
| SEA009 | Casual leave entitlement tracked per state-specific rule | MEDIUM |
| SEA010 | Employment of children under 14 must be blocked by the system — DOB validation at onboarding | CRITICAL |
| SEA011 | Employment of young persons (14-18) must enforce reduced hours and no night work | HIGH |
| SEA012 | Notice period for termination must meet state-specific minimum (e.g., 30 days or 1 month pay in lieu) | HIGH |
| SEA013 | System must generate the required statutory registers (Form A, B, etc.) per state | MEDIUM |
| SEA014 | Overtime beyond 48 hours/week must be flagged and computed at 2x rate | CRITICAL |
| SEA015 | Festival advance/bonus — system must support advance payment against upcoming bonus | LOW |

## 32. INDIAN LABOR LAW — FACTORIES ACT

| # | Rule | Priority |
|---|------|----------|
| FA001 | Weekly working hours must not exceed 48 hours for factory employees | CRITICAL |
| FA002 | Daily working hours must not exceed 9 hours | CRITICAL |
| FA003 | Overtime must be calculated at 2x the ordinary rate of wages | CRITICAL |
| FA004 | Total overtime hours must not exceed 50 hours per quarter (extendable to 75 with permission) | HIGH |
| FA005 | Minimum half-hour rest break after 5 hours of continuous work | HIGH |
| FA006 | Annual leave with wages — 1 day for every 20 days worked (adults), 1 for every 15 (children) | HIGH |
| FA007 | Canteen facility mandatory if 250+ workers — system must track worker count per factory | MEDIUM |
| FA008 | Creche facility mandatory if 30+ women workers — system must flag non-compliance | HIGH |
| FA009 | Safety officer appointment mandatory if 1000+ workers | MEDIUM |
| FA010 | Welfare officer appointment mandatory if 500+ workers | MEDIUM |
| FA011 | First aid facility — at least one first-aid box per 150 workers | LOW |
| FA012 | System must track factory license number and renewal date per location | HIGH |
| FA013 | Dangerous operations — employees in hazardous areas must have medical fitness certificate on file | HIGH |
| FA014 | Night shift for women — allowed only with safeguards (transport, security) per 2021 amendment | HIGH |
| FA015 | System must generate statutory returns (Form 21, 22, etc.) for factory inspector submissions | MEDIUM |

## 33. INDIAN LABOR LAW — PAYMENT OF WAGES ACT

| # | Rule | Priority |
|---|------|----------|
| PW001 | Wages must be paid before the 7th of the following month (establishments with <1000 employees) | CRITICAL |
| PW002 | Wages must be paid before the 10th of the following month (establishments with 1000+ employees) | CRITICAL |
| PW003 | Total deductions from wages must not exceed 50% of gross wages in any pay period | CRITICAL |
| PW004 | Only authorized deductions permitted: PF, ESI, TDS, professional tax, authorized advances, court orders | HIGH |
| PW005 | Fines imposed on employees must not exceed 3% of wages | HIGH |
| PW006 | Fines can only be imposed for acts/omissions specified in a displayed notice | MEDIUM |
| PW007 | Wages of terminated employee must be paid within 2 working days of termination | CRITICAL |
| PW008 | Wages of resigned employee must be paid on or before the next regular pay date | HIGH |
| PW009 | Delay in wage payment beyond statutory deadline must trigger system alert to HR/Admin | HIGH |
| PW010 | Wage slip must be issued to every employee — system must auto-generate and distribute | HIGH |
| PW011 | Payment mode must be bank transfer for establishments in notified areas — cash payment flagged | MEDIUM |
| PW012 | Unauthorized deduction (not in approved list) must be rejected by payroll system | CRITICAL |
| PW013 | Advance recovery installment must not exceed the agreed EMI amount | HIGH |
| PW014 | System must maintain a wage register (Form III) as required by the Act | MEDIUM |

## 34. INDIAN LABOR LAW — MINIMUM WAGES ACT

| # | Rule | Priority |
|---|------|----------|
| MW001 | Minimum wage rates must be configurable per state, per skill level (unskilled/semi-skilled/skilled/highly-skilled) | CRITICAL |
| MW002 | System must validate that no employee's basic + DA is below applicable minimum wage | CRITICAL |
| MW003 | Minimum wage revision notification — when state government revises rates, system must flag non-compliant employees | HIGH |
| MW004 | Different minimum wages for different zones within a state (Zone A, B, C) must be supported | HIGH |
| MW005 | VDA (Variable Dearness Allowance) revision (typically every 6 months) must be tracked and applied | HIGH |
| MW006 | Overtime for minimum wage employees must be at 2x the minimum rate, not the actual rate | HIGH |
| MW007 | Piece-rate workers — minimum wage guaranteed regardless of output | HIGH |
| MW008 | Part-time employees — pro-rata minimum wage must still be enforced | HIGH |
| MW009 | Apprentices — minimum wage rules may differ; stipend must meet Apprentices Act minimum | MEDIUM |
| MW010 | System must generate a report of employees below minimum wage after any revision | HIGH |

## 35. INDIAN LABOR LAW — PAYMENT OF BONUS ACT

| # | Rule | Priority |
|---|------|----------|
| PB001 | Bonus applicable to employees drawing salary up to Rs 21,000/month | CRITICAL |
| PB002 | Minimum bonus is 8.33% of salary or Rs 100, whichever is higher | CRITICAL |
| PB003 | Maximum bonus is 20% of salary | HIGH |
| PB004 | Bonus calculation ceiling — salary capped at Rs 7,000/month for calculation purposes | HIGH |
| PB005 | Employee must have worked for at least 30 days in the accounting year to be eligible | HIGH |
| PB006 | Disqualification — employee dismissed for fraud, violent behavior, theft, or sabotage | MEDIUM |
| PB007 | Bonus must be paid within 8 months from the close of the accounting year | HIGH |
| PB008 | Allocable surplus calculation — system must track and compute per statutory formula | MEDIUM |
| PB009 | Set-on and set-off — carried forward surplus/deficit must be tracked across years (max 4 years) | MEDIUM |
| PB010 | New establishments — exempt from bonus for first 5 years (or until profit, whichever is earlier) | MEDIUM |
| PB011 | Bonus register (Form C) must be generated by the system | MEDIUM |
| PB012 | Proportionate bonus for employees who joined mid-year | HIGH |

## 36. INDIAN LABOR LAW — PAYMENT OF GRATUITY ACT (EXTENDED)

| # | Rule | Priority |
|---|------|----------|
| GR001 | Gratuity payable on termination after 5 years of continuous service (superannuation, resignation, death, disability) | CRITICAL |
| GR002 | For death/disability, 5-year requirement is waived | CRITICAL |
| GR003 | Formula: 15 days wages x years of service / 26 (for monthly-rated), / 30 (for piece-rated) | CRITICAL |
| GR004 | Maximum gratuity cap is Rs 20,00,000 — system must enforce ceiling | HIGH |
| GR005 | Continuous service — breaks due to sickness, accident, authorized leave, lock-out, or strike not illegal do not break continuity | HIGH |
| GR006 | Gratuity can be forfeited wholly or partly if termination is for willful omission/negligence causing damage, or riotous/disorderly conduct, or moral turpitude offense | MEDIUM |
| GR007 | Nomination — every employee must file Form F (nomination) within 30 days of completing 1 year | HIGH |
| GR008 | Nomination update on marriage, divorce, death of nominee — system must prompt employee | HIGH |
| GR009 | Gratuity must be paid within 30 days of it becoming payable — delay triggers 10% interest | HIGH |
| GR010 | System must track gratuity liability per employee for accounting/provisioning | HIGH |
| GR011 | Gratuity fund trust (if applicable) — contributions must be tracked | MEDIUM |
| GR012 | Seasonal employees — 5 years = 3 years of actual service | LOW |

## 37. INDIAN LABOR LAW — EPF ACT (EXTENDED)

| # | Rule | Priority |
|---|------|----------|
| EPF001 | EPF mandatory for establishments with 20+ employees | CRITICAL |
| EPF002 | Employee contribution: 12% of (basic + DA), deducted from wages | CRITICAL |
| EPF003 | Employer contribution: 12% of (basic + DA), split as 3.67% EPF + 8.33% EPS | CRITICAL |
| EPF004 | EPS contribution capped at 8.33% of Rs 15,000 (Rs 1,250/month max) | HIGH |
| EPF005 | Admin charges: 0.50% of (basic + DA) by employer | HIGH |
| EPF006 | EDLI contribution: 0.50% of (basic + DA) by employer, capped at Rs 15,000 wage | HIGH |
| EPF007 | UAN (Universal Account Number) must be generated/linked for every eligible employee | CRITICAL |
| EPF008 | New employee — EPF enrollment within first month of joining | HIGH |
| EPF009 | International workers — separate PF provisions, no EPS if from country with SSA (Social Security Agreement) | MEDIUM |
| EPF010 | Voluntary PF (VPF) — employee can contribute above 12%, system must support this | MEDIUM |
| EPF011 | PF withdrawal — employee must be separated; partial withdrawal only for specified purposes (housing, medical, marriage) | HIGH |
| EPF012 | PF transfer on job change — system must support transfer-in/transfer-out via Form 13 | HIGH |
| EPF013 | Monthly ECR (Electronic Challan cum Return) — system must generate in EPFO format | CRITICAL |
| EPF014 | Annual PF return — Form 3A and Form 6A generation | HIGH |
| EPF015 | PF interest rate — system must apply current EPFO-declared rate (compounding annually) | MEDIUM |
| EPF016 | EPF tax: contribution above Rs 2.5L/year (5L if no employer contribution) — interest taxable | MEDIUM |
| EPF017 | Employees joining at age 58+ — no EPS contribution, full 12% to EPF | HIGH |
| EPF018 | Opted-out employees (basic > Rs 15,000 at joining before Sep 2014) — respect opt-out status | MEDIUM |

## 38. INDIAN LABOR LAW — ESI ACT (EXTENDED)

| # | Rule | Priority |
|---|------|----------|
| ESI001 | ESI applicable when gross salary is Rs 21,000/month or below (Rs 25,000 for disabled) | CRITICAL |
| ESI002 | Employee contribution: 0.75% of gross wages | CRITICAL |
| ESI003 | Employer contribution: 3.25% of gross wages | CRITICAL |
| ESI004 | ESI applicable to establishments with 10+ employees (20+ in some states) | HIGH |
| ESI005 | Once covered, employee continues for full contribution period even if salary exceeds threshold mid-period | HIGH |
| ESI006 | Contribution period: April-September and October-March | HIGH |
| ESI007 | Benefit period lags by 6 months — contributions in Apr-Sep yield benefits Jan-Jun next | MEDIUM |
| ESI008 | ESIC registration number must be tracked per establishment/branch | HIGH |
| ESI009 | Monthly ESI challan — system must generate in ESIC format | HIGH |
| ESI010 | Half-yearly return — system must generate | HIGH |
| ESI011 | Sickness benefit — employee gets 70% of wages for up to 91 days | MEDIUM |
| ESI012 | Maternity benefit under ESI — full wages for 26 weeks (takes precedence over Maternity Benefit Act for ESI-covered employees) | HIGH |
| ESI013 | Disablement benefit — temporary and permanent, tracked separately | MEDIUM |
| ESI014 | Dependents benefit — payable on death of insured person, system must track nominees | MEDIUM |

## 39. INDIAN LABOR LAW — MATERNITY BENEFIT ACT (EXTENDED)

| # | Rule | Priority |
|---|------|----------|
| MB001 | Maternity leave: 26 weeks for first two children, 12 weeks for third+ | CRITICAL |
| MB002 | Maximum 8 weeks can be taken before expected delivery date | HIGH |
| MB003 | Eligibility: employee must have worked for at least 80 days in the 12 months preceding expected delivery | HIGH |
| MB004 | Maternity benefit = average daily wage for the period of absence | HIGH |
| MB005 | Commissioning mother (surrogacy) — 12 weeks from date child is handed over | HIGH |
| MB006 | Adopting mother — 12 weeks from date of adoption (child below 3 months) | HIGH |
| MB007 | Miscarriage/MTP — 6 weeks leave from date of miscarriage | HIGH |
| MB008 | Tubectomy — 2 weeks leave | MEDIUM |
| MB009 | Illness arising out of pregnancy — additional 1 month leave | MEDIUM |
| MB010 | Creche facility mandatory in establishments with 50+ employees — system must track | HIGH |
| MB011 | Creche — mother allowed 4 visits per day including travel time | MEDIUM |
| MB012 | Work from home — option must be available after maternity leave if nature of work permits (employer discretion) | MEDIUM |
| MB013 | No termination/dismissal during maternity leave period | CRITICAL |
| MB014 | No adverse change to conditions of service during maternity leave | HIGH |
| MB015 | Maternity bonus/medical bonus — Rs 3,500 if no pre-natal/post-natal care provided by employer | MEDIUM |

## 40. INDIAN LABOR LAW — POSH ACT (SEXUAL HARASSMENT)

| # | Rule | Priority |
|---|------|----------|
| POSH001 | Internal Complaints Committee (IC) must be constituted — system tracks IC members | CRITICAL |
| POSH002 | IC must have a presiding officer who is a senior woman employee | HIGH |
| POSH003 | IC must have an external member from an NGO/women's organization | HIGH |
| POSH004 | At least half of IC members must be women | HIGH |
| POSH005 | IC member tenure — maximum 3 years, system tracks expiry | MEDIUM |
| POSH006 | Complaint filing — must be within 3 months of the incident (extendable to 6 by IC) | HIGH |
| POSH007 | Anonymous complaints — system must support intake but inform complainant that investigation requires identity | MEDIUM |
| POSH008 | Complaint against IC member — must be redirected to Local Complaints Committee (LCC) | HIGH |
| POSH009 | Inquiry must be completed within 90 days | HIGH |
| POSH010 | Conciliation — possible before inquiry if complainant requests, but no monetary settlement | MEDIUM |
| POSH011 | Interim relief — transfer complainant or respondent, grant leave to complainant | HIGH |
| POSH012 | Confidentiality — identity of complainant, respondent, and witnesses must be protected | CRITICAL |
| POSH013 | Annual report — system must generate POSH annual report (number of complaints, disposed, pending) | HIGH |
| POSH014 | Employer penalty for non-compliance — system must flag if IC is not constituted | HIGH |
| POSH015 | POSH policy acknowledgment — every employee must acknowledge during onboarding | HIGH |

## 41. INDIAN LABOR LAW — EQUAL REMUNERATION & INDUSTRIAL DISPUTES

| # | Rule | Priority |
|---|------|----------|
| ER001 | No discrimination in pay between men and women for same work or similar nature of work | CRITICAL |
| ER002 | System must support gender pay gap analysis report | HIGH |
| ER003 | No discrimination in recruitment, promotion, training based on gender | HIGH |
| ER004 | System must track pay parity metrics — median pay by gender, by role level | MEDIUM |
| ID001 | Retrenchment of workmen — applicable only to those who have worked 240+ days in 12 months | HIGH |
| ID002 | Retrenchment — last-come-first-go rule (LIFO) unless justified | HIGH |
| ID003 | Retrenchment compensation — 15 days average pay for every completed year of service | HIGH |
| ID004 | One month notice or wages in lieu required for retrenchment | HIGH |
| ID005 | Government permission required for retrenchment in establishments with 100+ workers | CRITICAL |
| ID006 | Layoff — 50% of basic + DA payable for layoff period (up to 45 days) | HIGH |
| ID007 | Closure of establishment — 60 days notice to government required (100+ workers) | HIGH |
| ID008 | Strike/lockout — system must track and handle attendance/pay accordingly | MEDIUM |
| ID009 | Standing orders — must be certified and displayed; system can store and distribute digitally | MEDIUM |
| ID010 | Voluntary retirement scheme (VRS) — minimum 15 days salary per year of service | MEDIUM |

## 42. INDIAN LABOR LAW — CONTRACT LABOUR & APPRENTICES

| # | Rule | Priority |
|---|------|----------|
| CL001 | Principal employer must obtain registration if employing 20+ contract workers | HIGH |
| CL002 | Contractor must obtain license from appropriate authority | HIGH |
| CL003 | System must track contractor registration number and license validity | HIGH |
| CL004 | Contract workers entitled to minimum wages — principal employer is ultimately liable | CRITICAL |
| CL005 | Canteen, rest rooms, drinking water, first aid must be provided to contract workers (per threshold) | MEDIUM |
| CL006 | Payment of wages — if contractor fails to pay, principal employer must pay directly | HIGH |
| CL007 | System must maintain a register of contract workers (name, nature of work, hours, wages) | HIGH |
| CL008 | Contract labour must not be used for core/perennial work — system can flag long-tenure contracts | MEDIUM |
| AP001 | Apprentice stipend must not be less than prescribed minimum (varies by trade and year) | HIGH |
| AP002 | Apprentice training period must be tracked — 6 months to 3 years depending on trade | HIGH |
| AP003 | No obligation to employ apprentice after training, but system tracks offer status | MEDIUM |
| AP004 | Apprentice ratio — must not exceed prescribed ratio per designated trade | MEDIUM |
| AP005 | Apprentice must be registered with RDAT/BOAT — system tracks registration number | HIGH |
| AP006 | Apprentice cannot be treated as regular employee for PF/ESI purposes unless explicitly opted | MEDIUM |

## 43. INTERNATIONAL HR — MULTI-CURRENCY PAYROLL

| # | Rule | Priority |
|---|------|----------|
| MC001 | Each country entity must have a primary currency for payroll processing | CRITICAL |
| MC002 | Exchange rate source must be configurable (manual, API — e.g., forex service) | HIGH |
| MC003 | Exchange rate lock date — rate frozen on payroll processing date, not payment date | HIGH |
| MC004 | Expat employees — salary split between home and host country currencies | HIGH |
| MC005 | Reimbursements in foreign currency — converted at rate on date of expense | HIGH |
| MC006 | Currency rounding rules per country (e.g., Japan has no decimals, Bahrain has 3) | HIGH |
| MC007 | Dual payslip — show amounts in both local currency and base/home currency | MEDIUM |
| MC008 | Multi-currency GL entries — accounting integration must handle currency conversion | HIGH |
| MC009 | Currency symbol and formatting — locale-specific (e.g., 1,00,000.00 for India, 100,000.00 for US) | MEDIUM |
| MC010 | Historical exchange rates preserved — no retroactive change to processed payroll | HIGH |

## 44. INTERNATIONAL HR — COUNTRY-SPECIFIC TAX & COMPLIANCE

| # | Rule | Priority |
|---|------|----------|
| CT001 | US: Federal income tax withholding per W-4 elections | CRITICAL |
| CT002 | US: State income tax — varies by state, some states have zero income tax | HIGH |
| CT003 | US: Social Security (6.2%) and Medicare (1.45%) — employer and employee portions | CRITICAL |
| CT004 | US: Additional Medicare tax 0.9% for income above $200K | HIGH |
| CT005 | UK: PAYE tax — real-time information (RTI) submission to HMRC | CRITICAL |
| CT006 | UK: National Insurance Contributions (NIC) — employer and employee | CRITICAL |
| CT007 | UK: Student loan deductions — Plan 1, Plan 2, Plan 4, Postgraduate | HIGH |
| CT008 | Singapore: CPF contributions — varying rates by age band and residency status | HIGH |
| CT009 | UAE: No income tax — but end-of-service gratuity (EOSB) must be calculated | HIGH |
| CT010 | UAE: EOSB formula — 21 days basic per year for first 5 years, 30 days per year thereafter | HIGH |
| CT011 | Canada: CPP, EI contributions — annual maximum tracked | HIGH |
| CT012 | Germany: Social insurance contributions — health, pension, unemployment, care | HIGH |
| CT013 | Australia: Superannuation guarantee — 11% (FY 2023-24) employer contribution | HIGH |
| CT014 | System must support different financial years per country (Apr-Mar India, Jan-Dec most others, Jul-Jun Australia) | HIGH |
| CT015 | Country-specific year-end forms: W-2 (US), P60 (UK), Form 16 (India), Payment Summary (Australia) | HIGH |

## 45. INTERNATIONAL HR — VISA & WORK PERMIT TRACKING

| # | Rule | Priority |
|---|------|----------|
| VW001 | Visa type, number, issue date, expiry date must be tracked for international employees | CRITICAL |
| VW002 | Work permit number and validity must be tracked separately from visa | HIGH |
| VW003 | System must send alerts at 90, 60, and 30 days before visa/work permit expiry | CRITICAL |
| VW004 | Expired work permit — system must flag employee as non-compliant, alert HR | CRITICAL |
| VW005 | Visa-dependent employees — track dependent visas and their expiry | MEDIUM |
| VW006 | Country of passport — tracked and used for compliance checks | HIGH |
| VW007 | Multiple passports — system must support employees with dual citizenship | MEDIUM |
| VW008 | Travel history — log international travel for tax residency determination | HIGH |
| VW009 | Tax residency — 183-day rule tracking for employees with international assignments | HIGH |
| VW010 | Immigration attorney/agent details — linkable to employee visa cases | LOW |
| VW011 | Work permit type-specific restrictions (e.g., H-1B specialty occupation, L-1 intra-company transfer) | MEDIUM |
| VW012 | Document upload — visa copy, I-94, work permit copy must be stored securely | HIGH |

## 46. INTERNATIONAL HR — EXPAT MANAGEMENT & TIME ZONES

| # | Rule | Priority |
|---|------|----------|
| EX001 | International transfer — home and host entity must be tracked simultaneously | HIGH |
| EX002 | Hypothetical tax — tax equalization calculation for expats | HIGH |
| EX003 | Cost of living allowance (COLA) — location-differential calculation | MEDIUM |
| EX004 | Hardship allowance — for difficult postings, configurable per location | MEDIUM |
| EX005 | Housing allowance — per host country cost, configurable | MEDIUM |
| EX006 | Home leave — annual trips to home country tracked as separate leave type | MEDIUM |
| EX007 | Assignment letter — auto-generate with terms, duration, compensation | MEDIUM |
| EX008 | Shadow payroll — employee appears on both home and host payroll for tax compliance | HIGH |
| EX009 | End of assignment — repatriation checklist and benefits settlement | MEDIUM |
| EX010 | Permanent establishment risk — if employee stays too long, triggers corporate tax liability | HIGH |
| TZ001 | All timestamps stored in UTC — displayed in user's local timezone | CRITICAL |
| TZ002 | Attendance punch — captured in local timezone of the office/employee | HIGH |
| TZ003 | Leave start/end — based on employee's timezone, not server timezone | HIGH |
| TZ004 | Payroll processing — cut-off dates in each entity's local timezone | HIGH |
| TZ005 | Approval deadlines — calculated in approver's timezone | MEDIUM |
| TZ006 | Scheduled reports — sent at configured time in recipient's timezone | MEDIUM |
| TZ007 | DST (Daylight Saving Time) transitions — attendance records handle clock changes correctly | HIGH |
| TZ008 | Global team meeting scheduler — show availability across timezones | LOW |

## 47. INTERNATIONAL HR — DATA PRIVACY (GDPR, CCPA, POPIA)

| # | Rule | Priority |
|---|------|----------|
| DP001 | GDPR: Employee consent must be obtained and recorded before processing personal data (EU employees) | CRITICAL |
| DP002 | GDPR: Right to access — employee can request all data held about them | CRITICAL |
| DP003 | GDPR: Right to erasure (right to be forgotten) — anonymize data on request, except legal retention requirements | CRITICAL |
| DP004 | GDPR: Data portability — export employee data in machine-readable format (JSON/CSV) | HIGH |
| DP005 | GDPR: Data breach notification — system supports incident reporting within 72 hours | CRITICAL |
| DP006 | GDPR: Data Processing Agreement (DPA) — system tracks DPA with all sub-processors | HIGH |
| DP007 | GDPR: Data residency — EU employee data must be stored in EU data centers (configurable) | HIGH |
| DP008 | GDPR: Lawful basis for processing — system records the legal basis per data category | MEDIUM |
| DP009 | GDPR: Data retention periods — auto-delete or archive after configurable retention period | HIGH |
| DP010 | CCPA: California employees can request disclosure of personal information collected | HIGH |
| DP011 | CCPA: Right to delete — similar to GDPR erasure for California residents | HIGH |
| DP012 | CCPA: Do Not Sell — while primarily consumer-focused, employee data must not be sold | MEDIUM |
| DP013 | POPIA: South African employees — consent and lawful processing requirements similar to GDPR | HIGH |
| DP014 | POPIA: Information officer must be designated — system tracks this role | MEDIUM |
| DP015 | Cross-border data transfer — only to countries with adequate data protection (or with appropriate safeguards) | HIGH |
| DP016 | Privacy impact assessment — system supports DPIA for new data processing activities | MEDIUM |
| DP017 | Cookie consent — if HRMS uses cookies, consent banner required for EU users | MEDIUM |

## 48. EMPLOYEE SELF-SERVICE — PROFILE & PERSONAL DATA

| # | Rule | Priority |
|---|------|----------|
| ESS001 | Profile photo — max file size 2 MB, formats: JPG, PNG only | MEDIUM |
| ESS002 | Profile photo — minimum resolution 200x200 pixels, maximum 4000x4000 | LOW |
| ESS003 | Profile photo — inappropriate content detection (nudity, offensive) if AI moderation enabled | LOW |
| ESS004 | Profile photo — cropping tool must maintain square aspect ratio | LOW |
| ESS005 | Emergency contact — at least one emergency contact required, enforced before first payroll | HIGH |
| ESS006 | Emergency contact — relationship type required (spouse, parent, sibling, friend, other) | MEDIUM |
| ESS007 | Emergency contact — phone number validated (format check per country) | MEDIUM |
| ESS008 | Bank account change — requires approval from HR/Finance, not instant | CRITICAL |
| ESS009 | Bank account change — old account preserved in history, not overwritten | HIGH |
| ESS010 | Bank account change — verification via cancelled cheque or bank statement upload | HIGH |
| ESS011 | Bank account change — at least one active bank account required if payroll active | HIGH |
| ESS012 | Address change — triggers review of tax jurisdiction (PT state, local tax, ESI branch) | HIGH |
| ESS013 | Address change — proof of address document upload (utility bill, Aadhaar) | MEDIUM |
| ESS014 | Address change — current and permanent address tracked separately | MEDIUM |
| ESS015 | Name change — requires legal proof upload (marriage certificate, gazette notification) | HIGH |
| ESS016 | Name change — must cascade to payslips (future), PF records (Form 11/UAN update), ESI, bank | CRITICAL |
| ESS017 | Name change — old name retained in history for audit trail | HIGH |
| ESS018 | Gender update — requires HR approval with supporting documentation | HIGH |
| ESS019 | Gender update — cascades to salutation (Mr/Ms/Mx), pronoun settings if applicable | MEDIUM |
| ESS020 | Date of birth correction — requires admin approval with birth certificate, allowed only once | HIGH |
| ESS021 | Marital status change — may affect tax deductions, HRA calculation, insurance coverage | HIGH |
| ESS022 | Dependent add — triggers insurance enrollment workflow within 30-day window | HIGH |
| ESS023 | Dependent remove — triggers insurance de-enrollment, requires reason (death, divorce, age-out) | HIGH |
| ESS024 | Dependent age tracking — child dependent auto-ages out of insurance at configurable age (e.g., 25) | MEDIUM |
| ESS025 | Nominee update for PF — Form 2 (revised) generation on any change | HIGH |
| ESS026 | Nominee update for Gratuity — Form F generation | HIGH |
| ESS027 | Nominee percentage allocation — must total exactly 100% | HIGH |
| ESS028 | IT declaration — lock after proof submission deadline (e.g., January 31) | HIGH |
| ESS029 | IT declaration — proofs required for all declared investments before deadline | HIGH |
| ESS030 | IT declaration — provisional vs actual — payroll uses provisional until proofs verified | HIGH |
| ESS031 | Reimbursement claim — receipt/invoice upload mandatory for each line item | HIGH |
| ESS032 | Reimbursement claim — amount per category capped (e.g., medical Rs 15,000/year) | HIGH |
| ESS033 | Reimbursement claim — duplicate receipt detection (same vendor, date, amount) | MEDIUM |
| ESS034 | Reimbursement claim — cannot claim for dates before joining or after last working day | HIGH |
| ESS035 | Reimbursement claim — pending claims auto-rejected if not approved within X days | MEDIUM |
| ESS036 | Password change — cannot reuse last 5 passwords | HIGH |
| ESS037 | Password change — must meet complexity requirements (min 8 chars, upper, lower, number, special) | HIGH |
| ESS038 | Employee can download own payslips, Form 16, tax computation sheet | HIGH |
| ESS039 | Employee can view but not edit: employee ID, joining date, department, designation (admin-only fields) | HIGH |
| ESS040 | Profile completeness indicator — percentage showing missing mandatory fields | MEDIUM |

## 49. MANAGER-SPECIFIC RULES

| # | Rule | Priority |
|---|------|----------|
| MGR001 | Manager can view only direct reports' data, not peer or other team data | CRITICAL |
| MGR002 | Skip-level manager (manager's manager) can view data of all reports in hierarchy below | HIGH |
| MGR003 | Manager cannot approve their own leave request — must go to their manager | CRITICAL |
| MGR004 | Manager cannot approve their own expense/reimbursement claim | CRITICAL |
| MGR005 | Manager cannot give themselves a salary increment or bonus | CRITICAL |
| MGR006 | Manager delegation — can assign a delegate approver during planned absence | HIGH |
| MGR007 | Manager delegation — delegation period must have start and end date | HIGH |
| MGR008 | Manager delegation — delegated approver has same approval power as original manager for that period only | HIGH |
| MGR009 | Manager delegation — original manager can revoke delegation at any time | MEDIUM |
| MGR010 | Team budget — manager cannot approve training/reward spend exceeding allocated team budget | HIGH |
| MGR011 | Team budget — real-time tracking of consumed vs remaining budget | MEDIUM |
| MGR012 | Span of control — alert if manager has more than configurable max direct reports (e.g., 15) | MEDIUM |
| MGR013 | Manager change — all pending approvals (leave, expense, etc.) transfer to new manager | CRITICAL |
| MGR014 | Manager change — in-progress performance reviews transfer to new manager | HIGH |
| MGR015 | Manager change — notification sent to employee about new reporting line | HIGH |
| MGR016 | Manager terminated/resigned — all pending approvals auto-escalate to skip-level manager | CRITICAL |
| MGR017 | Manager as IC (individual contributor role) — cannot have dual role of approver and requester for same request | HIGH |
| MGR018 | Manager can view team attendance summary but not modify attendance records (only HR/admin) | HIGH |
| MGR019 | Manager can initiate but not complete salary revision — requires HR approval | HIGH |
| MGR020 | Manager can view team leave calendar to plan resource allocation | MEDIUM |
| MGR021 | Manager exit — succession planning must be completed before full & final | HIGH |
| MGR022 | Manager bulk leave approval — audit trail must show individual approval action per request | HIGH |
| MGR023 | Manager cannot access confidential HR cases (POSH, disciplinary) of reports unless authorized | CRITICAL |
| MGR024 | Manager cannot see other managers' team compensation data (horizontal isolation) | CRITICAL |
| MGR025 | Manager can recommend promotion but cannot unilaterally promote | HIGH |
| MGR026 | Manager can add comments/notes to direct report profile — visible to HR | MEDIUM |
| MGR027 | Interim manager assignment — temporary reporting line with defined duration | MEDIUM |
| MGR028 | Dotted-line reporting — secondary manager can view but not approve (or with limited approval) | MEDIUM |
| MGR029 | Manager dashboard — shows pending actions count (approvals, reviews, etc.) | MEDIUM |
| MGR030 | Manager cannot backdate approval — approval timestamp is system-generated | HIGH |

## 50. MULTI-LOCATION & BRANCH RULES

| # | Rule | Priority |
|---|------|----------|
| ML001 | Each location has its own working hours configuration (start time, end time, break duration) | HIGH |
| ML002 | Each location can have different shift timings and rotation patterns | HIGH |
| ML003 | Location-wise attendance policy — grace period, late marking rules per location | HIGH |
| ML004 | Employee transfer between locations — all records updated: reporting manager, tax jurisdiction, leave policy, attendance policy | CRITICAL |
| ML005 | Transfer effective date — policies apply from effective date, not retroactively | HIGH |
| ML006 | Location-specific leave policy — state holidays differ (e.g., Pongal in Tamil Nadu, Bihu in Assam) | HIGH |
| ML007 | Geo-fencing — check-in only allowed within configured radius of office location | HIGH |
| ML008 | Geo-fencing — multiple geo-fence zones per location (e.g., campus with multiple buildings) | MEDIUM |
| ML009 | Remote employees — geo-fencing disabled but work-hours tracking still applies | HIGH |
| ML010 | Remote work policy — different rules for fully remote vs hybrid vs on-site | MEDIUM |
| ML011 | Location capacity — max headcount per location tracked for compliance and facilities | MEDIUM |
| ML012 | Location closure — all employees must be transferred or terminated before deactivating location | HIGH |
| ML013 | Location-wise payroll — different pay dates per location/entity allowed | MEDIUM |
| ML014 | Location-specific statutory compliance — PF/ESI establishment codes per location | HIGH |
| ML015 | Location-wise admin — branch admin can manage only their location's employees | HIGH |
| ML016 | Location hierarchy — region > state > city > branch supported for reporting | MEDIUM |
| ML017 | Multi-location employee — assigned to one primary location but can have secondary locations | MEDIUM |
| ML018 | Location-wise cost center — auto-assigned based on employee's location | HIGH |
| ML019 | Office asset tracking — assets linked to location, not just employee | MEDIUM |
| ML020 | Location-wise emergency contacts (building manager, security, fire warden) | LOW |

## 51. CONTRACTOR & TEMPORARY EMPLOYEE RULES

| # | Rule | Priority |
|---|------|----------|
| CON001 | Contract employee must have a contract end date — system enforces this | CRITICAL |
| CON002 | Alert at 30 and 15 days before contract end — to HR and employee | HIGH |
| CON003 | Auto-deactivation on contract end date — user access revoked | CRITICAL |
| CON004 | Auto-deactivation can be overridden by extending contract before end date | HIGH |
| CON005 | No leave accrual for contractors unless explicitly configured in their policy | HIGH |
| CON006 | No PF/ESI for independent contractors (1099-type) — only for contract employees on payroll | HIGH |
| CON007 | Contractor cannot be promoted — must be converted to permanent employee first | HIGH |
| CON008 | Contractor-to-permanent conversion workflow — requires HR approval, new employee record or record type change | HIGH |
| CON009 | Contract renewal — new contract dates, rate revision, approval workflow | HIGH |
| CON010 | Maximum contract duration — configurable limit (e.g., 2 years before mandatory conversion review) | MEDIUM |
| CON011 | Contractor billing rate — tracked per contractor (hourly/daily/monthly) | HIGH |
| CON012 | Contractor billing rate vs salary — billing rate is what client pays, salary is what contractor receives | MEDIUM |
| CON013 | Contractor timesheet — mandatory weekly/bi-weekly submission | HIGH |
| CON014 | Contractor timesheet — requires project manager or client approval | HIGH |
| CON015 | Contractor PO (Purchase Order) tracking — hours/amount consumed vs total PO value | HIGH |
| CON016 | PO exhaustion alert — when 80% and 100% of PO value is consumed | HIGH |
| CON017 | Contractor cannot access employee-only modules (performance review, bonus, ESOP) | HIGH |
| CON018 | Contractor exit — simplified process, no F&F settlement, just access revocation and asset return | MEDIUM |
| CON019 | Staffing agency tracking — which agency placed which contractor, commission terms | MEDIUM |
| CON020 | Contractor background verification — same as employees or configurable per policy | MEDIUM |
| CON021 | Temp employee — distinct from contractor, has different leave/benefit entitlements | MEDIUM |
| CON022 | Temp-to-perm — service continuity from temp start date (for benefits like gratuity, if applicable) | HIGH |
| CON023 | Contractor insurance — tracked separately, may be agency's responsibility | MEDIUM |
| CON024 | Contractor NDAs and agreements — stored in document management, signed digitally | MEDIUM |
| CON025 | Contractor compliance — misclassification risk alert if contractor works like an employee (fixed hours, single client, long tenure) | HIGH |

## 52. BULK OPERATIONS RULES

| # | Rule | Priority |
|---|------|----------|
| BLK001 | Bulk salary revision — atomic transaction: all succeed or all fail, no partial updates | CRITICAL |
| BLK002 | Bulk salary revision — preview/dry-run mode showing all changes before commit | HIGH |
| BLK003 | Bulk leave approval — partial success allowed, but each failure reason clearly logged | HIGH |
| BLK004 | Bulk leave approval — cannot bulk-approve if any leave violates policy (option to skip invalid) | HIGH |
| BLK005 | Bulk department transfer — all employees moved together, effective date same | HIGH |
| BLK006 | Bulk deactivation — only for employees with status Resigned/Terminated, not active employees | CRITICAL |
| BLK007 | Bulk deactivation — confirmation dialog listing all employees and consequences | HIGH |
| BLK008 | Bulk email — rate limiting enforced (e.g., max 500 emails/hour) | HIGH |
| BLK009 | Bulk email — opt-out preference respected, unsubscribed employees excluded | HIGH |
| BLK010 | CSV import — max 1000 rows per upload (configurable) | HIGH |
| BLK011 | CSV import — validation report generated showing row-by-row errors before commit | CRITICAL |
| BLK012 | CSV import — duplicate detection (same employee ID or email in upload) | HIGH |
| BLK013 | CSV import — encoding support: UTF-8 mandatory, BOM handled gracefully | MEDIUM |
| BLK014 | CSV import — column mapping UI for flexible header names | MEDIUM |
| BLK015 | Bulk payslip generation — parallel/async processing with progress indicator | HIGH |
| BLK016 | Bulk payslip generation — failure for one employee must not block others | HIGH |
| BLK017 | Bulk operations — audit log captures who initiated, timestamp, number of records affected | CRITICAL |
| BLK018 | Bulk operations — undo/rollback within a time window (e.g., 24 hours) for critical operations | HIGH |
| BLK019 | Bulk upload — file size limit (e.g., 10 MB per upload) | MEDIUM |
| BLK020 | Bulk operations — background processing with email notification on completion | HIGH |
| BLK021 | Bulk letter generation (offer, increment, experience) — template merge with employee data | MEDIUM |
| BLK022 | Concurrent bulk operations — prevent two admins from running conflicting bulk ops simultaneously | HIGH |

## 53. MOBILE APP RULES

| # | Rule | Priority |
|---|------|----------|
| MOB001 | Mobile check-in — GPS coordinates captured and stored with attendance punch | HIGH |
| MOB002 | Mobile check-in — GPS accuracy threshold: reject if accuracy > 100 meters | MEDIUM |
| MOB003 | Mobile check-in — mock location/GPS spoofing detection | HIGH |
| MOB004 | Mobile leave apply — same validation rules as web (balance check, overlap, policy) | CRITICAL |
| MOB005 | Mobile leave apply — attachment upload supported (medical certificate) | HIGH |
| MOB006 | Offline mode — attendance punch stored locally and synced when connectivity restored | HIGH |
| MOB007 | Offline mode — conflict resolution when offline punch conflicts with server data | HIGH |
| MOB008 | Offline mode — visual indicator that data is not yet synced | MEDIUM |
| MOB009 | Push notifications — opt-in/opt-out configurable per notification type | HIGH |
| MOB010 | Push notifications — leave approval/rejection, payslip, announcement, birthday | MEDIUM |
| MOB011 | Biometric attendance via mobile — fingerprint or face recognition matches device biometric | HIGH |
| MOB012 | Photo attendance — selfie captured with live timestamp and GPS overlay | HIGH |
| MOB013 | Photo attendance — liveness detection to prevent photo-of-photo spoofing | HIGH |
| MOB014 | Mobile app — session timeout same as web (configurable, e.g., 30 minutes) | HIGH |
| MOB015 | Mobile app — biometric unlock (fingerprint/face) for app re-entry within session | MEDIUM |
| MOB016 | Mobile app — minimum OS version enforced (e.g., Android 8+, iOS 14+) | MEDIUM |
| MOB017 | Mobile app — force update mechanism for critical security patches | HIGH |
| MOB018 | Mobile app — data cached locally encrypted, wiped on logout | HIGH |
| MOB019 | Mobile app — deep links to specific approvals from push notifications | MEDIUM |
| MOB020 | Mobile app — responsive to screen size, supports both phone and tablet layouts | MEDIUM |
| MOB021 | Mobile app — payslip view and download as PDF | HIGH |
| MOB022 | Mobile app — team calendar view for managers | MEDIUM |

## 54. APPROVAL WORKFLOW RULES (EXTENDED)

| # | Rule | Priority |
|---|------|----------|
| AW001 | Multi-level approval chain — configurable up to N levels (L1, L2, L3... LN) | CRITICAL |
| AW002 | Each approval level can have different approver logic: reporting manager, department head, HR, custom role | HIGH |
| AW003 | Auto-approve after configurable X days if no action taken (per workflow type) | HIGH |
| AW004 | Auto-escalate to next level/skip-level manager if approver doesn't act within X hours | HIGH |
| AW005 | Approval delegation — out-of-office auto-delegation to designated delegate | HIGH |
| AW006 | Approval delegation — delegated approvals clearly marked as "approved by delegate on behalf of" | HIGH |
| AW007 | Approval chain breaks if approver is terminated — auto-reroute to skip-level | CRITICAL |
| AW008 | Approval chain breaks if approver is on long leave — auto-reroute or queue for delegate | HIGH |
| AW009 | Parallel approval — multiple approvers must all approve (AND logic) | HIGH |
| AW010 | Parallel approval — any one approver can approve (OR logic) — configurable | HIGH |
| AW011 | Conditional approval — amount-based routing (e.g., expense > Rs 50,000 needs VP) | HIGH |
| AW012 | Conditional approval — type-based routing (e.g., international travel needs HR head) | HIGH |
| AW013 | Approval audit trail — who approved/rejected, timestamp, IP address, device info | CRITICAL |
| AW014 | Approval audit trail — comments mandatory on rejection | HIGH |
| AW015 | Recall/withdraw — requester can withdraw pending request before any approval | HIGH |
| AW016 | Recall — cannot withdraw after first approval in multi-level chain (or configurable) | MEDIUM |
| AW017 | Approval reminder — daily digest email for pending approvals | HIGH |
| AW018 | Approval reminder — escalation notification to HR if pending beyond SLA | MEDIUM |
| AW019 | Approval status — requester can view real-time status (pending at L1, approved at L1 pending at L2) | HIGH |
| AW020 | Approval re-routing — HR admin can manually re-route stuck approvals | HIGH |
| AW021 | Approval SLA tracking — average approval time per manager, per request type | MEDIUM |
| AW022 | Rejection with rework — rejected request can be re-submitted with modifications | HIGH |
| AW023 | Rejection with rework — re-submitted request goes through same approval chain from L1 | HIGH |
| AW024 | Auto-reject after configurable X days of inaction (alternative to auto-approve) | MEDIUM |
| AW025 | Approval matrix — different approval chains per company, department, or request type | HIGH |
| AW026 | Self-service for CEO/top-level — approval goes to HR head or board-designated person | HIGH |
| AW027 | Batch approval — approver can select multiple requests and approve/reject in one action | HIGH |
| AW028 | Batch approval — individual comments must still be supported even in batch mode | MEDIUM |
| AW029 | Workflow versioning — changes to workflow apply to new requests, in-flight requests follow old workflow | HIGH |
| AW030 | No circular approval — system prevents A approves B and B approves A for same request type | CRITICAL |

## 55. REPORTING & ANALYTICS RULES

| # | Rule | Priority |
|---|------|----------|
| RPT001 | Dashboard summary numbers must match detailed report totals exactly | CRITICAL |
| RPT002 | Dashboard — clicking a KPI number drills down to the detailed report | HIGH |
| RPT003 | Report filters — consistent filter options across all modules (date range, department, location, status) | HIGH |
| RPT004 | Report filters — applied filters displayed clearly on report and in exported file | HIGH |
| RPT005 | Export format — Excel (.xlsx), PDF, and CSV supported for all reports | HIGH |
| RPT006 | Export — large report export (10K+ rows) processed asynchronously with download link emailed | HIGH |
| RPT007 | Report scheduling — auto-email on configurable frequency (daily, weekly, monthly) | MEDIUM |
| RPT008 | Report scheduling — recipients configurable, supports distribution lists | MEDIUM |
| RPT009 | Year-on-year comparison — attrition, headcount, payroll cost trends | MEDIUM |
| RPT010 | Month-on-month comparison — attendance, leave, overtime trends | MEDIUM |
| RPT011 | Department-wise breakdown — all reports support department as a dimension | HIGH |
| RPT012 | Location-wise breakdown — all reports support location as a dimension | HIGH |
| RPT013 | Custom report builder — select fields, filters, grouping, save as template | MEDIUM |
| RPT014 | Custom report — saved templates shareable with other admins | LOW |
| RPT015 | Report access — RBAC applied, manager sees only their team's reports | CRITICAL |
| RPT016 | Report access — HR sees all employees, finance sees payroll reports, admin sees all | HIGH |
| RPT017 | Real-time dashboard vs batch reports — dashboard is real-time, scheduled reports use batch data | HIGH |
| RPT018 | Data freshness indicator — "Last updated: X minutes ago" on dashboards | MEDIUM |
| RPT019 | Headcount report — shows active, on notice, on probation, on leave at a point in time | HIGH |
| RPT020 | Attrition report — voluntary vs involuntary, by department, by tenure band | HIGH |
| RPT021 | Payroll cost report — gross, net, employer statutory cost, by department | HIGH |
| RPT022 | Leave balance report — all employees, all leave types, as of a date | HIGH |
| RPT023 | Attendance compliance report — late comers, absentees, regularization pending | HIGH |
| RPT024 | Overtime report — hours by employee, department, cost implication | HIGH |
| RPT025 | Statutory compliance report — PF/ESI/PT filing status per month | HIGH |
| RPT026 | Training report — completion rates, cost per employee, effectiveness scores | MEDIUM |
| RPT027 | Diversity report — gender, age, disability breakdown (anonymized if needed) | MEDIUM |
| RPT028 | Report data isolation — multi-tenant: one organization's data never leaks to another | CRITICAL |
| RPT029 | Report performance — report generation must complete within 30 seconds for standard reports | HIGH |
| RPT030 | Report pagination — large reports paginated in UI, full data in export | MEDIUM |

## 56. INTEGRATION RULES

| # | Rule | Priority |
|---|------|----------|
| INT001 | Slack integration — leave approval notifications pushed to Slack channel or DM | MEDIUM |
| INT002 | Slack integration — employee can apply leave via Slack slash command | LOW |
| INT003 | Calendar sync — approved leaves synced to Google Calendar/Outlook as all-day events | HIGH |
| INT004 | Calendar sync — holidays synced automatically to employee's calendar | MEDIUM |
| INT005 | Accounting integration — payroll GL entries auto-posted to accounting software (Tally, QuickBooks, Xero) | HIGH |
| INT006 | Accounting integration — journal entry format configurable (cost center, GL account mapping) | HIGH |
| INT007 | Background check API — initiate BGV on onboarding, status tracked in employee profile | HIGH |
| INT008 | Background check — statuses: Initiated, In Progress, Clear, Discrepancy, Failed | HIGH |
| INT009 | Job board integration — publish job postings to LinkedIn, Indeed, Naukri simultaneously | MEDIUM |
| INT010 | Job board integration — applications from all boards consolidated in ATS | MEDIUM |
| INT011 | SSO — SAML 2.0 integration for enterprise identity providers (Okta, Azure AD, OneLogin) | CRITICAL |
| INT012 | SSO — OAuth 2.0 / OpenID Connect support for Google Workspace, Microsoft 365 | HIGH |
| INT013 | SSO — LDAP integration for on-premises Active Directory | MEDIUM |
| INT014 | SSO — SCIM provisioning: auto-create/deactivate users from identity provider | HIGH |
| INT015 | API rate limiting — per API key/client, configurable (e.g., 1000 requests/minute) | HIGH |
| INT016 | API rate limiting — 429 response with Retry-After header | HIGH |
| INT017 | Webhook delivery — retry on failure with exponential backoff (1s, 5s, 30s, 5m, 1h) | HIGH |
| INT018 | Webhook delivery — max retries configurable, dead letter queue after max retries | MEDIUM |
| INT019 | Webhook — signature verification (HMAC) for webhook consumers to verify authenticity | HIGH |
| INT020 | Data sync conflict — last-write-wins for non-critical fields, manual merge for critical fields (salary, designation) | HIGH |
| INT021 | API versioning — v1 endpoints continue working when v2 is released, deprecation with advance notice | HIGH |
| INT022 | API — all responses include request ID for tracing and debugging | MEDIUM |
| INT023 | API — pagination: offset-based or cursor-based, max page size enforced | HIGH |
| INT024 | API — field-level filtering: only requested fields returned (sparse fieldsets) | LOW |
| INT025 | Biometric device integration — TCP/IP or API-based sync of punch data | HIGH |
| INT026 | Biometric device — duplicate punch within 1 minute ignored (debounce) | HIGH |
| INT027 | Email integration — transactional emails via configurable SMTP or API (SendGrid, SES) | HIGH |
| INT028 | Email — bounce handling: hard bounces mark email as invalid, soft bounces retry | MEDIUM |
| INT029 | Banking integration — salary payment file generation in bank-specific format (NEFT, RTGS, IMPS) | HIGH |
| INT030 | Banking integration — payment status reconciliation: uploaded, processed, failed, reversed | HIGH |

## 57. DATA INTEGRITY RULES

| # | Rule | Priority |
|---|------|----------|
| DI001 | No orphan records — every employee record has a valid organization, department, designation | CRITICAL |
| DI002 | Foreign key integrity — deleting a department with active employees must be blocked | CRITICAL |
| DI003 | Foreign key integrity — deleting a leave type with existing leave records must be blocked | HIGH |
| DI004 | Timestamps stored in UTC — displayed converted to user's timezone | CRITICAL |
| DI005 | All date fields use ISO 8601 format in API (YYYY-MM-DD), localized format in UI | HIGH |
| DI006 | Currency precision — 2 decimal places for INR, USD, EUR; 3 for BHD, OMR; 0 for JPY | HIGH |
| DI007 | Rounding rules — consistent across payroll (round to nearest, round up, round down configurable) | HIGH |
| DI008 | Rounding — payroll totals computed from individual items, not re-rounded (avoid accumulated rounding error) | HIGH |
| DI009 | Enum validation — only valid status values accepted (Active, Inactive, Probation, etc.) | HIGH |
| DI010 | Enum validation — API rejects invalid enum values with descriptive error message | HIGH |
| DI011 | Unique constraints — employee email globally unique, employee ID unique per organization | CRITICAL |
| DI012 | Unique constraints — enforced at database level, not just application level | CRITICAL |
| DI013 | Soft delete — deleted records set to is_deleted=true, not physically removed | HIGH |
| DI014 | Soft delete — all queries exclude soft-deleted records by default, unless explicitly included | HIGH |
| DI015 | Soft delete — related child records also soft-deleted in cascade | HIGH |
| DI016 | Search index — updated synchronously or within 5 seconds of data change | HIGH |
| DI017 | Cache invalidation — cached data invalidated immediately on underlying data change | CRITICAL |
| DI018 | Cache — stale cache must never serve data for a different user/organization | CRITICAL |
| DI019 | Transaction rollback — if any step in a multi-step operation fails, all steps rolled back | CRITICAL |
| DI020 | Idempotency — API operations that can be retried safely (payment, leave approval) must be idempotent | HIGH |
| DI021 | Sequence numbers — employee ID, payslip number, invoice number never reused after deletion | HIGH |
| DI022 | Data type validation — numeric fields reject non-numeric input, date fields reject invalid dates | HIGH |
| DI023 | Max length validation — all string fields have enforced max lengths matching database columns | MEDIUM |
| DI024 | Empty string vs null — consistent handling (empty string not treated as null or vice versa) | MEDIUM |
| DI025 | Unicode support — employee names, addresses can contain non-ASCII characters (accents, CJK, Devanagari) | HIGH |
| DI026 | Leading/trailing whitespace — trimmed on save for names, emails, and identifiers | MEDIUM |
| DI027 | Case sensitivity — email lookups case-insensitive, employee name stored in original case | HIGH |
| DI028 | Concurrent edit — optimistic locking: if two users edit same record, second save shows conflict error | HIGH |
| DI029 | Data migration — schema changes must be backward compatible or include data migration scripts | HIGH |
| DI030 | Referential integrity — employee cannot reference a non-existent manager, department, or designation | CRITICAL |
| DI031 | Circular reference prevention — employee cannot be their own manager; no circular reporting chains | CRITICAL |
| DI032 | Date logic — end date must be after start date in all date range fields | HIGH |
| DI033 | Future date limits — no records with dates more than 1 year in the future (except contract end dates) | MEDIUM |
| DI034 | Historical data immutability — processed payroll records cannot be modified, only adjusted via new entries | CRITICAL |
| DI035 | Audit trail integrity — audit log entries cannot be modified or deleted even by super admin | CRITICAL |

## 58. ACCESSIBILITY & UX RULES

| # | Rule | Priority |
|---|------|----------|
| AX001 | WCAG 2.1 AA compliance — all public and employee-facing pages | HIGH |
| AX002 | Screen reader compatibility — all interactive elements have ARIA labels | HIGH |
| AX003 | Keyboard navigation — all functionality accessible via keyboard alone, no mouse dependency | HIGH |
| AX004 | Focus indicators — visible focus ring on all interactive elements when navigating by keyboard | HIGH |
| AX005 | Color contrast — minimum 4.5:1 ratio for normal text, 3:1 for large text (18px+) | HIGH |
| AX006 | Color is not sole indicator — errors, status, and alerts use icon/text in addition to color | HIGH |
| AX007 | Form error messages — displayed inline near the field, not just as a toast/alert | HIGH |
| AX008 | Form error messages — specific and actionable (e.g., "Date must be in DD/MM/YYYY format" not just "Invalid input") | HIGH |
| AX009 | Loading states — spinner or skeleton shown during async operations | HIGH |
| AX010 | Loading states — operations taking > 3 seconds show progress indicator | MEDIUM |
| AX011 | Empty states — meaningful message with suggested action, not blank page | MEDIUM |
| AX012 | Responsive design — functional on 320px width (mobile) to 4K displays | HIGH |
| AX013 | Touch targets — minimum 44x44 pixels for mobile interactive elements | MEDIUM |
| AX014 | RTL language support — layout mirrors for Arabic, Hebrew, Urdu | MEDIUM |
| AX015 | Print-friendly pages — payslips, offer letters, experience letters, reports render cleanly when printed | HIGH |
| AX016 | Print — no navigation, sidebar, or interactive elements in print output | MEDIUM |
| AX017 | Timeout warning — session about to expire dialog shown 5 minutes before timeout | HIGH |
| AX018 | Timeout warning — option to extend session without losing unsaved work | HIGH |
| AX019 | Auto-save — long forms (e.g., IT declaration, performance review) auto-save draft periodically | MEDIUM |
| AX020 | Confirmation dialogs — destructive actions (delete, reject, cancel) require explicit confirmation | HIGH |
| AX021 | Undo support — accidental deletions of non-critical items can be undone within X seconds | MEDIUM |
| AX022 | Multi-language UI — language switcher available, labels/messages loaded from locale files | MEDIUM |
| AX023 | Date/time formatting — respects user's locale (DD/MM/YYYY for India, MM/DD/YYYY for US) | HIGH |
| AX024 | Number formatting — respects locale (Indian: 1,00,000; Western: 100,000) | HIGH |
| AX025 | Breadcrumb navigation — user always knows where they are in the app hierarchy | MEDIUM |

## 59. SECURITY — DEEP RULES

| # | Rule | Priority |
|---|------|----------|
| SEC001 | CSRF protection — anti-CSRF token on all state-changing POST/PUT/DELETE requests | CRITICAL |
| SEC002 | XSS prevention — all user-generated content HTML-encoded on output | CRITICAL |
| SEC003 | XSS prevention — Content Security Policy (CSP) header blocks inline scripts | HIGH |
| SEC004 | SQL injection — parameterized queries / prepared statements used everywhere, no string concatenation | CRITICAL |
| SEC005 | File upload — virus scan on all uploaded files before storage | HIGH |
| SEC006 | File upload — magic byte validation, not just extension check (e.g., .exe renamed to .pdf detected) | HIGH |
| SEC007 | File upload — max file size enforced (server-side, not just client-side) | HIGH |
| SEC008 | File upload — only allowed MIME types accepted (PDF, JPG, PNG, XLSX, DOCX, CSV) | HIGH |
| SEC009 | Session fixation — new session ID issued on login, old session invalidated | CRITICAL |
| SEC010 | Clickjacking — X-Frame-Options: DENY (or SAMEORIGIN for iframes within same app) | HIGH |
| SEC011 | Brute force — account locked after configurable failed attempts (e.g., 5), exponential backoff | CRITICAL |
| SEC012 | Brute force — CAPTCHA after 3 consecutive failed login attempts | HIGH |
| SEC013 | API authentication — bearer token in Authorization header, never in query string | HIGH |
| SEC014 | API authentication — tokens have configurable expiry (access token: 15 min, refresh token: 7 days) | HIGH |
| SEC015 | TLS 1.2+ enforced — TLS 1.0 and 1.1 disabled | CRITICAL |
| SEC016 | HSTS header — Strict-Transport-Security with long max-age and includeSubDomains | HIGH |
| SEC017 | Secrets management — API keys, DB passwords, encryption keys stored in vault (not in code or config files) | CRITICAL |
| SEC018 | No hardcoded credentials — security scan for leaked secrets in codebase | CRITICAL |
| SEC019 | IP whitelisting — optional for admin panel, API access from known corporate IPs | MEDIUM |
| SEC020 | Two-factor authentication (2FA) — TOTP-based, optional or mandatory per organization policy | HIGH |
| SEC021 | 2FA — backup codes provided, one-time use, 10 codes generated | HIGH |
| SEC022 | Login from new device/location — verification email or OTP sent | HIGH |
| SEC023 | Concurrent session limit — max N active sessions per user, oldest terminated on new login | MEDIUM |
| SEC024 | Password storage — bcrypt/argon2 hashed, salted, never stored in plain text | CRITICAL |
| SEC025 | Password — minimum 8 characters, at least 1 uppercase, 1 lowercase, 1 digit, 1 special character | HIGH |
| SEC026 | Password expiry — configurable (e.g., 90 days), forced change on expiry | MEDIUM |
| SEC027 | Password history — cannot reuse last N passwords (configurable, default 5) | HIGH |
| SEC028 | Session cookie — Secure, HttpOnly, SameSite=Strict flags set | CRITICAL |
| SEC029 | Sensitive data in logs — PII (Aadhaar, PAN, salary) must be masked in application logs | CRITICAL |
| SEC030 | Sensitive data in URLs — no PII in query strings (logged by proxies, browsers) | HIGH |
| SEC031 | Data encryption at rest — database and file storage encrypted (AES-256) | CRITICAL |
| SEC032 | Data encryption in transit — all API communication over HTTPS | CRITICAL |
| SEC033 | Field-level encryption — Aadhaar number, PAN, bank account number encrypted in DB | CRITICAL |
| SEC034 | Admin audit — all admin actions logged (user creation, role change, salary modification) | CRITICAL |
| SEC035 | Privilege escalation prevention — user cannot modify their own role or permissions | CRITICAL |
| SEC036 | API authorization — check resource ownership, not just authentication (IDOR prevention) | CRITICAL |
| SEC037 | Rate limiting on login endpoint — prevent credential stuffing attacks | HIGH |
| SEC038 | Rate limiting on OTP endpoint — prevent OTP brute force (max 5 attempts per 10 minutes) | HIGH |
| SEC039 | Account recovery — email-based, OTP-based; security questions optional | HIGH |
| SEC040 | Account recovery — link expires after 15 minutes | HIGH |
| SEC041 | Data export — all bulk data exports logged with user ID, timestamp, filter criteria | HIGH |
| SEC042 | PII access logging — access to sensitive fields (salary, Aadhaar, bank) logged per DPDP Act (India) | HIGH |

## 60. PAYROLL PROCESSING — EDGE CASES

| # | Rule | Priority |
|---|------|----------|
| PP001 | Payroll cannot be processed twice for the same month/employee (idempotency) | CRITICAL |
| PP002 | Payroll lock — once finalized, payroll month is locked for changes | CRITICAL |
| PP003 | Payroll unlock — only super admin can unlock with audit trail | HIGH |
| PP004 | Mid-month joining — salary pro-rated based on actual days (30-day, actual-day, or calendar-day basis configurable) | HIGH |
| PP005 | Mid-month exit — salary computed up to last working day | HIGH |
| PP006 | LOP (Loss of Pay) — deducted per day absent = (gross / total working days) x LOP days | HIGH |
| PP007 | Arrears — auto-calculated when salary revision is back-dated | HIGH |
| PP008 | Arrears — taxed differently (spread over method or lump-sum per employee choice under Section 89) | HIGH |
| PP009 | Salary hold — employee salary can be put on hold (pending investigation, missing documents) | HIGH |
| PP010 | Salary hold — held salary released in next cycle or as one-time payment | HIGH |
| PP011 | Payroll reversal — only before bank transfer, full reversal not individual component | HIGH |
| PP012 | Off-cycle payroll — bonuses, reimbursements, corrections processed outside regular cycle | HIGH |
| PP013 | Final settlement — includes: pending salary, leave encashment, bonus pro-rata, gratuity, notice pay, deductions | CRITICAL |
| PP014 | Final settlement — must be processed within 30 days of last working day (or per policy) | HIGH |
| PP015 | Rehired employee — new employee record but link to old record for service continuity decisions | HIGH |
| PP016 | Rehired employee — leave balance, PF, gratuity continuity depends on break duration and policy | MEDIUM |
| PP017 | Variable pay — computed per performance rating, disbursed per schedule (quarterly, annually) | HIGH |
| PP018 | Commission — calculated per sales data integration, included in payroll | MEDIUM |
| PP019 | Loan EMI deduction — auto-deducted per repayment schedule, stops when fully repaid | HIGH |
| PP020 | Salary advance recovery — deducted per agreed installment, cannot exceed 50% of net pay per month | HIGH |
| PP021 | Pay component order — net pay = gross - (PF + ESI + PT + TDS + other deductions) | CRITICAL |
| PP022 | Negative net pay — system flags if deductions exceed gross (cannot disburse negative amount) | CRITICAL |
| PP023 | Payslip password protection — PDF protected with DOB or PAN first 4 digits (configurable) | MEDIUM |
| PP024 | Payslip — shows both current month and year-to-date figures | HIGH |
| PP025 | Payroll variance report — flag employees with >20% change from previous month (catch errors) | HIGH |

## 61. PERFORMANCE MANAGEMENT — EDGE CASES

| # | Rule | Priority |
|---|------|----------|
| PM001 | Performance review cycle — cannot start new cycle if previous cycle has pending reviews | HIGH |
| PM002 | Self-appraisal — must be submitted before manager review is enabled | HIGH |
| PM003 | Manager review — cannot rate without reviewing self-appraisal | HIGH |
| PM004 | Bell curve / forced distribution — if enabled, department ratings must fit configured distribution | HIGH |
| PM005 | Rating calibration — HR/leadership can adjust ratings in calibration session | HIGH |
| PM006 | Rating calibration — adjustments logged with reason | HIGH |
| PM007 | 360-degree feedback — configurable reviewers: peers, subordinates, cross-functional | MEDIUM |
| PM008 | 360-degree feedback — anonymity of peer reviewers configurable | MEDIUM |
| PM009 | Goal setting — SMART goals: measurable targets with deadlines | MEDIUM |
| PM010 | Goal weightage — total weightage of all goals must equal 100% | HIGH |
| PM011 | Mid-year review — optional check-in without formal rating | MEDIUM |
| PM012 | PIP (Performance Improvement Plan) — triggered by low rating, with defined goals and timeline | HIGH |
| PM013 | PIP — failure to improve can trigger termination workflow | HIGH |
| PM014 | PIP — progress check-ins tracked (weekly/bi-weekly) | MEDIUM |
| PM015 | New joiners — excluded from review cycle if joined within last 3 months (configurable) | HIGH |
| PM016 | Transferred employees — reviewed by current manager, with input from previous manager | HIGH |
| PM017 | Rating scale — configurable (1-5, 1-4, A-E, etc.) per organization | HIGH |
| PM018 | Review form — different templates for different levels (IC, manager, leadership) | MEDIUM |
| PM019 | Review — once submitted, cannot be edited without HR override | HIGH |
| PM020 | Review outcome — links to salary increment, bonus, promotion decisions | HIGH |

## 62. ONBOARDING & OFFBOARDING — EDGE CASES

| # | Rule | Priority |
|---|------|----------|
| OB001 | Onboarding checklist — auto-generated per employee type (full-time, contract, intern) | HIGH |
| OB002 | Onboarding — offer letter must be accepted (digital signature or click-to-accept) before proceeding | HIGH |
| OB003 | Onboarding — background verification must be initiated before first day | HIGH |
| OB004 | Onboarding — mandatory documents not submitted within 30 days flags employee profile as incomplete | HIGH |
| OB005 | Onboarding — IT asset provisioning triggered automatically (laptop, email, badge) | MEDIUM |
| OB006 | Onboarding — buddy/mentor assignment tracked | LOW |
| OB007 | Onboarding — probation period auto-set based on offer terms | HIGH |
| OB008 | Onboarding — welcome email auto-sent with login credentials and Day 1 instructions | MEDIUM |
| OB009 | Offboarding — resignation submission triggers notice period calculation | CRITICAL |
| OB010 | Offboarding — notice period buyout — option to pay instead of serving | HIGH |
| OB011 | Offboarding — exit interview — must be completed before full & final clearance | MEDIUM |
| OB012 | Offboarding — asset return checklist — laptop, badge, keys, parking pass | HIGH |
| OB013 | Offboarding — all access revoked on last working day (email, VPN, app, building) | CRITICAL |
| OB014 | Offboarding — knowledge transfer — documented and assigned to receiving employee | MEDIUM |
| OB015 | Offboarding — full & final settlement — auto-calculated with all components | CRITICAL |
| OB016 | Offboarding — experience/relieving letter — auto-generated from template | HIGH |
| OB017 | Offboarding — PF transfer/withdrawal instructions provided to employee | MEDIUM |
| OB018 | Offboarding — alumni network — optional opt-in after exit | LOW |
| OB019 | Offboarding — rehire eligibility flag — set by HR during exit process | MEDIUM |
| OB020 | Offboarding — pending reimbursements settled in full & final | HIGH |

## 63. LEAVE MANAGEMENT — ADVANCED EDGE CASES

| # | Rule | Priority |
|---|------|----------|
| LV001 | Comp-off (compensatory off) — earned by working on holiday/weekend, has expiry (e.g., 30 days) | HIGH |
| LV002 | Comp-off — cannot be encashed, only used as leave | MEDIUM |
| LV003 | Comp-off — manager must approve the comp-off earning (not just the usage) | HIGH |
| LV004 | Leave encashment — only for specific leave types (typically EL/PL), not sick or casual | HIGH |
| LV005 | Leave encashment — taxable beyond exempted amount (Rs 25L lifetime from FY 2023-24) | HIGH |
| LV006 | Sandwich rule — leave between two holidays/weekends counts the holidays/weekends as leave (per policy) | HIGH |
| LV007 | Sandwich rule — configurable per leave type (e.g., sick leave exempt from sandwich rule) | MEDIUM |
| LV008 | Negative leave balance — allowed for specific types (e.g., sick leave) with future deduction | MEDIUM |
| LV009 | Leave year reset — pro-rata for mid-year joiners based on remaining months | HIGH |
| LV010 | Leave lapse — unused leave beyond carry-forward limit lapses on year end | HIGH |
| LV011 | Leave accrual — monthly vs annual vs quarterly credit configurable | HIGH |
| LV012 | Restricted holiday — limited number (e.g., 2 out of 10 listed), employee must apply in advance | MEDIUM |
| LV013 | Leave applied for past date — only with admin/HR approval and valid reason | HIGH |
| LV014 | Leave type deactivation — cannot deactivate leave type if employees have balance | HIGH |
| LV015 | Short leave / permission — half day or quarter day, max N per month | MEDIUM |
| LV016 | Bereavement leave — auto-approve option, proof not required immediately | MEDIUM |
| LV017 | Marriage leave — once in career, proof required within X days | LOW |
| LV018 | Leave clubbing restriction — certain leave types cannot be combined (e.g., CL + EL on same request) | MEDIUM |
| LV019 | Auto-leave on absence — if no attendance and no leave applied, auto-LOP or auto-CL per policy | HIGH |
| LV020 | Leave balance API — real-time balance check, not cached or stale | HIGH |

## 64. ATTENDANCE — ADVANCED EDGE CASES

| # | Rule | Priority |
|---|------|----------|
| AT001 | Regularization — employee can request attendance correction with reason and manager approval | HIGH |
| AT002 | Regularization — deadline: cannot regularize attendance older than X days (e.g., 7 days) | HIGH |
| AT003 | Regularization — max N regularizations per month to prevent misuse | MEDIUM |
| AT004 | Half-day logic — if worked < 4 hours (or configurable), marked as half-day present | HIGH |
| AT005 | Minimum hours for full-day — configurable (e.g., 8 hours = full day, 4-8 = half, <4 = absent) | HIGH |
| AT006 | Overtime calculation — only after completing minimum required hours | HIGH |
| AT007 | Overtime — pre-approved overtime only (or auto-approve per policy) | MEDIUM |
| AT008 | Overtime cap — max overtime hours per week/month configurable | HIGH |
| AT009 | Multiple punches in a day — first in and last out used for duration calculation | HIGH |
| AT010 | Multiple punches — intermediate punches tracked for break analysis | LOW |
| AT011 | Attendance on weekends — only counted if weekend working is approved or employee is on 6-day week | HIGH |
| AT012 | Attendance integration — biometric, mobile, web check-in: all sources consolidated into single attendance record | CRITICAL |
| AT013 | Conflict resolution — if biometric and manual attendance conflict, biometric takes priority (configurable) | HIGH |
| AT014 | Continuous absent for X days — auto-trigger absent without leave process | HIGH |
| AT015 | Absent without leave — after 3 consecutive days, show-cause notice workflow triggered | HIGH |
| AT016 | Work from home attendance — separate marking, no geo-fence, but hours tracked | HIGH |
| AT017 | Flexi-time — core hours (e.g., 10 AM - 4 PM) plus flexible start/end | MEDIUM |
| AT018 | Attendance roster — monthly roster with weekly off, shift assignment, holiday marking | HIGH |
| AT019 | Roster — cannot have more than 6 consecutive working days without a day off | HIGH |
| AT020 | Attendance anomaly detection — flagging unusual patterns (always exactly on time, always exactly minimum hours) | LOW |

## 65. DOCUMENT MANAGEMENT — EDGE CASES

| # | Rule | Priority |
|---|------|----------|
| DM001 | Document types — categorized: personal (Aadhaar, PAN), educational, professional, offer letter, etc. | HIGH |
| DM002 | Mandatory documents — tracked per employee type, onboarding incomplete without them | HIGH |
| DM003 | Document expiry — passport, visa, certification: alerts sent before expiry | HIGH |
| DM004 | Document version control — uploading new version retains previous versions in history | HIGH |
| DM005 | Document access — employee's personal documents visible only to employee and HR | CRITICAL |
| DM006 | Document access — salary documents (payslips, Form 16) visible to employee, HR, and finance | HIGH |
| DM007 | Document template — offer letter, experience letter, salary revision letter: merge fields auto-populated | HIGH |
| DM008 | Digital signature — document signing workflow (e.g., Aadhaar eSign, DocuSign integration) | MEDIUM |
| DM009 | Document storage — encrypted at rest, virus-scanned on upload | HIGH |
| DM010 | Document retention — per statutory requirement: payroll records 8 years, PF records 5 years after exit | HIGH |
| DM011 | Document purge — after retention period, documents eligible for automated purge with audit log | MEDIUM |
| DM012 | Bulk document download — employee can download all their documents as ZIP | MEDIUM |
| DM013 | Document upload — max individual file size 10 MB, total storage per employee configurable | HIGH |
| DM014 | Document search — by name, type, upload date, employee | MEDIUM |
| DM015 | Letter generation — auto-generate appointment letter, confirmation letter, transfer letter with correct data | HIGH |

## 66. TRAINING & DEVELOPMENT — EDGE CASES

| # | Rule | Priority |
|---|------|----------|
| TD001 | Training enrollment — cannot exceed batch capacity | HIGH |
| TD002 | Training enrollment — waitlist management when batch is full | MEDIUM |
| TD003 | Mandatory training — compliance training must be completed within X days (e.g., POSH, data privacy) | HIGH |
| TD004 | Mandatory training — non-completion flagged to HR and manager | HIGH |
| TD005 | Training completion — certificate generated and stored in employee profile | MEDIUM |
| TD006 | Training cost — tracked per employee, against department training budget | HIGH |
| TD007 | Training feedback — post-training evaluation form mandatory | MEDIUM |
| TD008 | Training bond — if company-sponsored, service agreement period tracked | HIGH |
| TD009 | Training bond — early exit triggers bond recovery calculation in full & final | HIGH |
| TD010 | E-learning integration — LMS course completion synced to HR system | MEDIUM |
| TD011 | Skill matrix — training linked to skill development, tracked per employee | MEDIUM |
| TD012 | Certification tracking — professional certifications with expiry and renewal alerts | MEDIUM |

## 67. COMPENSATION — ESOP & BENEFITS EDGE CASES

| # | Rule | Priority |
|---|------|----------|
| CB001 | ESOP grant — vesting schedule tracked (e.g., 4-year vest, 1-year cliff) | HIGH |
| CB002 | ESOP — vested options forfeited if not exercised within configurable window after exit | HIGH |
| CB003 | ESOP — exercise price, grant price, FMV at exercise tracked for tax calculation | HIGH |
| CB004 | ESOP — perquisite tax on exercise: FMV - exercise price, added to taxable income | HIGH |
| CB005 | Flexible benefits plan — employee allocates within total FBP amount across categories | HIGH |
| CB006 | FBP — unused allocation taxed as income at year end | HIGH |
| CB007 | FBP — category limits enforced (e.g., fuel max Rs 1,600/month) | HIGH |
| CB008 | Insurance — group health insurance enrollment window: 30 days from joining | HIGH |
| CB009 | Insurance — mid-year life events (marriage, childbirth) allow special enrollment | HIGH |
| CB010 | Insurance — premium split between employer and employee tracked separately | HIGH |
| CB011 | NPS (National Pension System) — employer contribution up to 10% of basic is tax-free under 80CCD(2) | MEDIUM |
| CB012 | NPS — employee additional contribution under 80CCD(1B) up to Rs 50,000 tracked | MEDIUM |
| CB013 | Retention bonus — conditional payout on completing specified tenure | MEDIUM |
| CB014 | Referral bonus — paid only after referred employee completes probation | HIGH |
| CB015 | Sign-on bonus — clawback clause tracked if employee exits before specified period | HIGH |

## 68. MULTI-TENANT & ORGANIZATION RULES

| # | Rule | Priority |
|---|------|----------|
| MT001 | Data isolation — no API or query can return data from another organization | CRITICAL |
| MT002 | Data isolation — database queries always include organization filter | CRITICAL |
| MT003 | Subdomain/custom domain — each tenant has unique access URL | HIGH |
| MT004 | Tenant configuration — each organization has independent settings (leave policy, payroll config, etc.) | CRITICAL |
| MT005 | Tenant deactivation — suspends all users, data preserved for retention period | HIGH |
| MT006 | Tenant data export — on cancellation, provide full data export within 30 days | HIGH |
| MT007 | Tenant deletion — data permanently purged after retention period, with confirmation | HIGH |
| MT008 | Cross-tenant reporting — only for platform super admin, never for tenant users | HIGH |
| MT009 | Tenant branding — logo, color theme, email templates customizable per organization | MEDIUM |
| MT010 | Tenant trial — auto-expire after trial period, convert to paid or deactivate | HIGH |
| MT011 | Feature flags — features can be enabled/disabled per tenant | HIGH |
| MT012 | Resource limits — per-tenant limits on storage, API calls, employees | HIGH |

## 69. LETTER & COMMUNICATION TEMPLATES

| # | Rule | Priority |
|---|------|----------|
| LT001 | Offer letter — salary breakup, designation, joining date, reporting manager auto-populated | HIGH |
| LT002 | Appointment letter — terms of employment, probation, notice period included | HIGH |
| LT003 | Confirmation letter — auto-triggered on probation completion, requires HR approval | HIGH |
| LT004 | Salary revision letter — new salary structure, effective date, all components listed | HIGH |
| LT005 | Transfer letter — from/to location, department, designation, effective date | HIGH |
| LT006 | Warning letter — incident details, previous warnings referenced, consequence stated | HIGH |
| LT007 | Termination letter — reason, last working day, F&F details | HIGH |
| LT008 | Experience letter — designation, period of employment, generated only after full clearance | HIGH |
| LT009 | Relieving letter — confirmation of resignation acceptance, last working day | HIGH |
| LT010 | All letters — version controlled with template versioning, changes audited | MEDIUM |
| LT011 | All letters — digital signature or authorized signatory stamped | HIGH |
| LT012 | All letters — auto-stored in employee document folder | HIGH |
| LT013 | All letters — language configurable (English, Hindi, regional) per employee preference | MEDIUM |
| LT014 | Bulk letter generation — for mass salary revision, transfer scenarios | MEDIUM |
| LT015 | Letter templates — HR can create/edit templates with merge variables ({{employee_name}}, {{designation}}) | HIGH |

## 70. HELPDESK & TICKETING — EDGE CASES

| # | Rule | Priority |
|---|------|----------|
| HK001 | Ticket auto-assignment — round-robin or load-balanced among HR team | MEDIUM |
| HK002 | Ticket SLA — response time SLA and resolution time SLA configurable per category | HIGH |
| HK003 | Ticket SLA breach — auto-escalate to HR manager | HIGH |
| HK004 | Ticket categories — Payroll, Leave, IT, Facilities, General HR, Compliance | MEDIUM |
| HK005 | Ticket priority — auto-set based on category or manually overridden | MEDIUM |
| HK006 | Ticket — employee can attach files (screenshots, documents) | MEDIUM |
| HK007 | Ticket — conversation thread between employee and HR, with timestamps | HIGH |
| HK008 | Ticket — reopen within X days if issue recurs | MEDIUM |
| HK009 | Ticket — satisfaction survey on closure (1-5 rating + optional comment) | LOW |
| HK010 | Ticket analytics — average resolution time, SLA compliance %, top categories | MEDIUM |
| HK011 | Ticket — PII in ticket content masked for non-authorized viewers | HIGH |
| HK012 | Ticket — cannot be deleted, only closed or archived | HIGH |

## 71. DISCIPLINARY & GRIEVANCE — EDGE CASES

| # | Rule | Priority |
|---|------|----------|
| DG001 | Warning levels — verbal warning, written warning, final warning, termination — progressive discipline tracked | HIGH |
| DG002 | Warning letter — employee must acknowledge receipt (digital signature or OTP confirmation) | HIGH |
| DG003 | Show cause notice — response deadline enforced (e.g., 7 days) | HIGH |
| DG004 | Domestic inquiry — hearing panel constitution tracked | MEDIUM |
| DG005 | Suspension pending inquiry — half salary payable during suspension period | HIGH |
| DG006 | Suspension — if exonerated, full salary arrears paid | HIGH |
| DG007 | Grievance submission — employee can file anonymously or named | HIGH |
| DG008 | Grievance — acknowledgment within 48 hours, resolution within 30 days | HIGH |
| DG009 | Grievance escalation — if not resolved at L1, auto-escalate to L2 (HR head), then L3 (management) | HIGH |
| DG010 | Disciplinary records — retained for configurable period, not visible to future managers unless authorized | HIGH |
| DG011 | Appeal process — employee can appeal disciplinary decision within X days | MEDIUM |
| DG012 | No retaliation — grievance filer's identity protected, any adverse action flagged | CRITICAL |

## 72. COUNTRY-SPECIFIC HOLIDAY & LEAVE RULES (INTERNATIONAL)

| # | Rule | Priority |
|---|------|----------|
| IH001 | Holiday calendars — separate calendar per country/entity | CRITICAL |
| IH002 | Holidays — gazetted/public holidays auto-populated per country (via configurable list or API) | HIGH |
| IH003 | US — FMLA tracking: 12 weeks unpaid leave for qualifying events, eligibility 12 months + 1,250 hours | HIGH |
| IH004 | US — state-specific paid sick leave laws (California, New York, etc.) | HIGH |
| IH005 | UK — statutory sick pay (SSP) after 3 waiting days, per HMRC rates | HIGH |
| IH006 | UK — 28 days statutory holiday entitlement (including bank holidays) | HIGH |
| IH007 | UAE — 30 calendar days annual leave after 1 year of service | HIGH |
| IH008 | Singapore — 7 to 14 days annual leave based on years of service | HIGH |
| IH009 | Germany — minimum 24 working days annual leave (based on 6-day week) or 20 (5-day week) | HIGH |
| IH010 | Australia — 4 weeks annual leave, long service leave after 7-10 years (state-dependent) | HIGH |
| IH011 | Japan — paid annual leave starts at 10 days, increases with tenure, min 5 days must be used | HIGH |
| IH012 | Country-specific parental leave — varies dramatically (Sweden 480 days, US 0 federal mandate) | MEDIUM |
| IH013 | Religious/cultural holidays — configurable optional holidays per location | MEDIUM |

---

**Total new rules in V3: ~680 (across 42 new categories: sections 31-72)**

**Grand total across all documents:**
- BUSINESS_RULES.md (V1): ~200 rules
- BUSINESS_RULES_V2.md (V2): ~150 rules
- BUSINESS_RULES_V3.md (V3): ~680 rules
- **Combined: ~1,030 business rules**

Each should be tested and categorized as:
- **ENFORCED** — rule works correctly
- **NOT ENFORCED** — rule should exist but doesn't (BUG)
- **NOT IMPLEMENTED** — feature doesn't exist yet (FEATURE REQUEST)
- **PARTIALLY ENFORCED** — works in some scenarios but not all
