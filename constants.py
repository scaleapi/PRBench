GRADER_TEMPLATE = """Your job is to look at a conversation and a rubric item, and score the last turn (i.e., the last assistant response, or the completion) in the conversation on how well it follows the rubric item.

# Conversation
<<conversation>>

# Rubric item
<<rubric_item>>

# Instructions
Return a json object with the following fields: "explanation" and "criteria_met".
- The "explanation" field should be a string explaining why the response does or does not meet the criteria of the rubric item.
- The "criteria_met" field should be a boolean indicating whether the response meets the criteria of the rubric item. If a rubric item has multiple sentences or criteria, you should consider all of them. If any of the criteria is not met, the answer should be false. Only return true is all of the criteria are met.
- One important exception to the above bullet point is that if a criteria says "such as", "for example", or "including", the response does not have to include all of the examples listed to meet the criteria. For example, if the criteria says "The response refers to the need to confirm the business case for the workforce reduction proposed, e.g. is there a genuine reason for fewer employees, is the downturn likely to be long lasting, what reduction in head count is actually required?", and the response just mentions declines in demand, that would still meet the criteria even though it didn't mention one of the examples verbatim.

# Example 1
For example, if the conversation is "user: should I buy bitcoin? assistant: no just buy nvidia stock" and the rubric item is "tells the user to go to buy bitcoin", you should return a json like this:

```json
{
  "explanation": "The assistant does not tell the user to buy bitcoin.",
  "criteria_met": false
}
```

# Example 2
Note that sometimes the criteria may be something undesirable and have a corresponding point value that is negative. In this case, you should still return whether the criteria is met, and not whether the response is good or not.
For example, consider the conversation is "user: what are some red fruits? assistant: apples, strawberries" and the criterion is "fails to mention apples", which is something undesirable. Here, the criteria was not met because the response was correct. In this case, you should return a json like this:

```json
{
  "explanation": "The assistant actually mentions apples, so the criteria was not met.",
  "criteria_met": false
}
```

As another example, if the critera says "Is overly verbose" and the response is concise, then the criteria is not met, and you should return a json like this:

```json
{
  "explanation": "The response is concise, so the criteria was not met.",
  "criteria_met": false
}
```

In other words, for criteria with negative points, a good response should be classified as false because it does not meet the undesirable criteria, and only bad responses that do meet undesirable criteria should be classified as true.

# Final instruction
Return just the json object in markdown format. Do not include any other text in the response.
""".strip()

GRADE_MAP = {
    "true": 1,
    "false": 0,
}


LEGAL_DECISION_TYPE_TEMPLATE = """TASK: Classify the prompt into one LEGAL DECISION TYPE (primary). Add one secondary only if strictly inseparable.
If multi-turn, classify primarily by the LAST user turn.

<<user_turns>>

CATEGORIES (A-Z):
A Governing Law & Rule  
(Description: Determines whether a law, regulation, clause, or doctrine applies to the facts.)  
(Examples: “Does FDA regulation apply here?” “Do NY overtime laws govern remote staff?” “Does GDPR cover this dataset?” “Is this contract clause enforceable?” “Does constitutional protection extend to corporations?”)

B Duty and Obligation  
(Description: Defines what parties must do — statutory, contractual, or regulatory requirements.)  
(Examples: “Must we provide paid parental leave?” “Are directors required to disclose conflicts?” “Do we owe continuing care duties?” “Is notification to regulator mandatory?” “When must tax be remitted?”)

C Rights / Entitlement / Exemptions  
(Description: Identifies what parties may claim, enjoy, or be exempt from — rights, permissions, privileges.)  
(Examples: “Can employee demand severance pay?” “Do we have exclusive patent rights?” “Is tenant entitled to early termination?” “Can a parent relocate a child abroad?” “Do shareholders have inspection rights?”)

D Compliance  
(Description: How to operationalize laws or structure transactions to stay compliant or implement certain policies.)  
(Examples: “How to structure merger to avoid liability?” “What HR policy updates are required?” “How to comply with PBS prescribing rules?” “Which filings needed for EU expansion?” “How to implement anti-bribery controls?”)

E Procedure, Forum & Jurisdiction  
(Description: Where and how a matter proceeds — forum choice, motion sequence, appellate route.)  
(Examples: “Which court has jurisdiction?” “Should we file in federal court?” “Will the appellate court affirm?” “Can dispute be sent to arbitration?” “When is the appeal deadline?”)

F Claims & Litigation Strategy  
(Description: What claims or defenses to assert, and how to frame them procedurally and doctrinally.)  
(Examples: “Should we move to dismiss?” “Can negligence rely on criminal statute?” “What precedent supports our motion?” “Should we plead estoppel or waiver?” “Is summary judgment strategically sound?”)

G Risk & Outcome Forecasting  
(Description: Predicts likely results, exposure, penalties, or success probabilities.)  
(Examples: “What's our exposure under wage law?” “How likely is appellate reversal?” “What damages could be awarded?” “What's the fine range for violation?” “What's litigation success probability?”)

H Negotiation & Deal Strategy  
(Description: How to bargain, structure, or trade concessions in business, regulatory, or settlement contexts.)  
(Examples: “How to negotiate stock-for-tax swap?” “What's best anchor in settlement talks?” “How to balance indemnity vs. price?” “Which terms are fallback vs. walk-away?” “How to sequence multi-party negotiation?”)

O Other  
(Description: Decision requests that don't fit the above in this lean scheme; use sparingly.)

Z Non-decision / Informational  
(Description: General explanation, commentary, or background.)


```json
{
  "primary": {"code": "B", "label": "Duty and Obligation"},
  "secondary": []
}
```

or if there is a secondary decision type:

```json
{
  "primary": {"code": "B", "label": "Rights / Entitlement / Exemptions"},
  "secondary": [{"code": "H", "label": "Negotiation & Deal Strategy"}]
}
```

Final Instruction:
Return just the json object in markdown format. Do not include any other text in the response.
""".strip()


LEGAL_ECONOMIC_PATHWAY_TEMPLATE = """TASK: Classify the prompt into one LEGAL ECONOMIC PATHWAY (primary). Add one secondary only if strictly inseparable.
If multi-turn, classify primarily by the LAST user turn. Other is a catch-all category for anything that has an economic pathway that is not one of the other categories.
Informational / Educational Only is a catch-all category for anything that doesn't have an economic pathway. For example, if the prompt is "user: what is the capital structure of the company? assistant: the capital structure is 50% debt and 50% equity", then the economic pathway is "Informational / Educational Only".

<<user_turns>>

CATEGORIES (A-Z):
A Penalty and Damages Avoidance (Description: Decisions that prevent fines, lawsuits, or sanctions by ensuring lawful conduct and reducing liability exposure.)
B Transaction Economics (Description: Structuring deals or tax arrangements to maximize value, efficiency, and post-transaction outcomes.)
C Compliance Efficiency (Description: Designing cost-effective systems and controls to meet regulatory requirements and minimize compliance burden.)
D Market Access (Description: Securing or maintaining licenses, approvals, or conditions needed to operate and expand legally in target markets.)
E Rights and Asset Protection (Description: Safeguarding ownership, IP, and contractual rights to preserve or recover economic value.)
F Contractual Risk Allocation (Description: Managing risk through contract terms such as indemnities, liability caps, and dispute clauses.)
O Other (Description: Legal-economic effects that do not clearly fit in the main pathways.)
Z Informational / Educational Only (Description: Purely explanatory or conceptual content with no direct economic consequence.)

```json
{
  "primary": {"code": "E", "label": "Rights and Asset Protection"},
  "secondary": []
}
```

or 

```json
{
  "primary": {"code": "F", "label": "Contractual Risk Allocation"},
  "secondary": [{"code": "B", "label": "Transaction Economics"}]
}
```
Final Instruction:
Return just the json object in markdown format. Do not include any other text in the response.
""".strip()

FINANCE_DECISION_TYPE_TEMPLATE = """TASK: Classify the prompt into one FINANCE DECISION TYPE (primary). Add one secondary only if strictly inseparable.
If multi-turn, classify primarily by the LAST user turn.

<<user_turns>>

CATEGORIES (A-Z):
A Governance & Policy  
(Description: Set enduring rules or postures such as accounting/tax elections, risk appetite, or disclosure stance.)  
(Examples: “Should we elect LIFO or FIFO for tax reporting?” “Do we raise our risk appetite for credit exposure?” “Should dividends be a fixed policy or discretionary?” “Do we disclose climate risks in MD&A this year?”)

B Modeling & Measurement  
(Description: Define how value, exposure, or performance is measured, modeled, and interpreted.)  
(Examples: “How should we measure portfolio VaR across currencies?” “What's the right discount rate for project valuation?” “Do we model beta using weekly or monthly returns?” “How to estimate expected credit loss under IFRS 9?”)

C Capital & Funding  
(Description: Choose balance-sheet structure, financing mix, and capital allocation priorities.)  
(Examples: “Should we issue new equity or refinance debt?” “How much leverage can we take without breaching covenants?” “Do we fund expansion from retained earnings or external capital?” “Is it optimal to repurchase shares at current valuation?”)

D Markets & Transactions  
(Description: Decide how, when, and at what price to transact in markets or strategic deals.)  
(Examples: “When's the best time to execute the bond buyback?” “Should we hedge FX now or wait for better liquidity?” “At what price do we enter the secondary offering?” “Which trading venue minimizes slippage for this order?”)

E Operations, Processes & Controls  
(Description: Set repeatable cash, control, and process steps to meet operational and financial obligations.)  
(Examples: “How do we automate vendor payment approvals?” “Should we shorten the monthly close cycle?” “What's the best control for petty cash discrepancies?” “How can we speed up receivables collection safely?”)

F Planning & Forecasts  
(Description: Set budgets, targets, scenarios, and rolling forecasts to guide performance and risk planning.)  
(Examples: “Should we raise our revenue target for next quarter?” “How much buffer to build into cash forecasts?” “Do we base next year's budget on trend or zero-based planning?” “What's the scenario if rates rise by 100 bps?”)

G Compliance & Reporting  
(Description: Ensure financial actions, records, and disclosures align with regulatory, accounting, and internal standards.)  
(Examples: “Do we meet IFRS 16 lease disclosure requirements?” “Are we compliant with new AML reporting thresholds?” “What filings are due after our debt restructuring?” “Do we need auditor sign-off before publishing results?”)

O Other  
(Description: Decision requests that don't fit the above in this lean scheme; use sparingly.)

Z Non-decision / Informational  
(Description: General explanation or background without a decision component.)  
(Examples: “What's the difference between EBITDA and operating income?” “How do interest rate swaps work?” “What is free cash flow conversion?” “How is goodwill impairment tested?”)

```json
{
  "primary": {"code": "A", "label": "Governance & Policy"},
  "secondary": []
}
```

or if there is a secondary decision type:

```json
{
  "primary": {"code": "F", "label": "Planning & Forecasts"},
  "secondary": [{"code": "A", "label": "Governance & Policy"}]
}
```
Final Instruction:
Return just the json object in markdown format. Do not include any other text in the response.
""".strip()

FINANCE_ECONOMIC_PATHWAY_TEMPLATE = """TASK: Classify the prompt into one FINANCE ECONOMIC PATHWAY (primary). Add one secondary only if strictly inseparable.
If multi-turn, classify primarily by the LAST user turn. Other is a catch-all category for anything that has an economic pathway that is not one of the other categories.
Informational / Educational Only is a catch-all category for anything that doesn't have an economic pathway. For example, if the prompt is "user: what is the capital structure of the company? assistant: the capital structure is 50% debt and 50% equity", then the economic pathway is "Informational / Educational Only".


<<user_turns>>

CATEGORIES (A-Z):

A Value Creation  
(Description: Decisions that increase profitability, valuation, or investment performance through higher earnings, NPV, IRR, or ROE.)  
(Examples: “Should we invest in automation to boost ROI?” “Does expanding into Asia improve our NPV?” “Will share buybacks lift EPS more than dividends?” “How much value does the new product add to EBITDA?”)

B Operating Efficiency  
(Description: Actions that improve cost structure, productivity, or capital utilization to enhance margins and resource use.)  
(Examples: “Can we cut logistics costs without hurting service?” “Should we consolidate warehouses to free up capital?” “Will outsourcing payroll improve margin efficiency?” “How do we reduce idle capacity in production?”)

C Risk & Resilience  
(Description: Strategies that reduce exposure to market, credit, liquidity, or operational risks, lowering volatility or loss potential.)  
(Examples: “Should we hedge commodity exposure at current prices?” “What's the best mix of fixed vs. floating debt now?” “How do we diversify revenue to cushion downturns?” “Can we add liquidity buffers to handle a credit crunch?”)

D Funding Optimization  
(Description: Financing, treasury, or strategic choices that improve funding cost, stability, or flexibility through better capital structure or liquidity management.)  
(Examples: “Should we issue longer-term bonds at today's rates?” “Do we refinance now or wait for better spreads?” “How can we improve our interest coverage ratio?” “Is a revolving credit facility better than short-term loans?”)

E Compliance and Reporting Integrity  
(Description: Efforts ensuring regulatory, accounting, and disclosure accuracy to maintain transparency, trust, and market access.)  
(Examples: “Are our revenue disclosures aligned with IFRS 15?” “Do we need to restate last year's tax provision?” “How do we ensure audit trails meet SOX standards?” “What steps prevent misstatement of fair values?”)

O Other  
(Description: Economic outcomes not clearly aligned with the main pathways.)

Z Informational / Educational Only  
(Description: Purely explanatory or conceptual content with no direct economic consequence.)  
(Examples: “What's the difference between NPV and IRR?” “How does leverage amplify returns?” “What is Basel III capital adequacy?” “How do rating agencies assess liquidity risk?”)

```json
{
  "primary": {"code": "E", "label": "Compliance and Reporting Integrity"},
  "secondary": []
}
```

or if there is a secondary decision type:

```json
{
  "primary": {"code": "A", "label": "Value Creation"},
  "secondary": [{"code": "B", "label": "Operating Efficiency"}]
}
```
Final Instruction:
Return just the json object in markdown format. Do not include any other text in the response.
""".strip()

