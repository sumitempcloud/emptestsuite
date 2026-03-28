import os
import re

kb_path = r'c:\emptesting\KNOWLEDGE_BASE.md'
br_path = r'c:\emptesting\BUSINESS_RULES.md'
out_dir = r'c:\emptesting\Agent_Test_Suites'

if not os.path.exists(out_dir):
    os.makedirs(out_dir)

# Read files
with open(kb_path, 'r', encoding='utf-8') as f:
    kb_content = f.read()

with open(br_path, 'r', encoding='utf-8') as f:
    br_content = f.read()

# --- Parse Business Rules ---
# They look like: | P001 | Cannot run payroll twice for same month | CRITICAL |
rules_by_module = {
    'Core': [],
    'Payroll': [],
    'Recruit': [],
    'Performance': [],
    'Rewards': [],
    'Exit': [],
    'LMS': [],
    'Cross_Module': []
}

# Categorize them based on their prefix or section
sections = re.split(r'## \d+\. ', br_content)
for section in sections[1:]:
    lines = section.strip().split('\n')
    section_title = lines[0].strip()
    
    module_key = 'Core'
    if 'PAYROLL' in section_title: module_key = 'Payroll'
    elif 'RECRUIT' in section_title: module_key = 'Recruit'
    elif 'PERFORMANCE' in section_title: module_key = 'Performance'
    elif 'EXIT' in section_title: module_key = 'Exit'
    elif 'LMS' in section_title: module_key = 'LMS'
    elif 'WELLNESS' in section_title or 'NOTIFICATIONS' in section_title or 'HELPDESK' in section_title: module_key = 'Rewards' # approximate mapping
    elif 'MULTI-TENANT' in section_title or 'SECURITY' in section_title: module_key = 'Cross_Module'
    else: module_key = 'Core'
    
    for line in lines:
        if line.startswith('|') and not 'Rule' in line and not '---' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                rule_id = parts[1]
                rule_desc = parts[2]
                priority = parts[3]
                if rule_id and rule_desc:
                    rules_by_module[module_key].append(f"- [ ] **{rule_id}** ({priority}): {rule_desc}")

# --- Parse API Endpoints ---
endpoints_by_module = {
    'Core': [],
    'Payroll': [],
    'Recruit': [],
    'Performance': [],
    'Rewards': [],
    'Exit': [],
    'LMS': []
}

api_sections = re.split(r'### EMP ', kb_content)
for section in api_sections[1:]:
    lines = section.strip().split('\n')
    section_title = lines[0].strip()
    
    module_key = 'Core'
    for k in endpoints_by_module.keys():
        if k.lower() in section_title.lower():
            module_key = k
            break
            
    # Extract table rows
    for line in lines:
        if line.startswith('|') and not 'Method' in line and not '---' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                method = parts[1]
                path = parts[2].replace('`', '')
                status = parts[3]
                if method and path and method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    endpoints_by_module[module_key].append(f"- [ ] `{method}` `{path}` -> Expected Status: `{status}`")

# --- Generate Markdown Files ---

def write_md(filename, title, module_key):
    path = os.path.join(out_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write("> **Testing Agent Note:** This is an exhaustive list derived directly from project parameters. Every item must be tested. Record actual HTTP response codes, payloads, and screenshot evidence.\n\n")
        
        f.write("## 1. Business Logic Rules\n\n")
        rules = rules_by_module.get(module_key, [])
        if rules:
            f.write("\n".join(rules) + "\n\n")
        else:
            f.write("*No specific business rules mapped solely to this module, see Cross_Module.*\n\n")
            
        f.write("## 2. API Endpoints to Verify\n\n")
        endpoints = endpoints_by_module.get(module_key, [])
        if endpoints:
            f.write("\n".join(endpoints) + "\n\n")
        else:
            f.write("*No endpoints found or API not deployed.*\n\n")

# Write Master Rules
with open(os.path.join(out_dir, '00_Master_Execution_Rules.md'), 'w', encoding='utf-8') as f:
    f.write("# Master Execution Rules for Agents\n\n"
            "1. **SSO Over Direct Login**: Always login to Core to get a JWT. Launch external modules by appending `?sso_token=<token>`.\n"
            "2. **Evidence**: Every bug requires a base64 screenshot or full Request/Response pair.\n"
            "3. **Exceptions**: Soft deletes (HTTP 200) and DB-stored XSS are BY DESIGN. Do not report them.\n\n"
            "Proceed to modules 01 through 08 and execute every mapped checkbox.\n")

write_md('01_Core_HR_Tests.md', 'Comprehensive Core HR Test Suite', 'Core')
write_md('02_Payroll_Tests.md', 'Comprehensive Payroll Test Suite', 'Payroll')
write_md('03_Recruit_Tests.md', 'Comprehensive Recruit Test Suite', 'Recruit')
write_md('04_Performance_Tests.md', 'Comprehensive Performance Test Suite', 'Performance')
write_md('05_Rewards_Tests.md', 'Comprehensive Rewards Test Suite', 'Rewards')
write_md('06_Exit_Tests.md', 'Comprehensive Exit Test Suite', 'Exit')
write_md('07_LMS_Tests.md', 'Comprehensive LMS Test Suite', 'LMS')
write_md('08_Cross_Module_Integrations.md', 'Comprehensive Cross-Module & Security Integrity Tests', 'Cross_Module')

print("All test suites generated successfully in Agent_Test_Suites!")
