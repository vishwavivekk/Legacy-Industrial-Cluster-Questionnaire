"""
NICDC Legacy Industrial Cluster Questionnaire - Form schema.

Each section is a dict with `id`, `title`, and `questions`.
Each question is a dict with at minimum: `id`, `label`, `type`.

Supported types:
    text         - single-line text
    textarea     - multi-line text
    number       - numeric
    yesno        - Yes / No radio
    select       - single choice from `options`
    multiselect  - multiple choice from `options`
    rank         - multi-select with ranking input per chosen option
    info         - read-only helper text (no input)
    group        - heading inside a section
    repeat       - repeated sub-block (used for raw material / machinery)
"""

SECTIONS = [
    {
        "id": "general",
        "title": "General Information",
        "icon": "🗂️",
        "questions": [
            {"id": "cluster_name",       "label": "Name of the Cluster",                                                  "type": "text", "required": True},
            {"id": "cluster_product",    "label": "Cluster Main Product / Product Line",                                  "type": "text", "required": True},
            {"id": "cluster_geo",        "label": "Geographic Location of the Cluster (Town / City and District)",        "type": "text", "required": True},
            {"id": "respondent",         "label": "Respondent Name and Designation",                                      "type": "text", "required": True},
            {"id": "respondent_contact", "label": "Respondent Contact (Email or Phone)",                                  "type": "text"},
        ],
    },
    {
        "id": "A_association",
        "title": "A. Industry Association",
        "icon": "🏛️",
        "questions": [
            {"id": "assoc_name",        "label": "Q1. Name of the association.",                              "type": "text"},
            {"id": "assoc_sector",      "label": "Q2. Sector represented by the association.",                "type": "text"},
            {"id": "assoc_year",        "label": "Q3. Year of establishment of the association.",             "type": "number", "min": 1800, "max": 2030, "step": 1},
            {"id": "assoc_legal",       "label": "Q4. Legal status.",                                         "type": "select",
                "options": ["Society", "Trust", "Section 8 Company", "Partnership", "LLP", "Cooperative Society", "Other"]},
            {"id": "assoc_legal_other", "label": "If Other, please specify.",                                 "type": "text"},
            {"id": "assoc_members",     "label": "Q5. Total number of members.",                              "type": "number", "min": 0, "step": 1},
            {"id": "assoc_staff",       "label": "Q6. Does the cluster association have full-time paid staff?", "type": "yesno"},
            {"id": "assoc_audit",       "label": "Q7. Does it maintain audited accounts for the last 2 years?", "type": "yesno"},
            {"id": "assoc_init1",       "label": "Q8a. Collective Initiative 1 (last 5 years).",              "type": "textarea"},
            {"id": "assoc_init2",       "label": "Q8b. Collective Initiative 2 (last 5 years).",              "type": "textarea"},
            {"id": "assoc_init3",       "label": "Q8c. Collective Initiative 3 (last 5 years).",              "type": "textarea"},
            {"id": "assoc_init_src",    "label": "Q9. For each initiative, was it independently led by the association or supported through a government-funded programme / partnership?", "type": "textarea"},
            {"id": "assoc_init_cost",   "label": "Q10. Approximate expenditure (budget / cost) for each initiative (mention amount and unit, e.g. ₹ 25 Lakh / ₹ 2 Crore).", "type": "textarea"},
        ],
    },
    {
        "id": "B_cluster",
        "title": "B. Cluster Information",
        "icon": "🏭",
        "questions": [
            {"id": "cluster_age",       "label": "Q1. How old is the cluster? (in years)",                                       "type": "number", "min": 0, "step": 1},
            {"id": "firms_micro",       "label": "Q2a. Number of MICRO firms (up to ₹10 Cr turnover).",                          "type": "number", "min": 0, "step": 1},
            {"id": "firms_small",       "label": "Q2b. Number of SMALL firms (₹10 Cr – ₹100 Cr turnover).",                      "type": "number", "min": 0, "step": 1},
            {"id": "firms_medium",      "label": "Q2c. Number of MEDIUM firms (up to ₹500 Cr turnover).",                        "type": "number", "min": 0, "step": 1},
            {"id": "firms_total",       "label": "Q2d. Total number of firms in the cluster.",                                   "type": "number", "min": 0, "step": 1},
            {"id": "concentration",     "label": "Q3. Where are firms concentrated in the cluster?",                             "type": "multiselect",
                "options": ["City and nearby places", "Block and nearby places", "District", "Industrial Park"]},
            {"id": "land_total",        "label": "Q4a. Total land area of the cluster (in acres).",                              "type": "number", "min": 0.0, "step": 0.1},
            {"id": "land_mapped",       "label": "Q4b. Has the cluster been mapped with clear and defined boundaries?",          "type": "yesno"},
            {"id": "land_expansion",    "label": "Q4c. Additional land available for expansion / rejuvenation (in acres).",      "type": "number", "min": 0.0, "step": 0.1},
            {"id": "land_rate",         "label": "Q5a. Prevailing land rate per acre in the cluster (in ₹ Crore per acre).",     "type": "number", "min": 0.0, "step": 0.01, "help": "Enter the value in Crores. Example: 1.25 means ₹ 1.25 Crore per acre."},
            {"id": "land_rate_change",  "label": "Q5b. Has the land rate changed significantly in the last 3–5 years? Please describe (mention amount and unit).", "type": "textarea"},
            {"id": "land_rate_barrier", "label": "Q5c. Are land rates a barrier to entry for new units?",                        "type": "yesno"},
            {"id": "land_available",    "label": "Q5d. Is land available for purchase or lease / sublease within the cluster?",  "type": "yesno"},
            {"id": "turnover",          "label": "Q6. Approximate turnover of the cluster (in ₹ Crore).",                        "type": "number", "min": 0.0, "step": 1.0},
            {"id": "exporting_pct",     "label": "Q7. Percentage of firms currently exporting (%).",                             "type": "number", "min": 0.0, "max": 100.0, "step": 0.5},
            {"id": "workers_total",     "label": "Q8a. Total number of workers currently employed.",                             "type": "number", "min": 0, "step": 1},
            {"id": "workers_skilled_pct","label": "Q8b. Of those, percentage of skilled workers (%).",                           "type": "number", "min": 0.0, "max": 100.0, "step": 0.5},
        ],
    },
    {
        "id": "C_support",
        "title": "C. Support Firms / BDS",
        "icon": "🤝",
        "questions": [
            {"id": "bds_info", "label": "BDS providers are specialised institutions (NGOs, public institutions, private consultants) that deliver non-financial support such as training, technology transfer, marketing, consultancy.", "type": "info"},
            {"id": "bds_types", "label": "Q1. Support firms / BDS providers present in the cluster (tick all that apply).", "type": "multiselect",
                "options": ["NGOs", "Public Institutions", "Private Consultants", "Others"]},
            {"id": "bds_other", "label": "If Others, please specify.", "type": "text"},
        ],
    },
    {
        "id": "C1_infrastructure",
        "title": "C.1 Infrastructure",
        "icon": "🛣️",
        "questions": [
            {"id": "infra_general_challenge", "label": "Q1. Does the cluster experience challenges in general infrastructure?", "type": "yesno"},
            {"id": "infra_ranked", "label": "Q1a. Rank each general infrastructure challenge in order of severity (1 = most severe). Leave the rank blank if not relevant.", "type": "rank",
                "options": ["Quality of road", "Telecommunications", "Power", "Water", "Cargo handling", "CETP", "Last mile connectivity", "Any other"]},
            {"id": "infra_other_specify", "label": "If 'Any other', please specify.", "type": "text"},
            {"id": "infra_suggestions",   "label": "Q2. Suggestions for improvement (solutions + supporting stakeholders/institutions).", "type": "textarea"},
            {"id": "infra_cluster_challenge", "label": "Q3. Do you face challenges in any cluster-specific infrastructure?", "type": "yesno"},
            {"id": "infra_common_req",    "label": "Q4. Common infrastructure requirements of the cluster (tick all that apply).", "type": "multiselect",
                "options": ["Testing laboratory", "Raw material depot", "Common facility centre", "Design centre", "Training centre", "Display centre", "Any other"]},
            {"id": "infra_common_other",  "label": "If 'Any other', please specify.", "type": "text"},
            {"id": "infra_scheme",        "label": "Q5. Has any cluster-specific infrastructure been established under any specific government scheme / programme? Mention the scheme.", "type": "textarea"},
        ],
    },
    {
        "id": "C2_park",
        "title": "C.2 Industrial Parks",
        "icon": "🏗️",
        "questions": [
            {"id": "park_name",     "label": "Q1. Name of the nearest industrial park.",                                                   "type": "text"},
            {"id": "park_distance", "label": "Q2. Distance of the park from the cluster (in km).",                                          "type": "number", "min": 0.0, "step": 0.5},
            {"id": "park_linked",   "label": "Q3. Is the cluster currently connected to the industrial park across the value chain (sourcing, production, logistics, services, markets)?", "type": "yesno"},
            {"id": "park_linkages", "label": "Q4. If yes, what types of linkages exist between the cluster and the industrial park?",      "type": "textarea"},
            {"id": "park_future",   "label": "Q5. Opportunities for establishing stronger or new linkages with the industrial park in the future?", "type": "yesno"},
            {"id": "park_future_specify", "label": "If yes, please specify.",                                                              "type": "textarea"},
            {"id": "park_barriers", "label": "Q6. Key barriers / challenges currently limiting effective linkages with the industrial park.", "type": "textarea"},
        ],
    },
    {
        "id": "C3_compliance",
        "title": "C.3 Compliance",
        "icon": "📋",
        "questions": [
            {"id": "comp_face",        "label": "Q1. Does the cluster face compliance-related challenges?",                  "type": "yesno"},
            {"id": "comp_types",       "label": "Q2. If yes, mention the type of challenges faced.",                         "type": "textarea"},
            {"id": "comp_time",        "label": "Q3. Approximate time spent by an enterprise on compliance per week.",       "type": "select",
                "options": ["Less than 2 hours", "2 to 3 hours", "More than 3 hours"]},
            {"id": "comp_suggestions", "label": "Q4. Suggestions for improvement (solutions + supporting stakeholders).",    "type": "textarea"},
        ],
    },
    {
        "id": "C4_export",
        "title": "C.4 Shift in Value Chain — Export Market",
        "icon": "🌐",
        "questions": [
            {"id": "exp_current",         "label": "Q1. Does the cluster currently export?",                                                "type": "yesno"},
            {"id": "exp_countries",       "label": "Q2. Major countries where the cluster is exporting.",                                   "type": "textarea"},
            {"id": "exp_challenges",      "label": "Q3. Challenges in continuing or expanding exports to existing countries (freight, market intel, regulation, supply chain, branding, tech gap, …).", "type": "textarea"},
            {"id": "exp_support_existing","label": "Q4. Types of support needed to expand in existing export markets.",                     "type": "textarea"},
            {"id": "exp_not_started",     "label": "Q5. If NOT exporting — main reasons (knowledge, finance, certifications, logistics, buyers, regulation, …).", "type": "textarea"},
            {"id": "exp_joint",           "label": "Q6. Capacity to collaborate for larger export orders / past joint domestic marketing?", "type": "textarea"},
            {"id": "exp_compliance_aware","label": "Q7. Is the cluster aware of compliances required for exporting (ISO, CE, …)?",          "type": "textarea"},
            {"id": "exp_support_new",     "label": "Q8. Support needed to enter / enhance export markets.",                                 "type": "textarea"},
            {"id": "anchor_challenges",   "label": "Anchor / Large Firms — Q1. Key challenges MSMEs face in aligning with supply chains of medium and large enterprises.", "type": "textarea"},
            {"id": "anchor_support",      "label": "Anchor / Large Firms — Q2. Which forms of support from larger enterprises can most effectively enable MSMEs to scale up?", "type": "multiselect",
                "options": ["Long term contracts", "Vendor development programmes", "Technology transfer", "Skill and capacity building", "Assured procurement", "Faster payment cycles", "Others"]},
            {"id": "anchor_other",        "label": "If Others, please specify.",                                                            "type": "text"},
        ],
    },
    {
        "id": "C5_market",
        "title": "C.5 Market Promotion (Domestic)",
        "icon": "🛒",
        "questions": [
            {"id": "mkt_channels",     "label": "Q1. How does the cluster sell its products? (tick all that apply)", "type": "multiselect",
                "options": ["Directly to local market", "National Market", "Retail / Wholesale", "Institutional / Bulk buyer", "Any other"]},
            {"id": "mkt_channel_other","label": "If 'Any other', please specify.",                                   "type": "text"},
            {"id": "mkt_preferred",    "label": "Any preferable channels? Why?",                                     "type": "textarea"},
            {"id": "mkt_challenges",   "label": "Q2. Challenges firms face in marketing the product.",               "type": "textarea"},
            {"id": "mkt_suggestions",  "label": "Q3. Suggestions for improvement (solutions + supporting stakeholders).", "type": "textarea"},
        ],
    },
    {
        "id": "C6_raw",
        "title": "C.6 Raw Material",
        "icon": "📦",
        "instructions": "Discuss the two or three most important (value-wise and/or critical) raw materials. Fill what applies — leave unused entries blank.",
        "questions": [
            {"id": "raw_materials", "type": "repeat", "label": "Raw Materials",
             "min_blocks": 1, "max_blocks": 3, "block_label": "Raw Material",
             "fields": [
                {"id": "name",    "label": "Name of the raw material",                                       "type": "text"},
                {"id": "source",  "label": "Q1. Source of supply (tick all that apply).",                    "type": "multiselect",
                    "options": ["Local supplier", "Domestic supplier", "International supplier", "Cooperative / SHG", "Group purchasing organisation", "Any other"]},
                {"id": "challenge_face",  "label": "Q2. Do they face challenges in procuring the raw material?", "type": "yesno"},
                {"id": "challenge_types", "label": "Q3. If yes, major challenges (tick all that apply, elaborate alongside).", "type": "multiselect",
                    "options": ["Poor quality", "Irregular supply", "Rapidly increasing price", "Price fluctuation", "Taxation", "Any other"]},
                {"id": "challenge_detail","label": "Elaboration on selected challenges.",                    "type": "textarea"},
                {"id": "suggestions",     "label": "Q4. Suggestions for improvement (solutions + supporting stakeholders).", "type": "textarea"},
             ]},
        ],
    },
    {
        "id": "C7_machinery",
        "title": "C.7 Machinery / Technology",
        "icon": "⚙️",
        "instructions": "Discuss the two or three most important (value-wise and/or critical) machinery. Fill what applies — leave unused entries blank.",
        "questions": [
            {"id": "machinery", "type": "repeat", "label": "Machinery",
             "min_blocks": 1, "max_blocks": 3, "block_label": "Machinery",
             "fields": [
                {"id": "name",         "label": "Name of the machinery",                                       "type": "text"},
                {"id": "source",       "label": "Q1. Source of supply (multiple allowed; please explain).",     "type": "multiselect",
                    "options": ["Local supplier", "Domestic supplier", "International supplier", "Cooperative / SHG", "Group purchasing organisation", "Any other"]},
                {"id": "source_detail","label": "Notes on source / supplier.",                                  "type": "textarea"},
                {"id": "challenges",   "label": "Q2. Key machinery-related challenges faced by the firms.",     "type": "textarea"},
                {"id": "suggestions",  "label": "Q3. Suggestions for improvement (solutions + supporting stakeholders).", "type": "textarea"},
             ]},
        ],
    },
    {
        "id": "C8_finance",
        "title": "C.8 Finance",
        "icon": "💰",
        "questions": [
            {"id": "fin_challenge",    "label": "Q1. Are firms facing challenges in obtaining financial support?", "type": "yesno"},
            {"id": "fin_issues",       "label": "Q2. Major challenges in accessing formal financing (tick all that apply).", "type": "multiselect",
                "options": [
                    "Delays in loan approval or disbursement by banks",
                    "Lack of adequate collateral or security",
                    "Limited knowledge or capacity to prepare project proposals or business plans",
                    "Inadequate documentation due to informal business operations",
                    "High or fluctuating interest rates",
                    "Limited awareness of available government or institutional finance schemes",
                    "Strict eligibility criteria of financial institutions",
                    "Others"
                ]},
            {"id": "fin_other",        "label": "If Others, please specify.",                                       "type": "text"},
            {"id": "fin_suggestions",  "label": "Q3. Suggestions for improvement (solutions + supporting stakeholders).", "type": "textarea"},
        ],
    },
    {
        "id": "C9_energy_water",
        "title": "C.9 Energy & Water",
        "icon": "💧",
        "questions": [
            {"id": "energy_tech",         "label": "Q1. Have any energy-saving technologies / interventions been introduced? Describe and indicate approximate reduction (%).", "type": "textarea"},
            {"id": "energy_suggestions",  "label": "Q2. Suggestions for improvement (solutions + supporting stakeholders).", "type": "textarea"},
            {"id": "water_source",        "label": "Q3. Major source of water consumption.", "type": "select",
                "options": ["Groundwater", "Municipality water", "Surface water", "Others"]},
            {"id": "water_source_other",  "label": "If Others, please specify.",                                              "type": "text"},
            {"id": "water_tech",          "label": "Q4. Water-saving technologies / interventions introduced? Describe and indicate approximate reduction (%).", "type": "textarea"},
            {"id": "water_challenges",    "label": "Q5. Water supply related challenges (if any).",                            "type": "textarea"},
            {"id": "water_suggestions",   "label": "Q6. Suggestions for improvement (solutions + supporting stakeholders).",   "type": "textarea"},
        ],
    },
    {
        "id": "C10_hr",
        "title": "C.10 HR / Capacity Building",
        "icon": "👷",
        "questions": [
            {"id": "skill_activities",  "label": "Q1. Activities for which skilled manpower is required.",                          "type": "textarea"},
            {"id": "skill_shortage",    "label": "Q2a. Is there a shortage of skilled labour in the cluster?",                       "type": "yesno"},
            {"id": "skill_states",      "label": "Q2b. States from which most workers migrate.",                                    "type": "text"},
            {"id": "wage_skilled",      "label": "Q3a. Average daily wage of SKILLED labour (in ₹ per day).",                       "type": "number", "min": 0, "step": 10},
            {"id": "wage_unskilled",    "label": "Q3b. Average daily wage of UNSKILLED labour (in ₹ per day).",                     "type": "number", "min": 0, "step": 10},
            {"id": "skill_area",        "label": "Q4. Functional areas with shortage of skilled manpower (tick all that apply).",   "type": "multiselect",
                "options": ["Operations / Maintenance", "Production / Manufacturing", "Marketing and Sales", "Customer Service", "Quality Control and Testing", "Finance and Accounting", "Any other"]},
            {"id": "skill_area_other",  "label": "If 'Any other', please specify.",                                                 "type": "text"},
            {"id": "skill_providers",   "label": "Q5. Main providers of technical training at cluster level (tick all that apply).", "type": "multiselect",
                "options": ["Association", "Technical Institution", "Value Chain Partner", "No source, need to organise specially"]},
            {"id": "skill_challenges",  "label": "Q6. Major challenges related to skilled labour (tick all that apply).",           "type": "multiselect",
                "options": ["Shortage of skilled labour", "High cost of hiring skilled workers", "Lack of quality-conscious skilled workers", "Inadequate technical skills among available workers", "Poor work attitude or behavioural / personality issues", "High attrition or migration of skilled workers"]},
            {"id": "skill_suggestions", "label": "Q7. Overall suggestions for improvement.",                                        "type": "textarea"},
        ],
    },
    {
        "id": "C11_waste",
        "title": "C.11 Waste Management",
        "icon": "♻️",
        "questions": [
            {"id": "waste_types",       "label": "Q1. Types of waste generated (tick all that apply).", "type": "multiselect",
                "options": ["Hazardous waste", "E-waste", "Plastic waste", "Others"]},
            {"id": "waste_other",       "label": "If Others, please specify.",                          "type": "text"},
            {"id": "waste_disposal",    "label": "Q2. Is disposal of waste a challenge? If yes, what measures have been taken?",  "type": "textarea"},
            {"id": "waste_common",      "label": "Q3. Is there any common facility for waste management?", "type": "yesno"},
            {"id": "waste_suggestions", "label": "Q4. If not, suggestions for improvement (solutions + supporting stakeholders).", "type": "textarea"},
        ],
    },
    {
        "id": "D_conclusion",
        "title": "D. Conclusion",
        "icon": "📝",
        "questions": [
            {"id": "additional", "label": "Please provide any further cluster-related information that will help in drafting the scheme.", "type": "textarea", "height": 220},
        ],
    },
]


def all_question_ids():
    """Flatten every leaf question id used in storage (CSV / DB export)."""
    ids = []
    for s in SECTIONS:
        for q in s["questions"]:
            if q["type"] == "info":
                continue
            if q["type"] == "repeat":
                for b in range(1, q.get("max_blocks", 3) + 1):
                    for f in q["fields"]:
                        ids.append(f"{s['id']}__{q['id']}__b{b}__{f['id']}")
            else:
                ids.append(f"{s['id']}__{q['id']}")
    return ids
